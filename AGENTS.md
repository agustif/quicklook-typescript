# Working on quicklook-typescript

- Keep the repository name and links spelled `quicklook-typescript`.
- `swift test` validates the source reader; `python3 build.py --arch universal` builds and verifies both architectures.
- `just check` runs native tests and a native build. Xcode Command Line Tools and Python 3 are the only build requirements.
- Keep one Swift type per file. The core reader must remain independent of AppKit and AVKit.
- Preserve bounded reads, Unicode character boundaries, read-only source access, and binary-video detection.
- Use the real `public.mpeg-2-transport-stream` type. Do not redefine system UTIs or change editor associations.
- Keep extension sandboxing enabled. Adding network access, filesystem exceptions, or background helpers requires an explicit design decision.
- Finder routing requires a live macOS check. A successful build or `qlmanage` test alone does not establish Finder behavior.
- Document the macOS version used for UI verification. Older macOS releases may route reserved types differently.
- Keep build outputs, app bundles, signing material, logs, and machine-specific paths out of commits.
- Never create or commit `TASKS.md`.
