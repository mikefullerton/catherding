---
name: apple-and-xcode-policies
description: Use when touching Swift code, Package.swift, project.yml, any .xcodeproj, an Xcode workspace, or code-signing entitlements. Enforces Swift 6.2.x, SPM for reusable code + Xcode projects for shipping products, XcodeGen, /apple layout, and code-signing rules. macOS only.
---

# Apple & Xcode — MANDATORY (macOS)

## Swift version

**All Swift code targets the latest patch release of Swift 6.2** (i.e. `6.2.x`).

- Use `// swift-tools-version: 6.2` in `Package.swift` files.
- Write code that compiles cleanly under Swift 6 concurrency rules: `@Sendable`, `@MainActor`, strict data-race safety.
- **Do not downgrade** to Swift 5 language mode.
- **Do not upgrade** to Swift 6.3 or later without an explicit decision.

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

## Project type: SPM vs Xcode — MANDATORY

Pick by what the code *is*, not by preference:

- **Reusable code → Swift package (SPM).** For multi-component reusable code, use a single package with multiple targets. If SPM is insufficient for a specific purpose (e.g. the reusable code needs assets or other files SPM doesn't support), **consult the user** before reaching for an Xcode project.
- **Shipping product → Xcode project.** Anything that ships as an app bundle, a plugin, or a macOS filesystem package uses an Xcode project — not an SPM package. Xcode projects consume the reusable Swift packages.

### Xcode project files

- Every Xcode project has a `project.yml` (XcodeGen spec) at its project root: `/apple/MyProject/project.yml`.
- The generated `.xcodeproj` is **checked into the repo** alongside `project.yml`.
- Use `cc-xcgen` to regenerate after editing `project.yml`.

## Xcode workspace

`/apple` must contain a single `.xcworkspace` that aggregates every Apple project in the repo — both Xcode projects and Swift packages:

- Every `.xcodeproj` directly under `/apple/<ProjectName>/` → include.
- Every Swift package directly under `/apple/<ProjectName>/` → include.
- Submodules (their directories sit at the repo root): include their Apple projects **one level deep only**. If a submodule itself contains nested submodules, do *not* include those nested projects.

## Code signing

- **Team:** `mikefullerton` (Temporal Apple Developer account).
- **Preserve all entitlements** when modifying project settings or converting projects.
- Provisioning profiles and certificates live on the local machine only — **never check them into the repo.** Prefer Xcode's automatic signing.

## Reference

Full rationale across these policy files in `~/projects/active/catherding/policies/workflow/apple-platform-development/`:

- [swift-version.md](../../policies/workflow/apple-platform-development/swift-version.md) — Swift 6.2.x and strict concurrency
- [xcode-projects.md](../../policies/workflow/apple-platform-development/xcode-projects.md) — XcodeGen + project.yml + .xcworkspace
- [code-signing.md](../../policies/workflow/apple-platform-development/code-signing.md) — signing team + entitlements

Start at [INDEX.md](../../policies/INDEX.md) to navigate.
