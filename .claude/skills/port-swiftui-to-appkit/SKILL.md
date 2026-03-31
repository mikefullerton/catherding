---
name: port-swiftui-to-appkit
version: "1.1.0"
description: "Analyze a macOS SwiftUI app and plan its conversion to native AppKit. Triggers on 'port to AppKit', 'convert SwiftUI to AppKit', 'remove SwiftUI', or /port-swiftui-to-appkit."
argument-hint: "[--version]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(xcodebuild *), Bash(git *), Bash(ls *), Bash(wc *), AskUserQuestion, Skill
---

# Port SwiftUI to AppKit v1.1.0

## Startup

**First action**: If `$ARGUMENTS` is `--version`, print `port-swiftui-to-appkit v1.1.0` and stop — do not run the skill.

Otherwise, print `port-swiftui-to-appkit v1.1.0` as the first line of output, then proceed.

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (1.1.0). If they differ, print:

> ⚠ This skill is running v1.1.0 but vA.B.C is installed. Restart the session to use the latest version.

Continue running — do not stop.

## Overview

Analyzes a macOS SwiftUI application and produces a comprehensive conversion report, then hands off to `/plan-roadmap` to create an implementation roadmap. The skill is read-only — it never modifies your code. The actual conversion happens later via `/implement-roadmap`.

## Usage

```
/port-swiftui-to-appkit
```

Run from the root of a macOS SwiftUI project.

## Prerequisites

Before doing anything else, verify all prerequisites. Stop immediately if any fails.

1. **macOS project.** Check for `.xcodeproj`, `Package.swift`, or `project.yml`. If none found, stop: "This does not appear to be an Xcode or Swift Package project."

2. **SwiftUI usage.** Grep for `import SwiftUI` across all `.swift` files. If zero results, stop: "No SwiftUI imports found — nothing to convert."

3. **macOS target.** Check for `import AppKit` or `NSApplication` or `macOS` in project configuration. If the project only imports UIKit or targets iOS/tvOS/watchOS, stop: "This skill only supports macOS apps. iOS/tvOS/watchOS conversions are not supported."

4. **Git clean.** Run `git status --porcelain`. If output is non-empty, stop: "Working tree has uncommitted changes. Commit or stash before running this skill."

5. **Load reference files.** Read all three:
   - `${CLAUDE_SKILL_DIR}/references/pattern-mappings.md`
   - `${CLAUDE_SKILL_DIR}/references/conversion-checklist.md`
   - `${CLAUDE_SKILL_DIR}/references/common-pitfalls.md`

   If any file is missing, stop and inform the user.

---

## Phase 1: Codebase Analysis

This phase is entirely read-only. No files are modified.

### Step 1.1: Inventory Swift Files

Glob for `**/*.swift` in the project source directories. For each file, check whether it contains `import SwiftUI`. Categorize every file into one of three buckets:

| Bucket | Criteria |
|--------|----------|
| **SwiftUI-dependent** | Contains `import SwiftUI` and is primarily a view (`some View`, `some Scene`, `NSViewRepresentable`) |
| **Hybrid** | Contains `import SwiftUI` but primarily model/logic code (only uses SwiftUI for `Color`, `@AppStorage`, etc.) |
| **Pure logic** | No `import SwiftUI` — unchanged by conversion |

Count files in each bucket.

### Step 1.2: Detect Architecture Patterns

Scan the codebase for each pattern. Record whether it exists and which file(s) contain it:

| Pattern | Search For | Conversion Impact |
|---------|-----------|-------------------|
| SwiftUI App lifecycle | `@main struct` with `: App` | Required — Phase 2 |
| Existing AppDelegate | `@NSApplicationDelegateAdaptor` or `NSApplicationDelegate` | Expand existing vs create new |
| Window groups | `WindowGroup` | One `NSWindowController` per group |
| Settings scene | `Settings {` or `Settings(` as a scene | Phase 4 |
| Split views | `HSplitView`, `NavigationSplitView` | `NSSplitViewController` in Phase 2 |
| List views | `List(` with model binding | `NSTableView` in Phase 3 |
| Sidebar style | `.listStyle(.sidebar)` | Source list style |
| NSViewRepresentable | `NSViewRepresentable` | Delete — direct NSView management |
| Window accessor hacks | `WindowAccessor`, `NSViewRepresentable` used for window config | Delete entirely |
| Toolbar items | `.toolbar {` | `NSToolbar` in Phase 2 |
| Multiple window types | Multiple `WindowGroup(id:` | One controller per type |
| Focused values | `@FocusedObject`, `@FocusedValue` | Route through `NSApp.mainWindow` |
| Environment objects | `@EnvironmentObject`, `@Environment(` | Direct property injection |
| Geometry readers | `GeometryReader` | Manual frame calculation |
| Task modifier | `.task {` | `Task {}` in `viewDidLoad()` |
| Custom layouts | `Layout` protocol conformance | Manual `NSView` layout |

