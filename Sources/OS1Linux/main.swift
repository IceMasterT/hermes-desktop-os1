import Foundation

let message = """
OS1's current UI app target is macOS-only (SwiftUI + AppKit).

This Linux target is a compatibility entrypoint so the package builds on Ubuntu.
Next step for real Linux support: extract transport/services into a shared core module,
then implement a Linux UI (for example: Tauri/Electron/GTK) against that core.
"""

print(message)
