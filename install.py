#!/usr/bin/env python3
"""Install a verified local build, preserving the previous app as a backup."""
import argparse
from datetime import datetime, timezone
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from project import APP_IDENTIFIER, APP_NAME, EXTENSION_IDENTIFIER, EXTENSION_NAME, LEGACY_IDENTIFIER, LSREGISTER, ROOT


def bundle_identifier(app: Path) -> str:
    with (app / "Contents/Info.plist").open("rb") as metadata:
        return plistlib.load(metadata).get("CFBundleIdentifier", "")


def run(*arguments: str) -> None:
    subprocess.run(arguments, check=True)


def wait_for_registration(extension: Path) -> None:
    # macOS discovers app extensions asynchronously after the containing app opens.
    deadline = time.monotonic() + 8
    while True:
        registration = subprocess.run(
            ["pluginkit", "-m", "-A", "-v", "-i", EXTENSION_IDENTIFIER],
            check=True, capture_output=True, text=True,
        )
        if EXTENSION_IDENTIFIER in registration.stdout and str(extension) in registration.stdout:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError("macOS did not register the installed extension within 8 seconds")
        time.sleep(0.2)


def install(source: Path, applications: Path, backups: Path) -> Path:
    if source.is_symlink() or bundle_identifier(source) != APP_IDENTIFIER:
        raise RuntimeError(f"Not a quicklook-typescript build: {source}")
    run("codesign", "--verify", "--deep", "--strict", str(source))
    applications.mkdir(parents=True, exist_ok=True)
    destination = applications / APP_NAME
    if source.resolve() == destination.resolve():
        raise RuntimeError("Build and installation paths must be different")
    if destination.exists() and (
        destination.is_symlink() or bundle_identifier(destination) not in (APP_IDENTIFIER, LEGACY_IDENTIFIER)
    ):
        raise RuntimeError(f"Refusing to replace another application: {destination}")

    backup = None
    with tempfile.TemporaryDirectory(prefix=".quicklook-install-", dir=applications) as temporary:
        staged = Path(temporary) / APP_NAME
        run("ditto", str(source), str(staged))
        run("codesign", "--verify", "--deep", "--strict", str(staged))
        if destination.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backups.mkdir(parents=True, exist_ok=True)
            backup = backups / f"{stamp}-{APP_NAME}"
            shutil.move(str(destination), str(backup))
        try:
            staged.replace(destination)
            run(str(LSREGISTER), "-f", str(destination))
            # Opening the containing app lets macOS discover its embedded extension.
            run("open", str(destination))
            extension = destination / "Contents/PlugIns" / EXTENSION_NAME
            run("pluginkit", "-a", str(extension))
            wait_for_registration(extension)
            run("pluginkit", "-e", "use", "-i", EXTENSION_IDENTIFIER)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as installation_error:
            try:
                if destination.exists():
                    # A failed unregister must not prevent restoring the previous app.
                    try:
                        run(str(LSREGISTER), "-u", str(destination))
                    except (OSError, subprocess.CalledProcessError) as error:
                        print(f"Could not unregister the failed installation: {error}", file=sys.stderr)
                    shutil.rmtree(destination)
                if backup is not None and backup.exists():
                    shutil.move(str(backup), str(destination))
                    run(str(LSREGISTER), "-f", str(destination))
                    restored_extension = destination / "Contents/PlugIns" / EXTENSION_NAME
                    run("pluginkit", "-a", str(restored_extension))
                    run("pluginkit", "-e", "use", "-i", f"{bundle_identifier(destination)}.Preview")
            except (OSError, subprocess.CalledProcessError) as rollback_error:
                raise RuntimeError(
                    f"Installation failed and rollback needs attention: {rollback_error}; backup: {backup}"
                ) from installation_error
            raise
    if backup is not None:
        print(f"Previous app preserved at {backup}")
    # Disable only the known prototype ID; unrelated previewers remain user-controlled.
    run("pluginkit", "-e", "ignore", "-i", f"{LEGACY_IDENTIFIER}.Preview")
    run("qlmanage", "-r")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=ROOT / "build" / APP_NAME)
    parser.add_argument("--applications-dir", type=Path, default=Path.home() / "Applications")
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "Library/Application Support/quicklook-typescript/Backups")
    arguments = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("macOS is required")
    try:
        destination = install(
            arguments.app.expanduser().absolute(), arguments.applications_dir.expanduser().resolve(),
            arguments.backup_dir.expanduser().resolve(),
        )
    except (OSError, RuntimeError, plistlib.InvalidFileException, subprocess.CalledProcessError) as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        return 1
    print(f"Installed {destination}. Select a TypeScript file in Finder and press Space.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