### Step 1.3: Map @AppStorage Keys

Find every `@AppStorage("key")` usage. For each, record:
- The key string
- The default value
- The Swift type
- Which file(s) use it

These become direct `UserDefaults.standard` reads/writes in the converted code.

### Step 1.4: Document Keyboard Shortcuts

Find every `.keyboardShortcut(` usage. For each, record:
- The key character
- The modifier mask
- The associated action/label
- Which file contains it

These must all appear in the AppKit `NSMenu` built in `applicationWillFinishLaunching`.

### Step 1.5: Detect Third-Party SwiftUI Dependencies

Check `Package.swift`, `Package.resolved`, or `project.yml` for package dependencies. For each dependency, check whether it is likely SwiftUI-based by examining the package name and its product names in the manifest. Do NOT grep through downloaded package sources (`.build/`, SPM cache) — this is unbounded. Instead, flag any dependency whose name or description suggests SwiftUI views (e.g., contains "SwiftUI", "View", "UI") for manual review by the user.

### Step 1.6: Flag Advanced Patterns

Check for patterns that need case-by-case discussion:
- `@Environment(\.` — custom environment values need manual threading
- `GeometryReader` — needs manual frame calculation
- Custom `Layout` conformances — needs manual `NSView` layout
- `@AppStorage` with non-standard types — may need custom `UserDefaults` encoding
- `PreferenceKey` — needs a different communication pattern
- `@FetchRequest` — needs manual Core Data fetch in view controller

For each one found, note the file and line for discussion with the user.

---

## Phase 2: Conversion Plan Generation

Using the analysis from Phase 1 and the pattern mappings reference, generate the conversion plan.

### Step 2.1: Determine Applicable Phases

| Phase | Required When |
|-------|--------------|
| Phase 1: Model Layer Cleanup | Always (any hybrid files exist) |
| Phase 2: App Lifecycle & Windows | Always (SwiftUI App struct exists) |
| Phase 3: Sidebar / List Views | `List` views detected |
| Phase 4: Settings Window | `Settings` scene detected |
| Phase 5: Final Cleanup | Always |

Mark each phase as applicable or skipped.

### Step 2.2: File-Level Plan

For every Swift file in the project, determine its fate:

| Action | Criteria |
|--------|----------|
| **DELETE** | Pure SwiftUI view with no reusable logic |
| **CREATE** | New AppKit controller replacing a deleted view |
| **MODIFY** | Hybrid file needing `import SwiftUI` removal and type changes |
| **UNCHANGED** | Pure logic file with no SwiftUI dependency |

For each DELETE, identify what CREATE replaces it. Use the file mapping patterns from `references/pattern-mappings.md`:
- App struct → absorbed into AppDelegate
- ContentView → SplitViewController or root ViewController
- List views → ListViewController + CellView
- Settings views → SettingsWindowController + per-tab VCs
- NSViewRepresentable wrappers → ContentViewController with direct NSView management
- WindowAccessor → absorbed into WindowController

### Step 2.3: Estimate Complexity

For each applicable phase, estimate complexity as S/M/L:
- **S**: Straightforward pattern replacement, no ambiguity
- **M**: Some case-by-case decisions needed
- **L**: Complex patterns, third-party dependencies, or extensive UI

---

## Phase 3: Present Analysis

Display the full analysis in a structured format:

