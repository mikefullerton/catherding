# SwiftUI to AppKit Pattern Mappings

16 categories of SwiftUI constructs mapped to their AppKit equivalents. Each category includes Before (SwiftUI) and After (AppKit) code examples.

---

## 1. App Lifecycle

### Before (SwiftUI)
```swift
@main
struct MyApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    var body: some Scene {
        WindowGroup(id: "main") { ContentView() }
            .commands { MyCommands() }
        Settings { SettingsView() }
    }
}
```

### After (AppKit)
```swift
@main
final class AppDelegate: NSObject, NSApplicationDelegate {
    var windowControllers: [MainWindowController] = []

    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.run()
    }

    func applicationWillFinishLaunching(_ notification: Notification) {
        NSApp.mainMenu = buildMainMenu()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        openNewWindow()
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { openNewWindow() }
        return true
    }
}
```

**Key details:**
- `@main` moves from App struct to AppDelegate
- `@NSApplicationDelegateAdaptor` is deleted — AppDelegate IS the entry point
- `WindowGroup` → manual `NSWindowController` creation in `applicationDidFinishLaunching`
- `Settings {}` → `SettingsWindowController` singleton opened via Cmd+,
- `.commands {}` → `buildMainMenu()` in `applicationWillFinishLaunching`

---

## 2. Menu Bar

### Before (SwiftUI)
```swift
struct MyCommands: Commands {
    @FocusedObject var manager: SessionManager?
    var body: some Commands {
        CommandGroup(after: .newItem) {
            Button("New Session") { manager?.addSession() }
                .keyboardShortcut("n", modifiers: [.command, .shift])
        }
    }
}
```

### After (AppKit)
```swift
func buildMainMenu() -> NSMenu {
    let mainMenu = NSMenu()

    // File menu
    let fileMenu = NSMenu(title: "File")
    let newSessionItem = fileMenu.addItem(
        withTitle: "New Session",
        action: #selector(newSession),
        keyEquivalent: "n"
    )
    newSessionItem.keyEquivalentModifierMask = [.command, .shift]

    let fileMenuItem = mainMenu.addItem(withTitle: "File", action: nil, keyEquivalent: "")
    mainMenu.setSubmenu(fileMenu, for: fileMenuItem)
    return mainMenu
}

@objc func newSession() {
    if let wc = NSApp.mainWindow?.windowController as? MainWindowController {
        wc.manager.addSession()
    }
}
```

**Key details:**
- `@FocusedObject` routing → `NSApp.mainWindow?.windowController` cast
- `.keyboardShortcut("n", modifiers:)` → `keyEquivalent: "n"` + `keyEquivalentModifierMask`
- Standard menus to build manually: App, File, Edit, View, Window, Help
- Edit menu: use standard selectors (`cut:`, `copy:`, `paste:`, `selectAll:`, `undo:`, `redo:`)
- App menu: About, Settings (Cmd+,), Services, Hide (Cmd+H), Hide Others, Show All, Quit (Cmd+Q)
- Assign `NSApp.servicesMenu` and `NSApp.windowsMenu` explicitly

---

## 3. Window Management

### Before (SwiftUI)
```swift
WindowGroup(id: "main") {
    ContentView()
        .frame(minWidth: 600, minHeight: 400)
}
```

### After (AppKit)
```swift
final class MainWindowController: NSWindowController, NSWindowDelegate {
    let manager = SessionManager()

    init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 800, height: 600),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered, defer: false
        )
        window.title = "My App"
        window.minSize = NSSize(width: 600, height: 400)
        window.setFrameAutosaveName("main-window")
        window.isReleasedWhenClosed = false
        super.init(window: window)
        window.delegate = self
        window.contentViewController = MainSplitViewController(manager: manager)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    func windowWillClose(_ notification: Notification) {
        manager.terminateAll()
        (NSApp.delegate as? AppDelegate)?.removeWindowController(self)
    }
}
```

