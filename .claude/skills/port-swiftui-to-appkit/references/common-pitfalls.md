# Common Pitfalls

10 documented pitfalls from real SwiftUI → AppKit conversions. Each includes the symptom, root cause, and fix.

---

## 1. Bidirectional Selection Feedback Loop

**Symptom:** Changing selection in the table causes infinite recursion, stack overflow, or flickering between two rows.

**Cause:** The table selection delegate updates the model, which triggers a Combine subscription that updates the table selection, which fires the delegate again...

**Fix:** Use an `isUpdatingSelection` boolean guard:

```swift
private var isUpdatingSelection = false

// Model → Table
manager.$selectedID.sink { [weak self] id in
    guard let self, !self.isUpdatingSelection else { return }
    // update table selection
}

// Table → Model
func tableViewSelectionDidChange(_ notification: Notification) {
    isUpdatingSelection = true
    manager.select(id: items[tableView.selectedRow].id)
    isUpdatingSelection = false
}
```

---

## 2. Combine Subscriptions Not Cancelled on Cell Reuse

**Symptom:** After scrolling, cells show wrong data, update with stale values, or crash on access to deallocated objects.

**Cause:** `NSTableView` reuses cell views via `makeView(withIdentifier:)`. If the old Combine subscriptions are not cancelled, the cell receives updates from the previous model object AND the new one.

**Fix:** Cancel subscriptions in both places:

```swift
func configure(with item: ItemModel) {
    cancellables.removeAll()  // Cancel BEFORE subscribing
    item.$title.sink { [weak self] in ... }.store(in: &cancellables)
}

override func prepareForReuse() {
    super.prepareForReuse()
    cancellables.removeAll()  // Cancel on reuse too
}
```

---

## 3. Missing `isReleasedWhenClosed = false`

**Symptom:** Crash (EXC_BAD_ACCESS) when trying to access the window or window controller after the user closes the window. Or singleton settings window disappears permanently after closing.

**Cause:** By default, `NSWindow.isReleasedWhenClosed` is `true`. When the window closes, it is deallocated. Any stored reference becomes a dangling pointer.

**Fix:** Set `isReleasedWhenClosed = false` on every programmatically created window:

```swift
window.isReleasedWhenClosed = false
```

This is especially critical for:
- Singleton windows (settings)
- Windows managed by controller arrays
- Any window you want to reshow after closing

---

## 4. Missing `init?(coder:)` Unavailability

**Symptom:** Compiler error: "'required' initializer 'init(coder:)' must be provided by subclass."

**Cause:** NSView, NSViewController, NSWindowController, and NSTableCellView all require `init?(coder:)` for Interface Builder support. If you only use programmatic init, you still need to satisfy the requirement.

**Fix:** Add to every subclass:

```swift
@available(*, unavailable)
required init?(coder: NSCoder) {
    fatalError("init(coder:) is not supported")
}
```

Using `@available(*, unavailable)` is better than a plain `fatalError` because it gives a compile-time error if anyone tries to use it.

---

## 5. Stale `import SwiftUI` in Model Files

**Symptom:** App compiles and works but still links the SwiftUI framework at runtime. Binary size is larger than expected. May cause issues in contexts where SwiftUI is unavailable.

**Cause:** Phase 1 model cleanup missed some files. Common culprits:
- Files that use `SwiftUI.Color` for a single property
- Files that imported SwiftUI for `@AppStorage` only
- Extension files that add SwiftUI conformances

**Fix:** Phase 5 verification must grep exhaustively:

```bash
grep -r "import SwiftUI" Sources/
```

Must return zero results. Check every match, not just the count.

---

## 6. Menu Keyboard Shortcuts Not Matching Originals

**Symptom:** Users report missing or changed keyboard shortcuts after conversion. Cmd+Shift+N no longer creates a new session. Cmd+, doesn't open settings.

**Cause:** SwiftUI `.keyboardShortcut` mapping to `keyEquivalent` + `keyEquivalentModifierMask` was done incorrectly or incompletely.

**Fix:** Create a complete inventory during pre-conversion analysis. Verify every shortcut in Phase 5:

| SwiftUI | AppKit keyEquivalent | AppKit modifierMask |
|---------|---------------------|---------------------|
| `.keyboardShortcut("n", modifiers: [.command, .shift])` | `"n"` | `[.command, .shift]` |
| `.keyboardShortcut(",", modifiers: .command)` | `","` | `.command` |
| `.keyboardShortcut(.delete)` | `String(Character(UnicodeScalar(NSBackspaceCharacter)!))` | `.command` |

Watch for special keys (delete, return, escape, arrow keys) — they use `NSEvent` key constants, not string characters.

---

## 7. NSPopUpButton Not Selecting Saved Value on Load

**Symptom:** Dropdown always shows the first item when the settings window opens, even though a different value is saved in UserDefaults.

**Cause:** After adding items to `NSPopUpButton`, no code selects the item matching the stored value. Or the code tries to match by title instead of `representedObject`.

**Fix:** After populating the popup, iterate items and match by `representedObject`:

```swift
let saved = UserDefaults.standard.string(forKey: key) ?? defaultValue
for item in popUp.itemArray {
    if item.representedObject as? String == saved {
        popUp.select(item)
        break
    }
}
```

Do NOT use `selectItem(withTitle:)` — titles may change or be localized.

---

## 8. Settings Window Appearing Behind Main Window

**Symptom:** Pressing Cmd+, appears to do nothing. The settings window is actually created but hidden behind the main window.

**Cause:** `showWindow(nil)` alone may not bring the window to the front if another window is key.

**Fix:** Call both methods:

```swift
func showSettings() {
    SettingsWindowController.shared.showWindow(nil)
    SettingsWindowController.shared.window?.makeKeyAndOrderFront(nil)
}
```

---

## 9. Lost First Responder After View Switching

**Symptom:** After switching sessions/tabs, keyboard input goes nowhere. The user must click the content area to restore input focus.

**Cause:** When reparenting an NSView (removing from one superview and adding to another), the first responder is resigned. The new view is not automatically made first responder.

**Fix:** Set first responder asynchronously after the view is in the window hierarchy:

```swift
view.addSubview(contentView)
DispatchQueue.main.async {
    contentView.window?.makeFirstResponder(contentView)
}
```

The async dispatch is necessary because the view may not be fully in the window hierarchy at the point of `addSubview`. Synchronous `makeFirstResponder` may silently fail.

---

## 10. Dynamic Row Height Not Updating

**Symptom:** Table cells clip content when text changes, or empty space appears below short content. Row heights seem stuck at their initial values.

**Cause:** NSTableView caches row heights. Changing a model property that affects content size (e.g., a subtitle appearing/disappearing) does not automatically trigger row height recalculation.

**Fix:** When a published property that affects row height changes, notify the table:

```swift
// For specific rows:
tableView.noteHeightOfRows(withIndexesChanged: IndexSet(integer: index))

// For all rows (simpler but less efficient):
tableView.reloadData()
```

If using `noteHeightOfRows`, you must also implement `tableView(_:heightOfRow:)` to return the correct height for the current content.
