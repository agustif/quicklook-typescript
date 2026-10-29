#!/usr/bin/env python3
"""Build and locally sign a standalone macOS Quick Look app using Xcode tools."""
import argparse
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from project import (
    APP_IDENTIFIER, APP_NAME, EXTENSION_IDENTIFIER, EXTENSION_NAME,
    MINIMUM_MACOS, ROOT, VERSION,
)


def run(*arguments: str) -> None:
    print("+", " ".join(arguments), flush=True)
    subprocess.run(arguments, check=True)


def write_plist(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as output:
        plistlib.dump(value, output)


def compile_binary(destination: Path, sources: list[Path], architectures: list[str], extension: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    objects = []
    for architecture in architectures:
        binary = destination.parent / f".{destination.name}-{architecture}"
        command = [
            "xcrun", "swiftc", "-swift-version", "5", "-O",
            "-target", f"{architecture}-apple-macosx{MINIMUM_MACOS}",
            "-framework", "Cocoa",
        ]
        if extension:
            command.extend([
                "-module-name", "TypeScriptPreview", "-emit-executable", "-parse-as-library",
                "-framework", "Quartz", "-framework", "AVKit",
                "-Xlinker", "-e", "-Xlinker", "_NSExtensionMain",
            ])
        run(*command, *(str(source) for source in sources), "-o", str(binary))
        objects.append(binary)
    if len(objects) == 1:
        objects[0].replace(destination)
    else:
        run("xcrun", "lipo", "-create", *(str(binary) for binary in objects), "-output", str(destination))
        for binary in objects:
            binary.unlink()


def build(output: Path, architectures: list[str], identity: str) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    destination = output / APP_NAME
    if destination.exists():
        metadata_path = destination / "Contents/Info.plist"
        if destination.is_symlink() or not metadata_path.is_file():
            raise RuntimeError(f"Refusing to replace an unknown build output: {destination}")
        with metadata_path.open("rb") as metadata:
            if plistlib.load(metadata).get("CFBundleIdentifier") != APP_IDENTIFIER:
                raise RuntimeError(f"Another application already exists at {destination}")

    with tempfile.TemporaryDirectory(prefix=".quicklook-build-", dir=output) as temporary:
        staging = Path(temporary)
        app = staging / APP_NAME
        extension = app / "Contents/PlugIns" / EXTENSION_NAME
        shared = {
            "CFBundleInfoDictionaryVersion": "6.0", "CFBundleVersion": "1",
            "CFBundleShortVersionString": VERSION, "LSMinimumSystemVersion": MINIMUM_MACOS,
            "CFBundleSupportedPlatforms": ["MacOSX"],
        }
        write_plist(app / "Contents/Info.plist", {
            **shared, "CFBundleIdentifier": APP_IDENTIFIER,
            "CFBundleName": "TypeScript Quick Look", "CFBundleDisplayName": "TypeScript Quick Look",
            "CFBundleExecutable": "TypeScriptQuickLook", "CFBundlePackageType": "APPL", "LSUIElement": True,
        })
        write_plist(extension / "Contents/Info.plist", {
            **shared, "CFBundleIdentifier": EXTENSION_IDENTIFIER,
            "CFBundleName": "TypeScript source previews", "CFBundleDisplayName": "TypeScript source previews",
            "CFBundleExecutable": "TypeScriptPreview", "CFBundlePackageType": "XPC!",
            "NSExtension": {
                "NSExtensionPointIdentifier": "com.apple.quicklook.preview",
                "NSExtensionPrincipalClass": "TypeScriptPreview.PreviewViewController",
                "NSExtensionAttributes": {
                    "QLIsDataBasedPreview": False, "QLSupportsSearchableItems": False,
                    "QLSupportedContentTypes": ["public.mpeg-2-transport-stream"],
                },
            },
        })
        entitlements = staging / "entitlements.plist"
        write_plist(entitlements, {
            "com.apple.security.app-sandbox": True,
            "com.apple.security.files.user-selected.read-only": True,
        })
        compile_binary(extension / "Contents/MacOS/TypeScriptPreview", [
            ROOT / "Sources/PreviewCore/SourceContent.swift",
            ROOT / "Sources/PreviewExtension/PreviewViewController.swift",
        ], architectures, extension=True)
        compile_binary(app / "Contents/MacOS/TypeScriptQuickLook", [ROOT / "Sources/App/main.swift"], architectures, extension=False)

        # Include the exact source and rebuild tools without bundling local paths or artifacts.
        bundled_source = app / "Contents/Resources/Source"
        shutil.copytree(ROOT / "Sources", bundled_source / "Sources")
        for filename in ("build.py", "install.py", "project.py", "README.md", "LICENSE"):
            shutil.copy2(ROOT / filename, bundled_source / filename)
        for bundle in (extension, app):
            run("codesign", "--force", "--sign", identity, "--entitlements", str(entitlements), str(bundle))
        run("codesign", "--verify", "--deep", "--strict", str(app))
        if destination.exists():
            shutil.rmtree(destination)
        app.replace(destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=("native", "universal", "arm64", "x86_64"), default="native")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build")
    parser.add_argument("--sign-identity", default="-", help="codesign identity; defaults to local ad-hoc signing")
    arguments = parser.parse_args()
    if platform.system() != "Darwin" or shutil.which("xcrun") is None:
        parser.error("macOS with Xcode Command Line Tools or Xcode is required")
    architecture = platform.machine() if arguments.arch == "native" else arguments.arch
    architectures = ["arm64", "x86_64"] if architecture == "universal" else [architecture]
    if any(value not in ("arm64", "x86_64") for value in architectures):
        parser.error(f"Unsupported architecture: {architecture}")
    try:
        app = build(arguments.output_dir.expanduser().resolve(), architectures, arguments.sign_identity)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    print(f"Built {app}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
