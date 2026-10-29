"""Shared bundle metadata for building and installing the Quick Look extension."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "TypeScript Quick Look.app"
APP_IDENTIFIER = "io.github.agustif.quicklook-typescript"
EXTENSION_IDENTIFIER = f"{APP_IDENTIFIER}.Preview"
EXTENSION_NAME = "TypeScriptPreview.appex"
MINIMUM_MACOS = "14.0"
VERSION = "0.1.0"
LEGACY_IDENTIFIER = "local.af.TypeScriptQuickLook"
LSREGISTER = Path(
    "/System/Library/Frameworks/CoreServices.framework/Frameworks/"
    "LaunchServices.framework/Support/lsregister"
)
