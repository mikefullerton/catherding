---
title: "Xcode Projects"
summary: "Apple projects use XcodeGen with project.yml + checked-in .xcodeproj; a single .xcworkspace in /apple aggregates them."
triggers: [creating-xcode-project, xcode-project-conversion, adding-xcode-target, xcodeworkspace-setup, converting-swift-package]
tags: [xcode, xcodegen, apple, build]
---

# Xcode Projects

Apple projects use XcodeGen with `project.yml` + checked-in `.xcodeproj`; a single `.xcworkspace` in `/apple` aggregates them.

## Project Structure

- Each Apple project MUST live in its own subdirectory under `/apple`:
  ```
  /apple/ProjectName1/
  /apple/ProjectName2/
  ```

## Xcode Projects over Swift Packages

- You MUST use Xcode projects, NOT Swift Package Manager, as the primary project format.
- Every project MUST have a `project.yml` (XcodeGen spec) at the root of its project directory, e.g. `/apple/MyProject/project.yml`.
- The generated `.xcodeproj` MUST be checked into the repo alongside `project.yml`.

### Converting from a Swift Package

When converting a `Package.swift`-based project to an Xcode project:

1. You MUST create `project.yml` with equivalent targets and settings.
2. You MUST include a test target — migrate all existing tests into it.
3. You MUST set the signing team to `mikefullerton` (Temporal Apple Developer account) and preserve all entitlements. See [code-signing](code-signing.md).
4. You MUST build and run tests after converting before considering the migration complete.

## Xcode Workspace

The `/apple` directory MUST contain a single `.xcworkspace` that includes all Xcode projects in the repo.

- Include every `.xcodeproj` directly under `/apple/<ProjectName>/`.
- For submodules (their directories sit at the repo root): include their Xcode projects **one level deep only**. If a submodule itself contains submodules, you MUST NOT include those nested projects.

**Derived from cookbook:** [native-controls](../../../agenticcookbook/principles/native-controls.md), [explicit-over-implicit](../../../agenticcookbook/principles/explicit-over-implicit.md)
