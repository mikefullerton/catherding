# Conversion Checklist

Phase-by-phase verification checklist for SwiftUI → AppKit conversion. Every item must pass before proceeding to the next phase.

---

## Pre-Conversion

- [ ] Git working tree is clean (`git status --porcelain` returns empty)
- [ ] All Swift files inventoried and categorized (SwiftUI-dependent / hybrid / pure logic)
- [ ] All `@AppStorage` keys documented (key, default, type, files)
- [ ] All `.keyboardShortcut()` usages documented (key, modifiers, action, file)
- [ ] Architecture patterns identified (split views, lists, settings, etc.)
- [ ] Third-party SwiftUI dependencies evaluated
- [ ] Advanced patterns flagged and discussed with user
- [ ] Applicable phases determined (which to run, which to skip)
- [ ] File-level plan created (delete / create / modify / unchanged)
- [ ] User approved the analysis

---

## Phase 1: Model Layer Cleanup

**Goal:** Remove `import SwiftUI` from all non-view files.

- [ ] Every hybrid file: `import SwiftUI` removed or replaced with `import AppKit`
- [ ] `SwiftUI.Color` → `NSColor` in all model/logic files
- [ ] `Color(hex:)` extensions ported to `NSColor(hex:)` if needed
- [ ] No `import SwiftUI` in any pure-logic or hybrid file
- [ ] `import SwiftUI` exists ONLY in files scheduled for deletion/replacement in later phases
- [ ] `@Published` properties unchanged (Combine stays)
- [ ] `ObservableObject` conformances unchanged
- [ ] **Build succeeds** (`xcodebuild build`)

---

## Phase 2: App Lifecycle & Window Infrastructure

**Goal:** Replace SwiftUI App entry point with AppKit AppDelegate.

### AppDelegate
- [ ] `@main` on AppDelegate class
- [ ] `static func main()` implemented
- [ ] `applicationWillFinishLaunching` builds main menu
- [ ] `applicationDidFinishLaunching` creates and shows first window
- [ ] `applicationShouldHandleReopen` handles dock click with no windows
- [ ] `applicationWillTerminate` cleans up resources

### Menu Bar
- [ ] App menu: About, Settings (Cmd+,), Services, Hide, Hide Others, Show All, Quit
- [ ] File menu with all original file operations
- [ ] Edit menu with standard selectors (cut/copy/paste/selectAll/undo/redo)
- [ ] View menu (if applicable — sidebar toggle, etc.)
- [ ] Window menu: Minimize, Zoom, Bring All to Front
- [ ] `NSApp.servicesMenu` assigned
- [ ] `NSApp.windowsMenu` assigned
- [ ] Every keyboard shortcut from pre-conversion inventory is present
- [ ] Shortcut key equivalents and modifier masks match originals

### Window Controller
- [ ] `NSWindowController` subclass created for each window type
- [ ] `isReleasedWhenClosed = false` set on all windows
- [ ] `setFrameAutosaveName` configured
- [ ] Window min size set
- [ ] `windowWillClose` cleanup implemented
- [ ] AppDelegate tracks window controllers in array

### Split View (if applicable)
- [ ] `NSSplitViewController` with sidebar + content items
- [ ] Sidebar `minimumThickness` and `maximumThickness` set
- [ ] `splitView.autosaveName` configured
- [ ] Sidebar toggle works

### Content View Controller
- [ ] NSView management replaces NSViewRepresentable
- [ ] View reparenting preserves child state
- [ ] `autoresizingMask = [.width, .height]` for layout
- [ ] First responder set async after view added

### Deleted Files
- [ ] App struct file deleted
- [ ] ContentView deleted
- [ ] WindowAccessor deleted (if existed)
- [ ] NSViewRepresentable wrappers deleted
- [ ] No dangling references to deleted files

### Verification
- [ ] **Build succeeds**
- [ ] App launches and shows a window
- [ ] Menu bar is complete with all items
- [ ] Cmd+T (or equivalent) creates new window
- [ ] Window frame persists across restarts
- [ ] Window close cleans up properly

---

## Phase 3: Sidebar / List Views (if applicable)

**Goal:** Replace SwiftUI List with NSTableView.

### NSTableView
- [ ] `tableView.style = .sourceList` (for sidebar lists)
- [ ] `headerView = nil`
- [ ] Single column with `.autoresizingMask`
- [ ] `NSTableViewDataSource` implemented (`numberOfRows`)
- [ ] `NSTableViewDelegate` implemented (`viewFor`, `selectionDidChange`)

