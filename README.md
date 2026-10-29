# quicklook-typescript

Preview TypeScript source with the normal **Space** key in Finder.

macOS identifies `.ts` files as `public.mpeg-2-transport-stream`, a video type.
Many code previewers claim a TypeScript UTI and never receive those files.
This app provides a **file-based Quick Look extension for the actual macOS type**.
Text appears as selectable, scrollable monospaced source in Finder's native Quick Look panel.

The extension is sandboxed, requests read-only access to user-selected files, and has no network entitlement or background helper.
It does not redefine system types, change your editor association, or execute the previewed source.

## Requirements

- macOS 14 or later.
- Xcode Command Line Tools or Xcode, with Swift 5.9 or later.
- Python 3.9 or later. No third-party Python or Swift packages are required.

Finder routing was verified on **macOS 27.0, Apple Silicon**.
The build supports `arm64`, `x86_64`, and universal binaries; builds and decoder tests do not establish Finder routing on older macOS releases.

## Build and install

```sh
git clone https://github.com/agustif/quicklook-typescript.git
cd quicklook-typescript
python3 build.py
python3 install.py
```

Then select a `.ts` file in Finder and press **Space**.

The installer writes `~/Applications/TypeScript Quick Look.app`, verifies its signature, registers the extension, and refreshes Quick Look.
An existing version of this app is backed up under `~/Library/Application Support/quicklook-typescript/Backups/`.
It refuses to replace an unrelated app at the same path.

If macOS shows the extension as disabled, enable **TypeScript source previews** in System Settings → General → Login Items & Extensions → Quick Look.
The exact settings labels vary by macOS version.

Build options:

```sh
python3 build.py --arch universal
python3 build.py --arch arm64 --output-dir /path/to/output
python3 build.py --sign-identity 'Developer ID Application: Your Name (TEAMID)'
python3 install.py --app '/path/to/output/TypeScript Quick Look.app'
```

The default is the current machine's architecture with local ad-hoc signing.
The app includes its source and rebuild scripts under `Contents/Resources/Source`.
Copy that directory outside the signed app before editing or rebuilding it.
Notarized downloads and automatic updates are not provided; build locally for this initial version.

## What it previews

- `.ts` source classified as `public.mpeg-2-transport-stream`.
- Other extensions, including `.mts`, when macOS resolves them to that same type.
- UTF-8, BOM-marked UTF-16 and UTF-32, and Windows-1252 fallback text.
- Up to the first **1 MiB** of source, preserving character boundaries and showing a truncation notice.

Source previews are plain monospaced text. Syntax coloring is not included.
Other programming-language formats remain with their existing previewers.

The reader uses a text/binary heuristic because genuine MPEG transport-stream videos also use `.ts`.
Binary content takes an `AVPlayerView` path; playback depends on the codecs available to AVFoundation.
This app does not supply video codecs or replace a general media previewer.

## Conflicting preview extensions

Quick Look extension selection is controlled by macOS.
Another extension claiming the same UTI may win even when this extension is enabled.

During development, **QuickLook Video 2.21** claimed `.ts` and took precedence.
Updating it to **3.12** removed its competing legacy Quick Look preview extension.
[QuickLook Video 3 uses AVFoundation Media Extensions](https://github.com/Marginal/QuickLookVideo/releases/tag/rel-312).
The installer does not update or disable unrelated applications.

Inspect registration:

```sh
pluginkit -m -vv -i io.github.agustif.quicklook-typescript.Preview
mdls -name kMDItemContentType /path/to/example.ts
```

An active user election starts with `+` in `pluginkit` output.
It is normal for `mdls` to continue reporting a video UTI: the extension handles that type directly.

The installer can migrate the original local prototype, `local.af.TypeScriptQuickLook`.
Its previous app is preserved, and only that known prototype's extension is disabled after installation succeeds.

## Validation

```sh
swift test
python3 -m unittest discover -s Tests/InstallerTests -v
python3 build.py --arch universal
```

If `just` is installed, `just check` runs tests and a native build.
CI tests bounded decoding, installer refusal and rollback, and a universal, locally signed app on macOS.

For UI verification, create a small `.ts` file, select it in Finder, and press Space.
Check that the source is readable and selectable and that the panel scrolls.
Also check an empty file, a large source file, and a real transport-stream video on the macOS version being supported.
`qlmanage -p /path/to/example.ts` is useful for debugging, but verify Finder separately.

Logs:

```sh
log show --last 5m --style compact \
  --predicate 'subsystem == "io.github.agustif.quicklook-typescript.Preview"'
```

The extension logs file extensions, completion, truncation, and errors. It does not log source contents.

## Uninstall

```sh
pluginkit -e ignore -i io.github.agustif.quicklook-typescript.Preview
```

Move `~/Applications/TypeScript Quick Look.app` to Trash in Finder, then run `qlmanage -r`.
Backups are separate and remain available for rollback.

## Architecture

| Path | Responsibility |
| --- | --- |
| `Sources/PreviewCore/SourceContent.swift` | Bounded reads, Unicode decoding, and text/binary classification |
| `Sources/PreviewExtension/PreviewViewController.swift` | Native source and video views; file-based Quick Look entry point |
| `Sources/App/main.swift` | Minimal containing application |
| `project.py` | Shared bundle identifiers, version, and platform metadata |
| `build.py` | Compilation, app packaging, architecture selection, and signing |
| `install.py` | Verified installation, backup, registration, and rollback on installation errors |
| `Tests/PreviewCoreTests` | Source decoding, size boundaries, video classification, and read-only behavior |
| `Tests/InstallerTests` | Refusal to replace unrelated apps, verified registration, and rollback after command failures |

The reader is tested through Swift Package Manager. The app and extension are compiled with `swiftc` and packaged as native bundles.
The extension implements Apple's [file-based Quick Look preview API](https://developer.apple.com/documentation/quicklookui/qlpreviewingcontroller).

## License

MIT. See [LICENSE](LICENSE).