**Key details:**
- `@StateObject` ownership → stored property on the window controller
- Multi-window: AppDelegate keeps `var windowControllers: [MainWindowController]`
- `isReleasedWhenClosed = false` — **critical** to prevent deallocation on close
- `setFrameAutosaveName` replaces SwiftUI's automatic frame persistence
- Close cleanup: terminate child processes, remove from AppDelegate's array

---

## 4. WindowAccessor Elimination

### Before (SwiftUI)
```swift
struct WindowAccessor: NSViewRepresentable {
    let autosaveName: String
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            view.window?.setFrameAutosaveName(autosaveName)
        }
        return view
    }
    func updateNSView(_ nsView: NSView, context: Context) {}
}
```

### After (AppKit)
**Delete entirely.** Window configuration is done directly in the `NSWindowController` init:
```swift
window.setFrameAutosaveName("main-window")
window.title = "My App"
```

---

## 5. Split Views

### Before (SwiftUI)
```swift
HSplitView {
    SidebarView(manager: manager)
        .frame(minWidth: 150, idealWidth: 200, maxWidth: 300)
    ContentDetailView(session: manager.selectedSession)
        .frame(minWidth: 400)
}
```

### After (AppKit)
```swift
final class MainSplitViewController: NSSplitViewController {
    override func viewDidLoad() {
        super.viewDidLoad()

        let sidebarItem = NSSplitViewItem(sidebarWithViewController: sidebarVC)
        sidebarItem.minimumThickness = 150
        sidebarItem.maximumThickness = 300
        sidebarItem.canCollapse = true

        let contentItem = NSSplitViewItem(viewController: contentVC)
        contentItem.minimumThickness = 400

        addSplitViewItem(sidebarItem)
        addSplitViewItem(contentItem)

        splitView.dividerStyle = .thin
        splitView.autosaveName = "main-split"
    }

    func toggleSidebar() {
        splitViewItems.first?.animator().isCollapsed.toggle()
    }
}
```

**Key details:**
- `NSSplitViewItem(sidebarWithViewController:)` gives standard sidebar behavior
- `splitView.autosaveName` persists divider position — separate from window autosave
- `canCollapse = true` on sidebar enables sidebar toggle
- `.animator()` for smooth collapse/expand animation

---

## 6. List Views → NSTableView

### Before (SwiftUI)
```swift
List(items, selection: $selectedID) { item in
    ItemRowView(item: item)
}
.listStyle(.sidebar)
```

### After (AppKit)
```swift
// Configuration
let scrollView = NSScrollView()
let tableView = NSTableView()
tableView.style = .sourceList
tableView.headerView = nil
tableView.usesAlternatingRowBackgroundColors = false
tableView.allowsEmptySelection = false
tableView.dataSource = self
tableView.delegate = self

let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("Column"))
column.resizingMask = .autoresizingMask
tableView.addTableColumn(column)

scrollView.documentView = tableView

// DataSource
func numberOfRows(in tableView: NSTableView) -> Int {
    items.count
}

// Delegate
func tableView(_ tv: NSTableView, viewFor col: NSTableColumn?, row: Int) -> NSView? {
    let cell = tv.makeView(withIdentifier: ItemCellView.identifier, owner: nil) as? ItemCellView
        ?? ItemCellView(frame: .zero)
    cell.identifier = ItemCellView.identifier
    cell.configure(with: items[row])
    return cell
}

func tableViewSelectionDidChange(_ notification: Notification) {
    guard tableView.selectedRow >= 0 else { return }
    manager.select(id: items[tableView.selectedRow].id)
}
```

**Key details:**
- `.listStyle(.sidebar)` → `tableView.style = .sourceList`
- `List(selection:)` → `tableViewSelectionDidChange` + manual `selectRowIndexes`
- Need bidirectional selection sync (see Pattern 13)
- Dynamic row heights: implement `tableView(_:heightOfRow:)` based on content
- Context menus: `tableView.menu = NSMenu()` using `tableView.clickedRow`
- Cell reuse: `makeView(withIdentifier:)` + `prepareForReuse()` to cancel Combine subscriptions

