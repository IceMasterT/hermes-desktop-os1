// swift-tools-version: 6.1

import PackageDescription
import Foundation

let isLinux = ProcessInfo.processInfo.operatingSystemVersionString.lowercased().contains("linux")

let products: [Product] = isLinux
    ? [
        .executable(
            name: "OS1",
            targets: ["OS1Linux"]
        )
    ]
    : [
        .executable(
            name: "OS1",
            targets: ["OS1"]
        )
    ]

let dependencies: [Package.Dependency] = isLinux
    ? []
    : [
        .package(path: "Vendor/SwiftTerm")
    ]

let targets: [Target] = isLinux
    ? [
        .executableTarget(
            name: "OS1Linux",
            path: "Sources/OS1Linux"
        )
    ]
    : [
        .executableTarget(
            name: "OS1",
            dependencies: [
                .product(name: "SwiftTerm", package: "SwiftTerm")
            ],
            path: "Sources/OS1",
            resources: [
                .process("Resources")
            ]
        ),
        .testTarget(
            name: "OS1Tests",
            dependencies: ["OS1"],
            path: "Tests/OS1Tests"
        )
    ]

let package = Package(
    name: "OS1",
    defaultLocalization: "en",
    platforms: isLinux ? nil : [
        .macOS(.v14)
    ],
    products: products,
    dependencies: dependencies,
    targets: targets
)
