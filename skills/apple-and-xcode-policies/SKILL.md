---
name: apple-and-xcode-policies
description: Use when touching Swift code, any .xcodeproj, an Xcode workspace, code-signing entitlements, or working in an Apple project that uses AgenticToolkit. Enforces Swift 6.2.x, Xcode-projects-only (no SPM, no XcodeGen), /apple layout, code-signing rules, Swift file organization, and AgenticToolkit Loggable requirement. macOS only.
---

# Apple & Xcode — MANDATORY (macOS)

## Swift version

**All Swift code targets the latest patch release of Swift 6.2** (i.e. `6.2.x`).

- Write code that compiles cleanly under Swift 6 concurrency rules: `@Sendable`, `@MainActor`, strict data-race safety.
- **Do not downgrade** to Swift 5 language mode.
- **Do not upgrade** to Swift 6.3 or later without an explicit decision.

## File organization

Three rules for Swift source files:

- **One entity per file.** One `struct`, `class`, `enum`, `actor`, or `protocol` per file. Child entities of that top-level entity are the only exception.
- **Nested entities in an extension, same file.** Declare nested types via `extension Outer { ... }`, not inside the outer entity's body.
- **Protocol conformance in an extension when possible.** Use `extension Foo: MyProtocol { }`. Fall back to declaring the conformance on the primary type only when the compiler forbids extension-based conformance.

## AgenticToolkit logging

For Apple projects that depend on **AgenticToolkit**, logging MUST go through the `Loggable` protocol:

- Any type that emits log output MUST conform to `Loggable`.
- Do not call `os.Logger` / `print` / `NSLog` directly from types that should be observable — conform to `Loggable`, which gives each subsystem a unique log category.

## Project layout

Multi-platform repos use top-level platform directories. Create only the ones the repo needs:

```
/apple
/windows
/android
```

Each Apple project lives in its own subdirectory under `/apple`:

```
/apple/ProjectName1/
/apple/ProjectName2/
```

Platform-specific code, projects, and tooling live *exclusively* under their platform directory.

## Project type — MANDATORY

**Xcode projects only.** All Apple code — reusable libraries and shipping products alike — lives in a hand-edited `.xcodeproj`.

- **No Swift packages for project structure.** Do not author local code as a Swift package; no `Package.swift` files. External SPM dependencies consumed from GitHub are still fine — they are referenced from the Xcode project as package dependencies.
- **No XcodeGen.** No `project.yml` files. The `.xcodeproj` is the source of truth and is edited directly (in Xcode or by careful `pbxproj` edits).
- Reusable code is consumed by other projects as an **Xcode project reference** in the same workspace.

## Xcode workspace

`/apple` must contain a single `.xcworkspace` that aggregates every Xcode project in the repo:

- Every `.xcodeproj` directly under `/apple/<ProjectName>/` → include.
- Submodules (their directories sit at the repo root): include their Apple projects **one level deep only**. If a submodule itself contains nested submodules, do *not* include those nested projects.

## Code signing

- **Team:** `mikefullerton` (Temporal Apple Developer account).
- **Preserve all entitlements** when modifying project settings or converting projects.
- Provisioning profiles and certificates live on the local machine only — **never check them into the repo.** Prefer Xcode's automatic signing.

## Reference

Full rationale across these policy files in `~/projects/active/catherding/policies/workflow/apple-platform-development/`:

- [swift-version.md](../../policies/workflow/apple-platform-development/swift-version.md) — Swift 6.2.x and strict concurrency
- [swift-file-organization.md](../../policies/workflow/apple-platform-development/swift-file-organization.md) — one entity per file; nested types and protocol conformance in extensions
- [xcode-projects.md](../../policies/workflow/apple-platform-development/xcode-projects.md) — Xcode projects only (no SPM, no XcodeGen) + single `.xcworkspace`
- [code-signing.md](../../policies/workflow/apple-platform-development/code-signing.md) — signing team + entitlements
- [agentictoolkit-logging.md](../../policies/workflow/apple-platform-development/agentictoolkit-logging.md) — Loggable protocol required in projects using AgenticToolkit

Start at [INDEX.md](../../policies/INDEX.md) to navigate.