---

## 7. Custom Cell Views

### Before (SwiftUI)
```swift
struct ItemRowView: View {
    @ObservedObject var item: ItemModel
    var body: some View {
        HStack {
            Circle().fill(item.statusColor).frame(width: 8)
            VStack(alignment: .leading) {
                Text(item.title).font(.body)
                Text(item.subtitle).font(.caption).foregroundStyle(.secondary)
            }
        }
    }
}
```

### After (AppKit)
```swift
final class ItemCellView: NSTableCellView {
    static let identifier = NSUserInterfaceItemIdentifier("ItemCellView")
    private var cancellables = Set<AnyCancellable>()

    private let dotView = NSView()
    private let titleLabel = NSTextField(labelWithString: "")
    private let subtitleLabel = NSTextField(labelWithString: "")

    override init(frame: NSRect) {
        super.init(frame: frame)
        setupLayout()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    func configure(with item: ItemModel) {
        cancellables.removeAll()

        Publishers.CombineLatest(item.$title, item.$statusColor)
            .receive(on: RunLoop.main)
            .sink { [weak self] title, color in
                self?.titleLabel.stringValue = title
                self?.dotView.layer?.backgroundColor = color.cgColor
            }
            .store(in: &cancellables)
    }

    override func prepareForReuse() {
        super.prepareForReuse()
        cancellables.removeAll()
    }
}
```

**Key details:**
- `@ObservedObject` → Combine subscriptions in `Set<AnyCancellable>`
- `prepareForReuse()` must cancel subscriptions to avoid stale updates
- `cancellables.removeAll()` at start of `configure()` AND in `prepareForReuse()`
- SF Symbols: `Image(systemName:)` → `NSImage(systemSymbolName:accessibilityDescription:)`
- Color for layers: `color.cgColor` on `layer.backgroundColor`
- Layout: `NSStackView(views:)` with `.orientation = .vertical` / `.horizontal`
- Truncation: `.lineBreakMode = .byTruncatingTail` (or `.byTruncatingMiddle` for paths)

---

## 8. NSViewRepresentable Elimination

### Before (SwiftUI)
```swift
struct TerminalViewRepresentable: NSViewRepresentable {
    let session: TerminalSession
    func makeNSView(context: Context) -> NSView {
        let container = NSView()
        container.addSubview(session.terminalView)
        return container
    }
    func updateNSView(_ nsView: NSView, context: Context) {
        nsView.subviews.forEach { $0.removeFromSuperview() }
        nsView.addSubview(session.terminalView)
    }
}
```

### After (AppKit)
```swift
final class ContentViewController: NSViewController {
    override func loadView() { view = NSView() }

    func switchToSession(_ session: Session) {
        view.subviews.forEach { $0.removeFromSuperview() }

        let contentView = session.terminalView
        contentView.frame = view.bounds
        contentView.autoresizingMask = [.width, .height]
        view.addSubview(contentView)

        DispatchQueue.main.async {
            contentView.window?.makeFirstResponder(contentView)
        }
    }
}
```

**Key details:**
- Delete the `NSViewRepresentable` wrapper entirely
- The wrapped NSView is managed directly from an `NSViewController`
- Views are **reparented** (not destroyed) to preserve state like scrollback/connections
- `autoresizingMask = [.width, .height]` replaces SwiftUI's automatic layout
- First responder must be set async (after view is in window hierarchy)

---

## 9. Settings Window

### Before (SwiftUI)
```swift
// Sidebar-style settings
Settings {
    NavigationSplitView {
        List(areas, selection: $selectedArea) { area in
            Label(area.title, systemImage: area.icon)
        }
    } detail: {
        switch selectedArea { ... }
    }
}
```

