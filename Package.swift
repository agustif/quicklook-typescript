// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "QuickLookTypeScript",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "PreviewCore", path: "Sources/PreviewCore"),
        .testTarget(name: "PreviewCoreTests", dependencies: ["PreviewCore"], path: "Tests/PreviewCoreTests"),
    ]
)
