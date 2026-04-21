---
title: "Swift Version"
summary: "All Swift code targets Swift 6.2.x with strict concurrency."
triggers: [starting-swift-project, swift-package-setup, swift-version-audit, xcode-project-conversion]
tags: [swift, language-version, apple, concurrency]
---

# Swift Version

All Swift code targets Swift 6.2.x with strict concurrency.

- All Swift code MUST target the latest patch release of Swift 6.2 (`6.2.x`).
- `Package.swift` files MUST use `// swift-tools-version: 6.2`.
- Code MUST compile cleanly under Swift 6 strict concurrency rules (`@Sendable`, `@MainActor`, strict data-race safety).
- You MUST NOT downgrade to Swift 5 language mode.
- You MUST NOT upgrade to Swift 6.3 or later without an explicit decision to do so.

**Derived from cookbook:** [native-controls](../../../agenticcookbook/principles/native-controls.md)