### After (AppKit) — Sidebar Style
```swift
final class SettingsWindowController: NSWindowController {
    static let shared = SettingsWindowController()

    init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 700, height: 450),
            styleMask: [.titled, .closable], backing: .buffered, defer: false
        )
        window.title = "Settings"
        window.isReleasedWhenClosed = false
        super.init(window: window)
        // Use NSSplitViewController with sidebar + detail
    }

    func showSettings() {
        showWindow(nil)
        window?.makeKeyAndOrderFront(nil)
    }
}
```

**IMPORTANT:** If the SwiftUI settings used `NavigationSplitView`, use `NSSplitViewController` with a source-list sidebar — NOT `NSTabViewController`. `NSTabViewController(.toolbar)` gives the wrong appearance for sidebar-style settings.

If the SwiftUI settings used `TabView`, then use `NSTabViewController` with `.tabStyle = .toolbar`.

### Tab-Style Settings (alternative)
```swift
let tabVC = NSTabViewController()
tabVC.tabStyle = .toolbar
tabVC.addTabViewItem(generalTab)
tabVC.addTabViewItem(profilesTab)
window.contentViewController = tabVC
```

**Key details:**
- Singleton pattern — settings window survives close
- `isReleasedWhenClosed = false` — critical for singleton
- `showWindow(nil)` + `makeKeyAndOrderFront(nil)` — both needed to bring forward
- `window.toolbar = nil` if using sidebar style to remove auto toggle button
- Each settings area is a separate `NSViewController` swapped into the detail container

---

## 10. Form Controls (@AppStorage → UserDefaults)

### Before (SwiftUI)
```swift
@AppStorage("general.startupBehavior") var startup = "newWindow"
@AppStorage("general.showWelcome") var showWelcome = true
@AppStorage("general.fontSize") var fontSize = 14.0

Picker("On startup", selection: $startup) { ... }
Toggle("Show welcome", isOn: $showWelcome)
Slider(value: $fontSize, in: 10...24)
TextField("Name", text: $name)
SecureField("API Key", text: $apiKey)
```

### After (AppKit)
```swift
// Read in viewDidLoad()
let startup = UserDefaults.standard.string(forKey: SettingsKeys.startup) ?? "newWindow"
let showWelcome = UserDefaults.standard.bool(forKey: SettingsKeys.showWelcome)

// Picker → NSPopUpButton
let popUp = NSPopUpButton()
popUp.addItems(withTitles: ["New Window", "Restore Last"])
for (i, item) in popUp.itemArray.enumerated() {
    item.representedObject = ["newWindow", "restoreLast"][i]
}
popUp.target = self
popUp.action = #selector(startupChanged)

// Toggle → NSButton (checkbox)
let toggle = NSButton(checkboxWithTitle: "Show welcome",
                      target: self, action: #selector(welcomeChanged))
toggle.state = showWelcome ? .on : .off

// Slider → NSSlider
let slider = NSSlider(value: fontSize, minValue: 10, maxValue: 24,
                      target: self, action: #selector(fontSizeChanged))

// TextField → NSTextField
let field = NSTextField()
field.delegate = self // use controlTextDidChange for live saving

// SecureField → NSSecureTextField
let secure = NSSecureTextField()
secure.delegate = self // controlTextDidChange for save-on-type

// Write in action handlers
@objc func startupChanged() {
    if let val = popUp.selectedItem?.representedObject as? String {
        UserDefaults.standard.set(val, forKey: SettingsKeys.startup)
    }
}
```

**Key details:**
- `@AppStorage` → direct `UserDefaults.standard` read/write
- NSPopUpButton: use `representedObject` for raw values, not item titles
- To select saved value on load: iterate `itemArray`, match `representedObject`
- SwiftUI `onChange` saves on every keystroke → AppKit needs `controlTextDidChange` delegate
- Form layout: `NSStackView` with helper that creates label + control in horizontal stack

---

## 11. Color Handling

