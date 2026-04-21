---
title: "Xcode Projects"
summary: "Reusable code goes in a Swift package (SPM); shipping products use an XcodeGen-managed Xcode project (project.yml + checked-in .xcodeproj). A single .xcworkspace in /apple aggregates both."
triggers: [creating-xcode-project, adding-xcode-target, xcodeworkspace-setup, creating-swift-package, adding-reusable-code]
tags: [xcode, xcodegen, apple, build, spm, swift-packages]
---

# Xcode Projects

Reusable code goes in a Swift package (SPM); shipping products use an XcodeGen-managed Xcode project (`project.yml` + checked-in `.xcodeproj`). A single `.xcworkspace` in `/apple` aggregates both.

## Project Structure

- Each Apple project — whether a Swift package or an Xcode project — MUST live in its own subdirectory under `/apple`:
  ```
  /apple/ProjectName1/
  /apple/ProjectName2/
  ```

## Project Type

Reusable code → **Swift package**. Shipping product → **Xcode project**.

### Swift packages (for reusable code)

- You MUST use a Swift package (SPM) for reusable code.
- If a Swift package is insufficient for a specific purpose — for example, the reusable code needs assets or other files the package format doesn't support — consult the user.
- For reusable code with multiple components, use a single package with multiple targets.

### Xcode projects (for shipping products)

- You MUST use an Xcode project for anything that ships as an app bundle, a plugin, or a macOS filesystem package (not a Swift package — to be clear).
- Xcode projects consume the reusable Swift packages.

## Xcode Project Files

- Every Xcode project MUST have a `project.yml` (XcodeGen spec) at the root of its project directory, e.g. `/apple/MyProject/project.yml`.
- The generated `.xcodeproj` MUST be checked into the repo alongside `project.yml`.

## Xcode Workspace

The `/apple` directory MUST contain a single `.xcworkspace` that aggregates every Apple project in the repo — both Xcode projects and Swift packages.

- Include every `.xcodeproj` directly under `/apple/<ProjectName>/`.
- Include every Swift package directly under `/apple/<ProjectName>/`.
- For submodules (their directories sit at the repo root): include their Apple projects **one level deep only**. If a submodule itself contains submodules, you MUST NOT include those nested projects.

**Derived from cookbook:** [native-controls](../../../../agenticcookbook/principles/native-controls.md), [explicit-over-implicit](../../../../agenticcookbook/principles/explicit-over-implicit.md)