### Cell View
- [ ] `NSTableCellView` subclass with programmatic layout
- [ ] Combine subscriptions in `configure(with:)` method
- [ ] `cancellables.removeAll()` at start of `configure()` AND in `prepareForReuse()`
- [ ] SF Symbols use `NSImage(systemSymbolName:accessibilityDescription:)`
- [ ] Colors use `NSColor` not `SwiftUI.Color`

### Selection
- [ ] Bidirectional selection sync implemented
- [ ] `isUpdatingSelection` guard prevents infinite loops
- [ ] Model → table: Combine subscription with guard check
- [ ] Table → model: `tableViewSelectionDidChange` sets guard

### Context Menus (if applicable)
- [ ] `tableView.menu` assigned
- [ ] Actions use `tableView.clickedRow` not `selectedRow`
- [ ] Menu labels match original exactly

### Deleted Files
- [ ] SwiftUI list view files deleted
- [ ] No dangling references

### Verification
- [ ] **Build succeeds**
- [ ] List displays all items
- [ ] Selection syncs: click item → model updates → content updates
- [ ] Model change → table selection follows
- [ ] Context menus work on correct item
- [ ] Add/remove items updates list correctly
- [ ] Dynamic row heights display correctly (if applicable)

---

## Phase 4: Settings Window (if applicable)

**Goal:** Replace SwiftUI Settings scene with AppKit.

### Window Controller
- [ ] `SettingsWindowController` is a singleton
- [ ] `isReleasedWhenClosed = false`
- [ ] Layout matches original: sidebar style → `NSSplitViewController`, tab style → `NSTabViewController`
- [ ] Cmd+, menu item opens settings
- [ ] `showWindow(nil)` + `makeKeyAndOrderFront(nil)` both called

### Per-Tab View Controllers
- [ ] One `NSViewController` per settings area
- [ ] All `@AppStorage` replaced with `UserDefaults.standard` read/write
- [ ] Values loaded in `viewDidLoad()`
- [ ] Changes written in `@objc` action handlers

### Control Mappings
- [ ] Picker → `NSPopUpButton` with `representedObject`
- [ ] Saved value correctly selected on load (iterate `itemArray`)
- [ ] Toggle → `NSButton(checkboxWithTitle:)` with correct initial state
- [ ] TextField → `NSTextField` with `controlTextDidChange` for live saving
- [ ] SecureField → `NSSecureTextField` with `controlTextDidChange`
- [ ] Slider → `NSSlider` with target/action
- [ ] Section → `NSStackView` with header label

### Deleted Files
- [ ] SwiftUI settings view files deleted
- [ ] No dangling references

### Verification
- [ ] **Build succeeds**
- [ ] Cmd+, opens settings window
- [ ] Settings window comes to front (not behind main window)
- [ ] All controls load saved values correctly
- [ ] Changes persist to UserDefaults
- [ ] Values survive app restart
- [ ] Closing and reopening settings preserves values

---

## Phase 5: Final Cleanup

**Goal:** Zero SwiftUI remaining, everything works.

### Zero SwiftUI
- [ ] `grep -r "import SwiftUI"` returns **zero** results across entire project
- [ ] No stale SwiftUI types: `@AppStorage`, `@StateObject`, `@ObservedObject` (in view files), `@EnvironmentObject`, `@FocusedObject`, `@FocusedValue`
- [ ] No `some View` or `some Scene` return types
- [ ] No `NSViewRepresentable` or `NSViewControllerRepresentable`
- [ ] No `WindowGroup`, `Settings`, `Commands`, `CommandGroup`

### Keyboard Shortcuts
- [ ] Every shortcut from pre-conversion inventory verified in `buildMainMenu()`
- [ ] Key equivalents match exactly
- [ ] Modifier masks match exactly

### Build
- [ ] `xcodebuild build` succeeds with **zero errors**
- [ ] Warning count documented (some new warnings may be acceptable)

### Functional Verification
- [ ] App launches correctly
- [ ] All windows display and function
- [ ] All menus work with correct shortcuts
- [ ] All list/sidebar interactions work
- [ ] All settings persist
- [ ] Multi-window works (if applicable)
- [ ] Window close cleanup works
- [ ] Dock click with no windows reopens a window

### Project Regeneration (if applicable)
- [ ] XcodeGen: `xcodegen generate` succeeds
- [ ] All new files included in build
- [ ] All deleted files removed from build
