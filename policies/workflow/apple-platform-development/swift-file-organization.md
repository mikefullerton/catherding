---
title: "Swift File Organization"
summary: "One entity per file; nested types and mixed-in protocol conformance live in extensions in the same file."
triggers: [writing-swift, creating-swift-file, swift-file-audit, refactoring-swift]
tags: [swift, file-organization, apple]
---

# Swift File Organization

Three rules govern what a Swift source file contains and where nested or supplementary declarations go.

## One entity per file

Each Swift file declares **one** top-level entity — one `struct`, `class`, `enum`, `actor`, or `protocol`. The exception is child entities of that top-level entity (see below), which live in the same file.

## Nested entities go in an extension, in the same file

Entities (`struct`, `class`, `enum`, `actor`) that belong to an enclosing entity MUST NOT be declared inside the enclosing entity's body. Declare them in an `extension` on the enclosing entity, in the same file.

Wrong:

```swift
struct Foo {
    enum State {
        case idle, running
    }
}
```

Right:

```swift
struct Foo {
}

extension Foo {
    enum State {
        case idle, running
    }
}
```

## Protocol conformance goes in an extension when possible

Mixed-in protocol conformance SHOULD be declared in an `extension`, not on the primary declaration, so each conformance reads independently.

```swift
struct Foo {
}

extension Foo: MyProtocol {
}
```

Some conformances cannot be satisfied in an extension (e.g. protocols requiring stored properties, or `Decodable` with a custom `init(from:)`). When the compiler forbids extension-based conformance, declare it on the primary type.

**Derived from cookbook:** [srp](../../../../agenticcookbook/principles/srp.md), [separation-of-concerns](../../../../agenticcookbook/principles/separation-of-concerns.md)
