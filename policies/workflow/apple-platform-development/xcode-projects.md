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

## Swift Packages for reusable code

- You MUST use Swift packages SPM for reusable code. If a Swift.package is insuffient for a specific purpose, like the reusable code needs assets or other files, consult the user
- For resuable code with multiple components, use a single package with multiple targets

## Xcode Projects for bundled products

- You MUST used xcode projects for apps, plugins, or anything else that ships as bundles or or file mananager packages (not Swift packages here to be clear) 
- these will consume the reusable Swift packages
- Every project MUST have a `project.yml` (XcodeGen spec) at the root of its project directory, e.g. `/apple/MyProject/project.yml`.
- The generated `.xcodeproj` MUST be checked into the repo alongside `project.yml`.

## Xcode Workspace

The `/apple` directory MUST contain a single `.xcworkspace` that includes all Xcode projects in the repo.

- Include every `.xcodeproj` directly under `/apple/<ProjectName>/`.
- For submodules (their directories sit at the repo root): include their Xcode projects **one level deep only**. If a submodule itself contains submodules, you MUST NOT include those nested projects.

**Derived from cookbook:** [native-controls](../../../../agenticcookbook/principles/native-controls.md), [explicit-over-implicit](../../../../agenticcookbook/principles/explicit-over-implicit.md)
