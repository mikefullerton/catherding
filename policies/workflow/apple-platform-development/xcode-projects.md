---
title: "Xcode Projects"
summary: "All Apple code lives in XcodeGen-managed Xcode projects (project.yml + checked-in .xcodeproj). A single .xcworkspace in /apple aggregates every project."
triggers: [creating-xcode-project, adding-xcode-target, xcodeworkspace-setup, adding-reusable-code]
tags: [xcode, xcodegen, apple, build]
---

# Xcode Projects

All Apple code lives in XcodeGen-managed Xcode projects (`project.yml` + checked-in `.xcodeproj`). A single `.xcworkspace` in `/apple` aggregates every project. Swift packages (SPM) are not used as a project structure in this author's repos.

## Project Structure

- Each Apple project MUST live in its own subdirectory under `/apple`:
  ```
  /apple/ProjectName1/
  /apple/ProjectName2/
  ```
- Both reusable code and shipping products use Xcode projects. Consuming projects reference reusable projects as Xcode project dependencies within the same workspace.
- You MUST NOT author local code as a Swift package (no `Package.swift` files for project structure). External SPM dependencies (libraries consumed from GitHub, etc.) are still referenced through an Xcode project's `project.yml` `packages:` section — that is fine; the prohibition is on authoring your own local code as a Swift package.

## Xcode Project Files

- Every Xcode project MUST have a `project.yml` (XcodeGen spec) at the root of its project directory, e.g. `/apple/MyProject/project.yml`.
- The generated `.xcodeproj` MUST be checked into the repo alongside `project.yml`.

## Xcode Workspace

The `/apple` directory MUST contain a single `.xcworkspace` that aggregates every Xcode project in the repo.

- Include every `.xcodeproj` directly under `/apple/<ProjectName>/`.
- For submodules (their directories sit at the repo root): include their Apple projects **one level deep only**. If a submodule itself contains submodules, you MUST NOT include those nested projects.

**Derived from cookbook:** [native-controls](../../../../agenticcookbook/principles/native-controls.md), [explicit-over-implicit](../../../../agenticcookbook/principles/explicit-over-implicit.md)