```
=== SWIFTUI → APPKIT CONVERSION ANALYSIS ===

Project: <name>
Swift files: <n> total
  SwiftUI-dependent: <n> (to delete/replace)
  Hybrid: <n> (to modify)
  Pure logic: <n> (unchanged)

Architecture Detected:
  [x/] SwiftUI App lifecycle
  [x/] Existing AppDelegate
  [x/] Split views
  [x/] List views (<n> files)
  [x/] Settings scene
  [x/] NSViewRepresentable wrappers (<n>)
  [x/] Window accessor hacks
  [x/] Toolbar items
  [x/] Multiple window types
  [x/] Focused values
  ...

@AppStorage keys: <n>
Keyboard shortcuts: <n>
Third-party SwiftUI deps: <list or "none">

Advanced patterns needing discussion:
  <list or "none">

Applicable phases: <list>
Skipped phases: <list with reasons>

FILE PLAN:
  DELETE (<n> files):
    - <file> → replaced by <new file>
    ...
  CREATE (<n> files):
    - <file> (replaces <old file>)
    ...
  MODIFY (<n> files):
    - <file> (remove import SwiftUI, Color → NSColor)
    ...
  UNCHANGED (<n> files):
    - <file>
    ...

COMMON PITFALLS TO WATCH:
  <list applicable pitfalls from references/common-pitfalls.md>
```

Then ask: **"Does this analysis look correct? Any files miscategorized or patterns I missed?"**

If the user identifies corrections, update the analysis and re-present.

If advanced patterns were flagged in Step 1.6, discuss each one with the user now to determine the conversion approach before proceeding.

---

## Phase 4: Hand Off to /plan-roadmap

Once the user confirms the analysis, invoke `/plan-roadmap` using the Skill tool.

Before invoking, print:

```
Analysis confirmed. Handing off to /plan-roadmap to create the implementation roadmap.

The roadmap will break this conversion into implementation steps following
the 5-phase process. Each step will map to a single PR with build verification.
```

When `/plan-roadmap` asks "What feature would you like to plan?", provide all of the following context from your analysis:

1. **Feature name**: "SwiftUI to AppKit Conversion"
2. **Problem description**: The full analysis summary from Phase 3
3. **The 5-phase conversion process**: model cleanup → app lifecycle → lists → settings → final cleanup
4. **File-level plan**: which files to delete, create, modify
5. **Pattern mappings**: reference the specific AppKit replacements for each SwiftUI construct found
6. **@AppStorage keys and keyboard shortcuts**: the complete inventories
7. **Applicable pitfalls**: from `references/common-pitfalls.md`
8. **Verification strategy**: build after each phase, `grep -r "import SwiftUI"` returns zero at the end

Each roadmap step should correspond to a logical unit within a phase:
- Phase 1 may be a single step (model cleanup)
- Phase 2 typically needs 2-3 steps (AppDelegate + menus, window controller, split/content VCs)
- Phase 3 needs 1-2 steps per list view (controller + cell view)
- Phase 4 needs 1 step per settings tab + 1 for the window controller
- Phase 5 is a single verification step

Every step must include:
- Build verification as acceptance criteria
- The specific patterns from `references/pattern-mappings.md` that apply
- Relevant pitfalls from `references/common-pitfalls.md`

---

## Guards

- **Read-only.** This skill MUST NOT modify any source files. It only reads, analyzes, and reports.
- **macOS only.** Do not attempt to analyze iOS, tvOS, watchOS, or visionOS apps.
- **Git must be clean.** Do not run on a dirty working tree.
- **User approval required.** Do not hand off to `/plan-roadmap` until the user confirms the analysis.
- **No assumptions about build system.** Detect whether the project uses `.xcodeproj`, XcodeGen, or SPM and report it. Do not assume.
- **Flag what you cannot handle.** If you encounter a SwiftUI pattern not covered by `references/pattern-mappings.md`, tell the user explicitly rather than guessing.
- **Preserve all keyboard shortcuts.** Every shortcut found in Step 1.4 must appear in the roadmap's Phase 2 acceptance criteria.

## Verification

The skill completed successfully when all of these are true:

1. The structured analysis report (Phase 3) was presented to the user
2. The user confirmed the analysis is correct (or corrections were applied and re-confirmed)
3. `/plan-roadmap` was invoked with the full analysis context
4. `/plan-roadmap` produced a roadmap with build verification in every step