| SwiftUI | AppKit |
|---------|--------|
| `Color.green` | `NSColor.green` (NOT `.systemGreen` — different color) |
| `Color.red` | `NSColor.red` |
| `Color.secondary` | `NSColor.secondaryLabelColor` |
| `Color(hex:)` | `NSColor(hex:)` (port the extension) |
| `.foregroundStyle(.secondary)` | `imageView.contentTintColor = .secondaryLabelColor` |
| Color swatch `RoundedRectangle().fill()` | `NSView` with `wantsLayer = true`, `layer.cornerRadius`, `layer.backgroundColor` |

**Key detail:** `NSColor.systemGreen` ≠ `SwiftUI.Color.green`. Use `NSColor.green` for an exact match.

---

## 12. Observable Pattern (Combine Stays)

**No change needed.** `ObservableObject` + `@Published` + Combine works identically with AppKit.

```swift
// In NSViewController
manager.$items
    .receive(on: RunLoop.main)
    .sink { [weak self] _ in self?.tableView.reloadData() }
    .store(in: &cancellables)
```

| SwiftUI | AppKit |
|---------|--------|
| `@StateObject var x = X()` | Property owned by window controller: `let x = X()` |
| `@ObservedObject var x` | Combine subscription in view controller |
| `@Published var prop` | Unchanged — works with AppKit |
| `@EnvironmentObject` | Direct property injection via init or configure method |

**Key details:**
- Always use `[weak self]` in sink closures to avoid retain cycles
- Always `.receive(on: RunLoop.main)` for UI updates
- Observe `UserDefaults.didChangeNotification` for settings changes

---

## 13. Bidirectional Selection Sync

Critical pattern for NSTableView ↔ model selection sync:

```swift
private var isUpdatingSelection = false

// Model → Table (Combine subscription)
manager.$selectedID
    .receive(on: RunLoop.main)
    .sink { [weak self] id in
        guard let self, !self.isUpdatingSelection else { return }
        guard let index = self.items.firstIndex(where: { $0.id == id }) else { return }
        self.tableView.selectRowIndexes(IndexSet(integer: index), byExtendingSelection: false)
    }
    .store(in: &cancellables)

// Table → Model (delegate)
func tableViewSelectionDidChange(_ notification: Notification) {
    guard tableView.selectedRow >= 0 else { return }
    isUpdatingSelection = true
    manager.select(id: items[tableView.selectedRow].id)
    isUpdatingSelection = false
}
```

**Without the `isUpdatingSelection` guard flag, you get infinite loops.**

---

## 14. Context Menus

### Before (SwiftUI)
```swift
.contextMenu {
    Button("Rename") { rename(item) }
    Button("Delete") { delete(item) }
}
```

### After (AppKit)
```swift
let menu = NSMenu()
menu.addItem(withTitle: "Rename", action: #selector(renameItem), keyEquivalent: "")
menu.addItem(withTitle: "Delete", action: #selector(deleteItem), keyEquivalent: "")
tableView.menu = menu

@objc func renameItem() {
    let row = tableView.clickedRow
    guard row >= 0 else { return }
    // rename items[row]
}
```

**Key detail:** Use `tableView.clickedRow` (not `selectedRow`) in context menu actions — the clicked row may differ from the selected row.

---

## 15. Build System Notes

| Build System | File Management |
|-------------|----------------|
| **XcodeGen** (`project.yml`) | Auto-discovers sources — run `xcodegen generate` after adding/removing files |
| **Swift Package Manager** | Auto-discovers sources under `Sources/` |
| **Raw `.xcodeproj`** | New files must be added to target's compile sources manually. Fragile. |

Build command:
```bash
xcodebuild -project MyApp.xcodeproj -scheme MyApp build
# or with SPM plugin validation skip:
xcodebuild -project MyApp.xcodeproj -scheme MyApp -skipPackagePluginValidation build
```

---

## 16. init(coder:) Unavailability Pattern

Every programmatic NSViewController, NSWindowController, NSView, and NSTableCellView subclass must include:

```swift
@available(*, unavailable)
required init?(coder: NSCoder) {
    fatalError("init(coder:) is not supported")
}
```

This prevents accidental use from storyboards/nibs (which are not used in programmatic AppKit).
