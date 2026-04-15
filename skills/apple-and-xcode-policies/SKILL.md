---
name: apple-and-xcode-policies
description: Use when touching Swift code, Package.swift, project.yml, any .xcodeproj, an Xcode workspace, or code-signing entitlements. Enforces Swift 6.2.x, Xcode-projects-over-SPM, XcodeGen, /apple layout, and code-signing rules. macOS only.
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

## Xcode projects over Swift Packages — MANDATORY

**Always use Xcode projects, never Swift Package Manager as the primary project format.**

- Every project has `project.yml` (XcodeGen spec) at its project root: `/apple/MyProject/project.yml`.
- The generated `.xcodeproj` is **checked into the repo** alongside `project.yml`.
- Use `cc-xcgen` to regenerate after editing `project.yml`.

### Converting from Swift Package → Xcode project

1. Create `project.yml` with equivalent targets and settings.
2. **Include a test target** — migrate all existing tests into it.
3. Set the signing team to `mikefullerton` (Temporal Apple Developer account); preserve all entitlements.
4. **Always build and run tests after converting** — `cc-xcbuild <scheme> --test`. Migration isn't complete until tests pass.

## Xcode workspace

`/apple` must contain a single `.xcworkspace` that includes every Xcode project in the repo:

- Every `.xcodeproj` directly under `/apple/<ProjectName>/` → include.
- Submodules (their directories sit at the repo root): include their Xcode projects **one level deep only**. If a submodule itself contains nested submodules, do *not* include those nested projects.

## Code signing

- **Team:** `mikefullerton` (Temporal Apple Developer account).
- **Preserve all entitlements** when modifying project settings or converting projects.
- Provisioning profiles and certificates live on the local machine only — **never check them into the repo.** Prefer Xcode's automatic signing.

## Reference

Full rationale: `~/projects/active/cat-herding/docs/rules/development-policies.md` (section: "Apple [macOS only]").
