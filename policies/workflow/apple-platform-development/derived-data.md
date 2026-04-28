---
title: "DerivedData"
summary: "All Xcode project builds MUST land in the default DerivedData location (~/Library/Developer/Xcode/DerivedData/). Projects MUST NOT redirect build output into the repo or another custom path."
triggers: [creating-xcode-project, configuring-build-settings, xcodeproj-audit, build-output-debug, writing-build-script]
tags: [xcode, build, deriveddata, apple]
---

# DerivedData

All Xcode project builds MUST land in Xcode's default DerivedData location (`~/Library/Developer/Xcode/DerivedData/`). Projects MUST NOT redirect build output into the repo or another custom path.

## Why

- Build artefacts are machine-local and should never be committed. Keeping them in `~/Library/...` (outside every repo) makes that impossible by default — no `.gitignore` gymnastics required.
- Every project in the workspace resolves to the same canonical build root, so cross-project references and `xcodebuild` CLI invocations find each other's built products without path juggling.
- Cleaning is a one-liner (`rm -rf ~/Library/Developer/Xcode/DerivedData/<project>-<hash>`) and the Xcode UI's "Clean Build Folder" does the expected thing.

## What this means in practice

- Project / target build settings (and any `.xcconfig`) MUST NOT set any of these:
  `SYMROOT`, `OBJROOT`, `BUILD_DIR`, `CONFIGURATION_BUILD_DIR`, `BUILD_ROOT`, `DSTROOT`, `TARGET_BUILD_DIR`.
- `xcodebuild` CLI invocations (in scripts, hooks, CI) MUST NOT pass `-derivedDataPath` to redirect output. The exception is a transient, well-justified case (e.g. a sandbox test) where the script explicitly opts out and documents why — not a default.
- Xcode's **Preferences → Locations** must be set to **Default**, not **Custom** or **Workspace-relative**.
- Do not check any `build/`, `Build/`, `DerivedData/`, or per-target intermediate directories into the repo. `~/.gitignore_global` or a top-level `.gitignore` should already cover them.

## Carve-outs

- This project workflow does not use local Swift packages for project structure (see [xcode-projects](xcode-projects.md)), so `swift build` should not be invoked on authored code. External SPM dependencies consumed by an Xcode project build into DerivedData through the normal build plan — their in-package `.build/` dirs are not involved.
- Stale `.build/` directories left over from an SPM-era project layout should be deleted, not reused.

**Derived from cookbook:** [native-controls](../../../../agenticcookbook/principles/native-controls.md), [principle-of-least-astonishment](../../../../agenticcookbook/principles/principle-of-least-astonishment.md)
