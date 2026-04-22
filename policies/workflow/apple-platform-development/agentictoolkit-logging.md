---
title: "AgenticToolkit Logging"
summary: "Apple projects using AgenticToolkit must implement logging via the Loggable protocol so every subsystem gets a unique log category."
triggers: [using-agentictoolkit, writing-swift, adding-logging, swift-logging-audit]
tags: [swift, logging, agentictoolkit, apple]
---

# AgenticToolkit Logging

For Apple projects using AgenticToolkit, logging support MUST be implemented via the `Loggable` protocol provided by AgenticToolkit.

- Any type that emits log output MUST conform to `Loggable`.
- Conforming to `Loggable` gives each type a unique log category, so logs are filterable per-subsystem.
- Do not call `os.Logger`, `print`, or `NSLog` directly from types that should be observable in logs — conform to `Loggable` instead.

**Derived from cookbook:** [separation-of-concerns](../../../../agenticcookbook/principles/separation-of-concerns.md), [explicit-over-implicit](../../../../agenticcookbook/principles/explicit-over-implicit.md)
