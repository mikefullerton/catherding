---
title: "Xcode Projects"
summary: "All Apple code lives in hand-edited Xcode projects (.xcodeproj). No SPM, no XcodeGen. A single .xcworkspace in /apple aggregates every project."
triggers: [creating-xcode-project, adding-xcode-target, xcodeworkspace-setup, adding-reusable-code]
tags: [xcode, apple, build]
---

# Xcode Projects

All Apple code lives in hand-edited Xcode projects (`.xcodeproj`). The `.xcodeproj` is the source of truth and is checked into the repo. A single `.xcworkspace` in `/apple` aggregates every project.

This author's repos do **not** use Swift packages for project structure and do **not** use XcodeGen.

## Project Structure

- Each Apple project MUST live in its own subdirectory under `/apple`:
  ```
  /apple/ProjectName1/
  /apple/ProjectName2/
  ```
- Both reusable code and shipping products use Xcode projects. Consuming projects reference reusable projects as Xcode project references within the same workspace.
- You MUST NOT author local code as a Swift package (no `Package.swift` files for project structure). External SPM dependencies (libraries consumed from GitHub, etc.) are still fine — they are referenced from the Xcode project as package dependencies.
- You MUST NOT introduce XcodeGen (`project.yml`). The `.xcodeproj` is edited directly — in Xcode, or via deliberate `pbxproj` edits.

## Xcode Workspace

The `/apple` directory MUST contain a single `.xcworkspace` that aggregates every Xcode project in the repo.

- Include every `.xcodeproj` directly under `/apple/<ProjectName>/`.
- For submodules (their directories sit at the repo root): include their Apple projects **one level deep only**. If a submodule itself contains submodules, you MUST NOT include those nested projects.

**Derived from cookbook:** [native-controls](../../../../agenticcookbook/principles/native-controls.md), [explicit-over-implicit](../../../../agenticcookbook/principles/explicit-over-implicit.md)
