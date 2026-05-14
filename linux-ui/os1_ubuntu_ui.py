#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import pathlib
import shutil
import uuid
import shlex
import subprocess
import threading
import urllib.error
import urllib.request
import tkinter as tk
from dataclasses import asdict, dataclass
from tkinter import filedialog, messagebox, ttk


APP_DIR = pathlib.Path.home() / ".config" / "os1-linux"
CONNECTIONS_FILE = APP_DIR / "connections.json"
SESSIONS_FILE = APP_DIR / "sessions.json"
KANBAN_FILE = APP_DIR / "kanban.json"
SKILLS_FILE = APP_DIR / "skills.json"
CRON_FILE = APP_DIR / "cron.json"
SETTINGS_FILE = APP_DIR / "settings.json"
SECRET_SERVICE = "os1-ubuntu-ui"
SECRET_ACCOUNT = "orgo_api_key"


@dataclass
class Connection:
    name: str
    transport: str
    host: str
    user: str
    port: str


@dataclass
class SessionItem:
    id: str
    title: str
    connection: str
    notes: str


@dataclass
class KanbanTask:
    id: str
    title: str
    status: str


@dataclass
class SkillItem:
    id: str
    name: str
    summary: str


@dataclass
class CronItem:
    id: str
    schedule: str
    command: str


class OS1UbuntuUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OS1 Desktop (Ubuntu)")
        self.geometry("1320x860")
        self.minsize(980, 600)
        self.configure(bg="#141015")

        self._configure_style()
        self.connections: list[Connection] = self._load_connections()
        self.sessions: list[SessionItem] = self._load_items(SESSIONS_FILE, SessionItem)
        self.kanban_tasks: list[KanbanTask] = self._load_items(KANBAN_FILE, KanbanTask)
        self.skills: list[SkillItem] = self._load_items(SKILLS_FILE, SkillItem)
        self.cron_jobs: list[CronItem] = self._load_items(CRON_FILE, CronItem)
        self.current_file: pathlib.Path | None = None
        self.settings = self._load_settings()
        self.orgo_workspace_rows: list[dict] = []
        self.orgo_computer_rows: list[dict] = []
        self.active_connection_name = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="ready")

        self.sidebar = tk.Frame(self, bg="#1f1724", width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.content = tk.Frame(self, bg="#141015")
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.views: dict[str, tk.Frame] = {}
        self._build_sidebar()
        self._build_views()
        self._build_status_bar()
        self.show_view("Connections")
        self.after(250, self._maybe_show_first_run_wizard)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background="#201927", fieldbackground="#201927", foreground="#f6ebf0")
        style.configure("Treeview.Heading", background="#2f2438", foreground="#f6ebf0")
        style.map("Treeview", background=[("selected", "#e76f51")], foreground=[("selected", "#1a0f13")])

    def _build_sidebar(self) -> None:
        tk.Label(
            self.sidebar,
            text="OS1",
            bg="#1f1724",
            fg="#f6ebf0",
            font=("DejaVu Sans", 22, "bold"),
        ).pack(anchor="w", padx=16, pady=(20, 4))
        tk.Label(
            self.sidebar,
            text="Ubuntu Desktop",
            bg="#1f1724",
            fg="#ccb8c3",
            font=("DejaVu Sans", 10),
        ).pack(anchor="w", padx=16, pady=(0, 14))

        for section in [
            "Connections",
            "Sessions",
            "Files",
            "Terminal",
            "Kanban",
            "Skills",
            "Cron",
        ]:
            btn = tk.Button(
                self.sidebar,
                text=section,
                anchor="w",
                bg="#1f1724",
                fg="#f6ebf0",
                activebackground="#e76f51",
                activeforeground="#1a0f13",
                relief=tk.FLAT,
                font=("DejaVu Sans", 12),
                command=lambda s=section: self.show_view(s),
            )
            btn.pack(fill=tk.X, padx=10, pady=2, ipady=8)

    def _build_views(self) -> None:
        self.views["Connections"] = self._build_connections_view()
        self.views["Sessions"] = self._build_sessions_view()
        self.views["Kanban"] = self._build_kanban_view()
        self.views["Skills"] = self._build_skills_view()
        self.views["Cron"] = self._build_cron_view()
        self.views["Files"] = self._build_files_view()
        self.views["Terminal"] = self._build_terminal_view()

        for view in self.views.values():
            view.place(in_=self.content, x=0, y=0, relwidth=1, relheight=1)

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self, bg="#1a141f", height=28)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(bar, textvariable=self.status_text, bg="#1a141f", fg="#ccb8c3", anchor="w").pack(
            side=tk.LEFT, padx=10
        )

    def _header(self, parent: tk.Widget, title: str, subtitle: str) -> None:
        tk.Label(parent, text=title, bg="#141015", fg="#f6ebf0", font=("DejaVu Sans", 20, "bold")).pack(
            anchor="w", padx=20, pady=(20, 4)
        )
        tk.Label(parent, text=subtitle, bg="#141015", fg="#b8a7b2", font=("DejaVu Sans", 10)).pack(
            anchor="w", padx=20, pady=(0, 12)
        )

    def _build_connections_view(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg="#141015")
        self._header(frame, "Connections", "Saved SSH/Orgo profiles for Ubuntu desktop use")

        table_wrap = tk.Frame(frame, bg="#141015")
        table_wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

        self.conn_tree = ttk.Treeview(table_wrap, columns=("transport", "host", "user", "port"), show="headings")
        for col, width in [("transport", 110), ("host", 300), ("user", 180), ("port", 80)]:
            self.conn_tree.heading(col, text=col.capitalize())
            self.conn_tree.column(col, width=width, anchor="w")
        self.conn_tree.pack(fill=tk.BOTH, expand=True)

        form = tk.Frame(frame, bg="#141015")
        form.pack(fill=tk.X, padx=20, pady=(0, 16))
        self.conn_name = self._labeled_entry(form, "Name", 0)
        self.conn_transport = self._labeled_entry(form, "Transport (ssh|orgo)", 1)
        self.conn_host = self._labeled_entry(form, "Host / Computer ID", 2)
        self.conn_user = self._labeled_entry(form, "User", 3)
        self.conn_port = self._labeled_entry(form, "Port", 4)

        actions = tk.Frame(frame, bg="#141015")
        actions.pack(fill=tk.X, padx=20, pady=(0, 20))
        tk.Button(actions, text="Save Connection", command=self._save_connection, bg="#e76f51", fg="#1a0f13").pack(side=tk.LEFT)
        tk.Button(actions, text="Delete Selected", command=self._delete_connection, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        tk.Button(actions, text="Set Active", command=self._set_active_connection, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        tk.Button(actions, text="Test Connection", command=self._test_connection, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        tk.Button(actions, text="Fetch Orgo Workspaces", command=self._fetch_orgo_workspaces, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        tk.Button(actions, text="Export Profiles", command=self._export_profiles, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        tk.Button(actions, text="Import Profiles", command=self._import_profiles, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        tk.Label(actions, text="Active:", bg="#141015", fg="#ccb8c3").pack(side=tk.LEFT, padx=(16, 4))
        tk.Label(actions, textvariable=self.active_connection_name, bg="#141015", fg="#f6ebf0").pack(side=tk.LEFT)

        orgo_row = tk.Frame(frame, bg="#141015")
        orgo_row.pack(fill=tk.X, padx=20, pady=(0, 10))
        tk.Label(orgo_row, text="Orgo API Key", bg="#141015", fg="#d6c6d0", font=("DejaVu Sans", 10)).pack(side=tk.LEFT)
        self.orgo_api_key_entry = tk.Entry(
            orgo_row,
            width=46,
            bg="#251c2b",
            fg="#f6ebf0",
            insertbackground="#f6ebf0",
            relief=tk.FLAT,
            show="*",
        )
        self.orgo_api_key_entry.pack(side=tk.LEFT, padx=(10, 8))
        self.orgo_api_key_entry.insert(0, self._load_orgo_api_key())
        tk.Button(orgo_row, text="Save Key", command=self._save_orgo_api_key, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT)

        create_row = tk.Frame(frame, bg="#141015")
        create_row.pack(fill=tk.X, padx=20, pady=(0, 10))
        tk.Label(create_row, text="Workspace ID", bg="#141015", fg="#d6c6d0", font=("DejaVu Sans", 10)).pack(side=tk.LEFT)
        self.orgo_workspace_id_entry = tk.Entry(
            create_row,
            width=24,
            bg="#251c2b",
            fg="#f6ebf0",
            insertbackground="#f6ebf0",
            relief=tk.FLAT,
        )
        self.orgo_workspace_id_entry.pack(side=tk.LEFT, padx=(10, 8))
        tk.Label(create_row, text="Computer Name", bg="#141015", fg="#d6c6d0", font=("DejaVu Sans", 10)).pack(side=tk.LEFT)
        self.orgo_computer_name_entry = tk.Entry(
            create_row,
            width=26,
            bg="#251c2b",
            fg="#f6ebf0",
            insertbackground="#f6ebf0",
            relief=tk.FLAT,
        )
        self.orgo_computer_name_entry.pack(side=tk.LEFT, padx=(10, 8))
        tk.Button(create_row, text="Create Computer", command=self._create_orgo_computer, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT)

        tk.Label(frame, text="Orgo Workspaces", bg="#141015", fg="#d6c6d0", font=("DejaVu Sans", 10)).pack(anchor="w", padx=20)
        self.orgo_workspaces_tree = ttk.Treeview(frame, columns=("name", "id", "computers"), show="headings", height=5)
        self.orgo_workspaces_tree.heading("name", text="Workspace")
        self.orgo_workspaces_tree.heading("id", text="Workspace ID")
        self.orgo_workspaces_tree.heading("computers", text="# Computers")
        self.orgo_workspaces_tree.column("name", width=240, anchor="w")
        self.orgo_workspaces_tree.column("id", width=320, anchor="w")
        self.orgo_workspaces_tree.column("computers", width=110, anchor="w")
        self.orgo_workspaces_tree.pack(fill=tk.X, padx=20, pady=(0, 8))
        self.orgo_workspaces_tree.bind("<<TreeviewSelect>>", self._on_orgo_workspace_select)

        tk.Label(frame, text="Orgo Computers", bg="#141015", fg="#d6c6d0", font=("DejaVu Sans", 10)).pack(anchor="w", padx=20)
        self.orgo_computers_tree = ttk.Treeview(frame, columns=("name", "id", "status"), show="headings", height=6)
        self.orgo_computers_tree.heading("name", text="Computer")
        self.orgo_computers_tree.heading("id", text="Computer ID")
        self.orgo_computers_tree.heading("status", text="Status")
        self.orgo_computers_tree.column("name", width=220, anchor="w")
        self.orgo_computers_tree.column("id", width=360, anchor="w")
        self.orgo_computers_tree.column("status", width=110, anchor="w")
        self.orgo_computers_tree.pack(fill=tk.X, padx=20, pady=(0, 10))

        map_row = tk.Frame(frame, bg="#141015")
        map_row.pack(fill=tk.X, padx=20, pady=(0, 12))
        tk.Button(
            map_row,
            text="Use Selected Computer in Connection",
            command=self._apply_selected_orgo_computer_to_connection,
            bg="#3a2c43",
            fg="#f6ebf0",
        ).pack(side=tk.LEFT)
        tk.Button(
            map_row,
            text="Create Connection from Selected Computer",
            command=self._create_connection_from_selected_orgo_computer,
            bg="#3a2c43",
            fg="#f6ebf0",
        ).pack(side=tk.LEFT, padx=8)

        self._refresh_connections_table()
        return frame

    def _build_sessions_view(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg="#141015")
        self._header(frame, "Sessions", "Create and track sessions tied to connection profiles")

        self.session_tree = ttk.Treeview(frame, columns=("title", "connection"), show="headings")
        self.session_tree.heading("title", text="Title")
        self.session_tree.heading("connection", text="Connection")
        self.session_tree.column("title", width=360, anchor="w")
        self.session_tree.column("connection", width=220, anchor="w")
        self.session_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        self.session_tree.bind("<<TreeviewSelect>>", self._on_session_select)

        form = tk.Frame(frame, bg="#141015")
        form.pack(fill=tk.X, padx=20, pady=(0, 8))
        self.session_title = self._labeled_entry(form, "Title", 0)
        self.session_connection = self._labeled_entry(form, "Connection name", 1)

        tk.Label(frame, text="Notes", bg="#141015", fg="#d6c6d0", font=("DejaVu Sans", 10)).pack(anchor="w", padx=20)
        self.session_notes = tk.Text(frame, height=8, bg="#19141d", fg="#f6ebf0", insertbackground="#f6ebf0")
        self.session_notes.pack(fill=tk.X, padx=20, pady=(0, 10))

        actions = tk.Frame(frame, bg="#141015")
        actions.pack(fill=tk.X, padx=20, pady=(0, 20))
        tk.Button(actions, text="Save Session", command=self._save_session, bg="#e76f51", fg="#1a0f13").pack(side=tk.LEFT)
        tk.Button(actions, text="Delete Selected", command=self._delete_session, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        self._refresh_sessions_table()
        return frame

    def _build_kanban_view(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg="#141015")
        self._header(frame, "Kanban", "Track tasks across Todo / Doing / Done")

        self.kanban_tree = ttk.Treeview(frame, columns=("title", "status"), show="headings")
        self.kanban_tree.heading("title", text="Task")
        self.kanban_tree.heading("status", text="Status")
        self.kanban_tree.column("title", width=420, anchor="w")
        self.kanban_tree.column("status", width=140, anchor="w")
        self.kanban_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        form = tk.Frame(frame, bg="#141015")
        form.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.kanban_title = self._labeled_entry(form, "Task", 0)
        self.kanban_status = self._labeled_entry(form, "Status (Todo|Doing|Done)", 1)

        actions = tk.Frame(frame, bg="#141015")
        actions.pack(fill=tk.X, padx=20, pady=(0, 20))
        tk.Button(actions, text="Save Task", command=self._save_kanban, bg="#e76f51", fg="#1a0f13").pack(side=tk.LEFT)
        tk.Button(actions, text="Delete Selected", command=self._delete_kanban, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        self._refresh_kanban_table()
        return frame

    def _build_skills_view(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg="#141015")
        self._header(frame, "Skills", "Store reusable agent skills and summaries")

        self.skills_tree = ttk.Treeview(frame, columns=("name", "summary"), show="headings")
        self.skills_tree.heading("name", text="Name")
        self.skills_tree.heading("summary", text="Summary")
        self.skills_tree.column("name", width=220, anchor="w")
        self.skills_tree.column("summary", width=500, anchor="w")
        self.skills_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        form = tk.Frame(frame, bg="#141015")
        form.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.skill_name = self._labeled_entry(form, "Name", 0)
        self.skill_summary = self._labeled_entry(form, "Summary", 1)

        actions = tk.Frame(frame, bg="#141015")
        actions.pack(fill=tk.X, padx=20, pady=(0, 20))
        tk.Button(actions, text="Save Skill", command=self._save_skill, bg="#e76f51", fg="#1a0f13").pack(side=tk.LEFT)
        tk.Button(actions, text="Delete Selected", command=self._delete_skill, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        self._refresh_skills_table()
        return frame

    def _build_cron_view(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg="#141015")
        self._header(frame, "Cron", "Manage scheduled commands")

        self.cron_tree = ttk.Treeview(frame, columns=("schedule", "command"), show="headings")
        self.cron_tree.heading("schedule", text="Schedule")
        self.cron_tree.heading("command", text="Command")
        self.cron_tree.column("schedule", width=180, anchor="w")
        self.cron_tree.column("command", width=520, anchor="w")
        self.cron_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        form = tk.Frame(frame, bg="#141015")
        form.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.cron_schedule = self._labeled_entry(form, "Schedule (e.g. */15 * * * *)", 0)
        self.cron_command = self._labeled_entry(form, "Command", 1)

        actions = tk.Frame(frame, bg="#141015")
        actions.pack(fill=tk.X, padx=20, pady=(0, 20))
        tk.Button(actions, text="Save Job", command=self._save_cron, bg="#e76f51", fg="#1a0f13").pack(side=tk.LEFT)
        tk.Button(actions, text="Delete Selected", command=self._delete_cron, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        self._refresh_cron_table()
        return frame

    def _labeled_entry(self, parent: tk.Widget, label: str, row: int) -> tk.Entry:
        tk.Label(parent, text=label, bg="#141015", fg="#d6c6d0", font=("DejaVu Sans", 10)).grid(row=row, column=0, sticky="w", pady=3)
        entry = tk.Entry(parent, width=44, bg="#251c2b", fg="#f6ebf0", insertbackground="#f6ebf0", relief=tk.FLAT)
        entry.grid(row=row, column=1, sticky="we", pady=3, padx=(12, 0))
        return entry

    def _build_files_view(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg="#141015")
        self._header(frame, "Files", "Open, edit, and save workspace files locally on Ubuntu")

        top = tk.Frame(frame, bg="#141015")
        top.pack(fill=tk.X, padx=20, pady=(0, 8))
        tk.Button(top, text="Open File", command=self._open_file, bg="#e76f51", fg="#1a0f13").pack(side=tk.LEFT)
        tk.Button(top, text="Save", command=self._save_file, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=8)
        self.file_path_label = tk.Label(top, text="No file selected", bg="#141015", fg="#b8a7b2")
        self.file_path_label.pack(side=tk.LEFT, padx=12)

        self.file_text = tk.Text(frame, wrap="none", bg="#19141d", fg="#f6ebf0", insertbackground="#f6ebf0")
        self.file_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        return frame

    def _build_terminal_view(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg="#141015")
        self._header(frame, "Terminal", "Run Ubuntu shell commands inside OS1 desktop")

        controls = tk.Frame(frame, bg="#141015")
        controls.pack(fill=tk.X, padx=20, pady=(0, 8))
        self.cmd_entry = tk.Entry(controls, bg="#251c2b", fg="#f6ebf0", insertbackground="#f6ebf0", relief=tk.FLAT)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cmd_entry.bind("<Return>", lambda _e: self._run_command())
        tk.Button(controls, text="Run", command=self._run_command, bg="#e76f51", fg="#1a0f13").pack(side=tk.LEFT, padx=8)
        tk.Button(controls, text="Run on Active Host", command=self._run_command_remote, bg="#3a2c43", fg="#f6ebf0").pack(side=tk.LEFT, padx=4)

        notice = "Safe mode: blocked commands include sudo/rm/chmod/chown/dd/mkfs/shutdown/reboot by default."
        tk.Label(frame, text=notice, bg="#141015", fg="#b8a7b2", font=("DejaVu Sans", 9)).pack(anchor="w", padx=20)

        self.terminal_output = tk.Text(frame, wrap="word", bg="#0f0c12", fg="#e9fce8", insertbackground="#e9fce8")
        self.terminal_output.pack(fill=tk.BOTH, expand=True, padx=20, pady=(8, 20))
        self.terminal_output.insert(tk.END, "$ ready\n")
        return frame

    def _placeholder_view(self, title: str, subtitle: str) -> tk.Frame:
        frame = tk.Frame(self.content, bg="#141015")
        self._header(frame, title, subtitle)
        card = tk.Frame(frame, bg="#201927")
        card.pack(fill=tk.BOTH, expand=False, padx=20, pady=20)
        tk.Label(
            card,
            text="UI shell complete. Data/service wiring is the next step.",
            bg="#201927",
            fg="#f6ebf0",
            font=("DejaVu Sans", 12),
            padx=16,
            pady=16,
        ).pack(anchor="w")
        return frame

    def show_view(self, name: str) -> None:
        self.views[name].tkraise()

    def _load_connections(self) -> list[Connection]:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if not CONNECTIONS_FILE.exists():
            return []
        try:
            data = json.loads(CONNECTIONS_FILE.read_text(encoding="utf-8"))
            return [Connection(**item) for item in data]
        except Exception:
            return []

    def _write_connections(self) -> None:
        payload = [asdict(c) for c in self.connections]
        CONNECTIONS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_items(self, file_path: pathlib.Path, item_type):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            return []
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            return [item_type(**item) for item in payload]
        except Exception:
            return []

    def _write_items(self, file_path: pathlib.Path, items: list) -> None:
        payload = [asdict(item) for item in items]
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_settings(self) -> dict:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        settings = {}
        if not SETTINGS_FILE.exists():
            settings = {}
        else:
            try:
                settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                settings = {}

        if os.environ.get("OS1_DISALLOW_PLAINTEXT_KEY_FALLBACK", "").lower() in {"1", "true", "yes"}:
            settings["disallow_plaintext_key_fallback"] = True
        return settings

    def _maybe_show_first_run_wizard(self) -> None:
        if self.settings.get("first_run_completed"):
            return
        run = messagebox.askyesno(
            "Welcome to OS1 Ubuntu UI",
            "Run quick setup now?\n\n"
            "This will guide you through:\n"
            "1) Saving Orgo API key\n"
            "2) Fetching workspaces\n"
            "3) Creating first Orgo connection",
        )
        if not run:
            self.settings["first_run_completed"] = True
            self._write_settings()
            return
        self._run_first_setup_flow()

    def _run_first_setup_flow(self) -> None:
        self.show_view("Connections")
        if not self._load_orgo_api_key().strip():
            messagebox.showinfo(
                "Step 1",
                "Paste your Orgo API key in the Connections tab and click Save Key, then click OK here.",
            )

        self._fetch_orgo_workspaces()
        messagebox.showinfo(
            "Step 2",
            "Workspaces were requested. Select a workspace and computer, then click\n"
            "'Create Connection from Selected Computer'.",
        )
        self.settings["first_run_completed"] = True
        self._write_settings()

    def _write_settings(self) -> None:
        SETTINGS_FILE.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
        try:
            SETTINGS_FILE.chmod(0o600)
        except Exception:
            pass

    def _refresh_connections_table(self) -> None:
        for row in self.conn_tree.get_children():
            self.conn_tree.delete(row)
        for idx, conn in enumerate(self.connections):
            self.conn_tree.insert("", tk.END, iid=str(idx), values=(conn.transport, conn.host, conn.user, conn.port))

    def _selected_connection(self) -> Connection | None:
        selected = self.conn_tree.selection()
        if not selected:
            return None
        idx = int(selected[0])
        if idx >= len(self.connections):
            return None
        return self.connections[idx]

    def _save_connection(self) -> None:
        name = self.conn_name.get().strip()
        transport = self.conn_transport.get().strip().lower()
        host = self.conn_host.get().strip()
        user = self.conn_user.get().strip()
        port = self.conn_port.get().strip()

        if not name or transport not in {"ssh", "orgo"} or not host:
            messagebox.showerror("Invalid connection", "Provide name, transport (ssh|orgo), and host/computer id.")
            return

        self.connections = [c for c in self.connections if c.name != name]
        self.connections.append(Connection(name=name, transport=transport, host=host, user=user, port=port))
        self._write_connections()
        self._refresh_connections_table()

    def _delete_connection(self) -> None:
        selected = self.conn_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx < len(self.connections):
            del self.connections[idx]
            self._write_connections()
            self._refresh_connections_table()
            if self.active_connection_name.get() and self.active_connection_name.get() not in {c.name for c in self.connections}:
                self.active_connection_name.set("")
                self.status_text.set("active connection cleared")

    def _set_active_connection(self) -> None:
        conn = self._selected_connection()
        if conn is None:
            messagebox.showinfo("No selection", "Select a connection first.")
            return
        self.active_connection_name.set(conn.name)
        self.status_text.set(f"active connection: {conn.name}")

    def _selected_connection_index(self) -> int | None:
        selected = self.conn_tree.selection()
        if not selected:
            return None
        idx = int(selected[0])
        if idx >= len(self.connections):
            return None
        return idx

    def _save_orgo_api_key(self) -> None:
        key = self.orgo_api_key_entry.get().strip()
        if self._store_orgo_api_key(key):
            self.status_text.set("saved Orgo API key")
        else:
            self.status_text.set("failed to save Orgo API key")

    def _fetch_orgo_workspaces(self) -> None:
        key = self._load_orgo_api_key().strip()
        if not key:
            messagebox.showerror("Missing API key", "Enter and save an Orgo API key first.")
            return

        self.status_text.set("fetching Orgo workspaces...")

        def worker() -> None:
            request = urllib.request.Request(
                "https://www.orgo.ai/api/projects",
                headers={"Authorization": f"Bearer {key}"},
                method="GET",
            )
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                projects = payload.get("projects", [])
                self.after(0, lambda: self._set_orgo_workspace_data(projects, "fetched Orgo workspaces"))
            except urllib.error.HTTPError as exc:
                message = self._decode_http_error(exc)
                self.after(0, lambda: self._set_orgo_workspace_data([], message))
            except Exception as exc:
                message = f"Orgo request failed: {exc}"
                self.after(0, lambda: self._set_orgo_workspace_data([], message))

        threading.Thread(target=worker, daemon=True).start()

    def _create_orgo_computer(self) -> None:
        key = self._load_orgo_api_key().strip()
        workspace_id = self.orgo_workspace_id_entry.get().strip()
        computer_name = self.orgo_computer_name_entry.get().strip()

        if not key:
            messagebox.showerror("Missing API key", "Enter and save an Orgo API key first.")
            return
        if not workspace_id or not computer_name:
            messagebox.showerror("Missing fields", "Workspace ID and computer name are required.")
            return

        payload = {
            "workspace_id": workspace_id,
            "name": computer_name,
            "os": "linux",
            "ram": 8,
            "cpu": 4,
            "gpu": "none",
            "disk_size_gb": 50,
            "resolution": "1280x720x24",
        }
        data = json.dumps(payload).encode("utf-8")
        self.status_text.set("creating Orgo computer...")

        def worker() -> None:
            request = urllib.request.Request(
                "https://www.orgo.ai/api/computers",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                data=data,
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    created = json.loads(response.read().decode("utf-8"))
                cid = created.get("id", "unknown-id")
                cname = created.get("name") or computer_name
                status = created.get("status", "creating")
                msg = f"Created computer: {cname} ({cid}) status={status}"
                self.after(0, lambda: self.status_text.set(msg))
                self.after(0, self._fetch_orgo_workspaces)
            except urllib.error.HTTPError as exc:
                message = self._decode_http_error(exc)
                self.after(0, lambda: self.status_text.set(message))
            except Exception as exc:
                message = f"Orgo create failed: {exc}"
                self.after(0, lambda: self.status_text.set(message))

        threading.Thread(target=worker, daemon=True).start()

    def _set_orgo_workspaces_output(self, text: str, status: str) -> None:
        # Backward-compatible shim kept for old call sites.
        self._set_orgo_workspace_data([], status if text else status)
        self.status_text.set(status)

    def _set_orgo_workspace_data(self, projects: list[dict], status: str) -> None:
        self.orgo_workspace_rows = []
        self.orgo_computer_rows = []
        for row in self.orgo_workspaces_tree.get_children():
            self.orgo_workspaces_tree.delete(row)
        for row in self.orgo_computers_tree.get_children():
            self.orgo_computers_tree.delete(row)

        for idx, project in enumerate(projects):
            desktops = project.get("desktops") or []
            row = {
                "name": project.get("name", "Untitled"),
                "id": project.get("id", "unknown-id"),
                "desktops": desktops,
            }
            self.orgo_workspace_rows.append(row)
            self.orgo_workspaces_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(row["name"], row["id"], len(desktops)),
            )
        self.status_text.set(status)

    def _decode_http_error(self, exc: urllib.error.HTTPError) -> str:
        detail = ""
        try:
            raw = exc.read().decode("utf-8", errors="replace").strip()
            if raw:
                try:
                    payload = json.loads(raw)
                    detail = payload.get("error") or payload.get("message") or raw
                except Exception:
                    detail = raw
        except Exception:
            detail = ""
        if detail:
            return f"Orgo API error {exc.code}: {detail}"
        return f"Orgo API error {exc.code}"

    def _export_profiles(self) -> None:
        target = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="os1-ubuntu-profiles.json",
        )
        if not target:
            return
        payload = {
            "connections": [asdict(c) for c in self.connections],
            "sessions": [asdict(s) for s in self.sessions],
            "kanban": [asdict(k) for k in self.kanban_tasks],
            "skills": [asdict(s) for s in self.skills],
            "cron": [asdict(c) for c in self.cron_jobs],
        }
        try:
            pathlib.Path(target).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self.status_text.set(f"exported profiles to {target}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def _import_profiles(self) -> None:
        source = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not source:
            return
        try:
            payload = json.loads(pathlib.Path(source).read_text(encoding="utf-8"))
            imported_connections = [Connection(**item) for item in payload.get("connections", [])]
            imported_sessions = [SessionItem(**item) for item in payload.get("sessions", [])]
            imported_kanban = [KanbanTask(**item) for item in payload.get("kanban", [])]
            imported_skills = [SkillItem(**item) for item in payload.get("skills", [])]
            imported_cron = [CronItem(**item) for item in payload.get("cron", [])]
        except Exception as exc:
            messagebox.showerror("Import failed", f"Invalid profile file: {exc}")
            return

        self.connections = imported_connections
        self.sessions = imported_sessions
        self.kanban_tasks = imported_kanban
        self.skills = imported_skills
        self.cron_jobs = imported_cron

        self._write_connections()
        self._write_items(SESSIONS_FILE, self.sessions)
        self._write_items(KANBAN_FILE, self.kanban_tasks)
        self._write_items(SKILLS_FILE, self.skills)
        self._write_items(CRON_FILE, self.cron_jobs)
        self._refresh_connections_table()
        self._refresh_sessions_table()
        self._refresh_kanban_table()
        self._refresh_skills_table()
        self._refresh_cron_table()
        self.status_text.set(f"imported profiles from {source}")

    def _on_orgo_workspace_select(self, _event=None) -> None:
        selected = self.orgo_workspaces_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx >= len(self.orgo_workspace_rows):
            return
        workspace = self.orgo_workspace_rows[idx]
        self.orgo_workspace_id_entry.delete(0, tk.END)
        self.orgo_workspace_id_entry.insert(0, workspace["id"])

        for row in self.orgo_computers_tree.get_children():
            self.orgo_computers_tree.delete(row)
        self.orgo_computer_rows = []

        desktops = workspace.get("desktops", [])
        for cidx, desktop in enumerate(desktops):
            comp = {
                "name": desktop.get("name") or "Untitled",
                "id": desktop.get("id", "unknown-id"),
                "status": desktop.get("status", "unknown"),
            }
            self.orgo_computer_rows.append(comp)
            self.orgo_computers_tree.insert(
                "",
                tk.END,
                iid=str(cidx),
                values=(comp["name"], comp["id"], comp["status"]),
            )

    def _apply_selected_orgo_computer_to_connection(self) -> None:
        selected_computer = self.orgo_computers_tree.selection()
        if not selected_computer:
            messagebox.showinfo("No computer selected", "Select an Orgo computer first.")
            return
        cidx = int(selected_computer[0])
        if cidx >= len(self.orgo_computer_rows):
            return
        comp = self.orgo_computer_rows[cidx]

        idx = self._selected_connection_index()
        if idx is None:
            messagebox.showinfo("No connection selected", "Select an Orgo connection row first.")
            return
        current = self.connections[idx]
        if current.transport != "orgo":
            messagebox.showerror("Wrong transport", "Selected connection is not an Orgo transport.")
            return

        self.connections[idx] = Connection(
            name=current.name,
            transport=current.transport,
            host=comp["id"],
            user=current.user,
            port=current.port,
        )
        self.conn_host.delete(0, tk.END)
        self.conn_host.insert(0, comp["id"])
        self._write_connections()
        self._refresh_connections_table()
        self.status_text.set(f"mapped {comp['id']} to connection {current.name}")

    def _create_connection_from_selected_orgo_computer(self) -> None:
        selected_workspace = self.orgo_workspaces_tree.selection()
        selected_computer = self.orgo_computers_tree.selection()
        if not selected_workspace or not selected_computer:
            messagebox.showinfo("Selection required", "Select an Orgo workspace and computer first.")
            return

        widx = int(selected_workspace[0])
        cidx = int(selected_computer[0])
        if widx >= len(self.orgo_workspace_rows) or cidx >= len(self.orgo_computer_rows):
            return

        workspace = self.orgo_workspace_rows[widx]
        computer = self.orgo_computer_rows[cidx]
        base_name = f"orgo-{workspace['name']}-{computer['name']}".replace(" ", "-").lower()
        connection_name = base_name
        counter = 1
        existing_names = {c.name for c in self.connections}
        while connection_name in existing_names:
            counter += 1
            connection_name = f"{base_name}-{counter}"

        self.connections.append(
            Connection(
                name=connection_name,
                transport="orgo",
                host=computer["id"],
                user="",
                port="",
            )
        )
        self._write_connections()
        self._refresh_connections_table()
        self.status_text.set(f"created Orgo connection {connection_name}")

        # Prefill editor fields for visibility.
        self.conn_name.delete(0, tk.END)
        self.conn_name.insert(0, connection_name)
        self.conn_transport.delete(0, tk.END)
        self.conn_transport.insert(0, "orgo")
        self.conn_host.delete(0, tk.END)
        self.conn_host.insert(0, computer["id"])

    def _load_orgo_api_key(self) -> str:
        if shutil.which("secret-tool"):
            try:
                proc = subprocess.run(
                    [
                        "secret-tool",
                        "lookup",
                        "service",
                        SECRET_SERVICE,
                        "account",
                        SECRET_ACCOUNT,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    return proc.stdout.strip()
            except Exception:
                pass
        return self.settings.get("orgo_api_key", "")

    def _store_orgo_api_key(self, key: str) -> bool:
        disallow_plaintext_fallback = self.settings.get("disallow_plaintext_key_fallback", False)
        if shutil.which("secret-tool"):
            try:
                proc = subprocess.run(
                    [
                        "secret-tool",
                        "store",
                        "--label",
                        "OS1 Ubuntu Orgo API Key",
                        "service",
                        SECRET_SERVICE,
                        "account",
                        SECRET_ACCOUNT,
                    ],
                    input=key,
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                if proc.returncode == 0:
                    self.settings.pop("orgo_api_key", None)
                    self._write_settings()
                    return True
            except Exception:
                pass

        if disallow_plaintext_fallback:
            messagebox.showerror(
                "Keyring required",
                "secret-tool unavailable and plaintext fallback is disabled. Install libsecret tools or re-enable fallback.",
            )
            return False

        self.settings["orgo_api_key"] = key
        self._write_settings()
        messagebox.showwarning(
            "Keyring unavailable",
            "secret-tool not available; Orgo API key stored in ~/.config/os1-linux/settings.json (0600 best effort).",
        )
        return True

    def _connection_by_name(self, name: str) -> Connection | None:
        for conn in self.connections:
            if conn.name == name:
                return conn
        return None

    def _test_connection(self) -> None:
        conn = self._selected_connection()
        if conn is None:
            messagebox.showinfo("No selection", "Select a connection first.")
            return

        def done(message: str) -> None:
            self.status_text.set(message)
            messagebox.showinfo("Connection test", message)

        def worker() -> None:
            if conn.transport == "ssh":
                if shutil.which("ssh") is None:
                    self.after(0, lambda: done("ssh binary not found on system"))
                    return
                host = conn.host.strip()
                if not host:
                    self.after(0, lambda: done("missing ssh host"))
                    return
                user_prefix = f"{conn.user}@" if conn.user.strip() else ""
                port_args = ["-p", conn.port.strip()] if conn.port.strip() else []
                cmd = [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=8",
                    *port_args,
                    f"{user_prefix}{host}",
                    "echo ok",
                ]
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
                    if proc.returncode == 0:
                        self.after(0, lambda: done(f"ssh test passed for {conn.name}"))
                    else:
                        error = (proc.stderr or proc.stdout or "ssh test failed").strip()
                        self.after(0, lambda: done(f"ssh test failed: {error}"))
                except Exception as exc:
                    self.after(0, lambda: done(f"ssh test error: {exc}"))
                return

            if conn.transport == "orgo":
                has_key = bool((pathlib.Path.home() / ".config" / "os1-linux").exists())
                if has_key:
                    self.after(0, lambda: done("orgo profile saved (API validation wiring pending)"))
                else:
                    self.after(0, lambda: done("orgo profile incomplete"))
                return

            self.after(0, lambda: done("unknown transport type"))

        self.status_text.set(f"testing {conn.name}...")
        threading.Thread(target=worker, daemon=True).start()

    def _on_session_select(self, _event=None) -> None:
        selected = self.session_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx >= len(self.sessions):
            return
        item = self.sessions[idx]
        self.session_title.delete(0, tk.END)
        self.session_title.insert(0, item.title)
        self.session_connection.delete(0, tk.END)
        self.session_connection.insert(0, item.connection)
        self.session_notes.delete("1.0", tk.END)
        self.session_notes.insert("1.0", item.notes)

    def _refresh_sessions_table(self) -> None:
        for row in self.session_tree.get_children():
            self.session_tree.delete(row)
        for idx, session in enumerate(self.sessions):
            self.session_tree.insert("", tk.END, iid=str(idx), values=(session.title, session.connection))

    def _save_session(self) -> None:
        title = self.session_title.get().strip()
        connection = self.session_connection.get().strip()
        notes = self.session_notes.get("1.0", tk.END).strip()
        if not title:
            messagebox.showerror("Invalid session", "Session title is required.")
            return
        selected = self.session_tree.selection()
        if selected:
            idx = int(selected[0])
            self.sessions[idx] = SessionItem(id=self.sessions[idx].id, title=title, connection=connection, notes=notes)
        else:
            self.sessions.append(SessionItem(id=str(uuid.uuid4()), title=title, connection=connection, notes=notes))
        self._write_items(SESSIONS_FILE, self.sessions)
        self._refresh_sessions_table()

    def _delete_session(self) -> None:
        selected = self.session_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx < len(self.sessions):
            del self.sessions[idx]
            self._write_items(SESSIONS_FILE, self.sessions)
            self._refresh_sessions_table()

    def _refresh_kanban_table(self) -> None:
        for row in self.kanban_tree.get_children():
            self.kanban_tree.delete(row)
        for idx, item in enumerate(self.kanban_tasks):
            self.kanban_tree.insert("", tk.END, iid=str(idx), values=(item.title, item.status))

    def _save_kanban(self) -> None:
        title = self.kanban_title.get().strip()
        status = self.kanban_status.get().strip() or "Todo"
        if not title:
            messagebox.showerror("Invalid task", "Task title is required.")
            return
        selected = self.kanban_tree.selection()
        if selected:
            idx = int(selected[0])
            self.kanban_tasks[idx] = KanbanTask(id=self.kanban_tasks[idx].id, title=title, status=status)
        else:
            self.kanban_tasks.append(KanbanTask(id=str(uuid.uuid4()), title=title, status=status))
        self._write_items(KANBAN_FILE, self.kanban_tasks)
        self._refresh_kanban_table()

    def _delete_kanban(self) -> None:
        selected = self.kanban_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx < len(self.kanban_tasks):
            del self.kanban_tasks[idx]
            self._write_items(KANBAN_FILE, self.kanban_tasks)
            self._refresh_kanban_table()

    def _refresh_skills_table(self) -> None:
        for row in self.skills_tree.get_children():
            self.skills_tree.delete(row)
        for idx, skill in enumerate(self.skills):
            self.skills_tree.insert("", tk.END, iid=str(idx), values=(skill.name, skill.summary))

    def _save_skill(self) -> None:
        name = self.skill_name.get().strip()
        summary = self.skill_summary.get().strip()
        if not name:
            messagebox.showerror("Invalid skill", "Skill name is required.")
            return
        selected = self.skills_tree.selection()
        if selected:
            idx = int(selected[0])
            self.skills[idx] = SkillItem(id=self.skills[idx].id, name=name, summary=summary)
        else:
            self.skills.append(SkillItem(id=str(uuid.uuid4()), name=name, summary=summary))
        self._write_items(SKILLS_FILE, self.skills)
        self._refresh_skills_table()

    def _delete_skill(self) -> None:
        selected = self.skills_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx < len(self.skills):
            del self.skills[idx]
            self._write_items(SKILLS_FILE, self.skills)
            self._refresh_skills_table()

    def _refresh_cron_table(self) -> None:
        for row in self.cron_tree.get_children():
            self.cron_tree.delete(row)
        for idx, item in enumerate(self.cron_jobs):
            self.cron_tree.insert("", tk.END, iid=str(idx), values=(item.schedule, item.command))

    def _save_cron(self) -> None:
        schedule = self.cron_schedule.get().strip()
        command = self.cron_command.get().strip()
        if not schedule or not command:
            messagebox.showerror("Invalid cron job", "Schedule and command are required.")
            return
        selected = self.cron_tree.selection()
        if selected:
            idx = int(selected[0])
            self.cron_jobs[idx] = CronItem(id=self.cron_jobs[idx].id, schedule=schedule, command=command)
        else:
            self.cron_jobs.append(CronItem(id=str(uuid.uuid4()), schedule=schedule, command=command))
        self._write_items(CRON_FILE, self.cron_jobs)
        self._refresh_cron_table()

    def _delete_cron(self) -> None:
        selected = self.cron_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx < len(self.cron_jobs):
            del self.cron_jobs[idx]
            self._write_items(CRON_FILE, self.cron_jobs)
            self._refresh_cron_table()

    def _open_file(self) -> None:
        path = filedialog.askopenfilename()
        if not path:
            return
        file_path = pathlib.Path(path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))
            return
        self.current_file = file_path
        self.file_text.delete("1.0", tk.END)
        self.file_text.insert("1.0", content)
        self.file_path_label.config(text=str(file_path))

    def _save_file(self) -> None:
        if self.current_file is None:
            messagebox.showinfo("No file", "Open a file first.")
            return
        try:
            self.current_file.write_text(self.file_text.get("1.0", tk.END), encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        messagebox.showinfo("Saved", f"Saved {self.current_file}")

    def _run_command(self) -> None:
        command = self.cmd_entry.get().strip()
        if not command:
            return

        blocked_tokens = {"sudo", "rm", "chmod", "chown", "dd", "mkfs", "shutdown", "reboot", "poweroff"}
        tokens = shlex.split(command)
        if any(token in blocked_tokens for token in tokens):
            self._append_terminal(f"$ {command}\nblocked in safe mode\n")
            return

        self._append_terminal(f"$ {command}\n")
        self.cmd_entry.delete(0, tk.END)

        def worker() -> None:
            try:
                proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                output = proc.stdout + proc.stderr
                if not output.strip():
                    output = "(no output)\n"
                self.after(0, lambda: self._append_terminal(output))
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self._append_terminal("command timed out after 30s\n"))
            except Exception as exc:
                self.after(0, lambda: self._append_terminal(f"error: {exc}\n"))

        threading.Thread(target=worker, daemon=True).start()

    def _run_command_remote(self) -> None:
        command = self.cmd_entry.get().strip()
        if not command:
            return

        conn_name = self.active_connection_name.get().strip()
        conn = self._connection_by_name(conn_name) if conn_name else None
        if conn is None:
            messagebox.showinfo("No active connection", "Set an active connection in Connections first.")
            return
        if conn.transport != "ssh":
            messagebox.showinfo("Unsupported transport", "Remote execution currently supports SSH connections.")
            return
        if shutil.which("ssh") is None:
            messagebox.showerror("Missing ssh", "ssh binary not found on this system.")
            return

        blocked_tokens = {"sudo", "rm", "chmod", "chown", "dd", "mkfs", "shutdown", "reboot", "poweroff"}
        tokens = shlex.split(command)
        if any(token in blocked_tokens for token in tokens):
            self._append_terminal(f"$[{conn.name}] {command}\nblocked in safe mode\n")
            return

        user_prefix = f"{conn.user}@" if conn.user.strip() else ""
        port_args = ["-p", conn.port.strip()] if conn.port.strip() else []
        ssh_cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            *port_args,
            f"{user_prefix}{conn.host}",
            command,
        ]
        self._append_terminal(f"$[{conn.name}] {command}\n")
        self.cmd_entry.delete(0, tk.END)

        def worker() -> None:
            try:
                proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
                output = proc.stdout + proc.stderr
                if not output.strip():
                    output = "(no output)\n"
                self.after(0, lambda: self._append_terminal(output))
                self.after(0, lambda: self.status_text.set(f"remote command exit code: {proc.returncode}"))
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self._append_terminal("remote command timed out after 30s\n"))
            except Exception as exc:
                self.after(0, lambda: self._append_terminal(f"remote error: {exc}\n"))

        threading.Thread(target=worker, daemon=True).start()

    def _append_terminal(self, text: str) -> None:
        self.terminal_output.insert(tk.END, text)
        self.terminal_output.see(tk.END)


def main() -> None:
    app = OS1UbuntuUI()
    app.mainloop()


if __name__ == "__main__":
    main()
