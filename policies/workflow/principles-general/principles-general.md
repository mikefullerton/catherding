---
title: "General Principles"
summary: "Map of the 21 cookbook principles that guide this repo, grouped by theme, with one-line hooks and links to the policies that apply each one."
triggers: [starting-work, writing-code, code-review, design-decision]
tags: [principles, general, cross-cutting]
---

# General Principles

All 21 principles in the [agenticcookbook](../../../../agenticcookbook/principles/INDEX.md) are in scope for this repo. This file is the map: the cookbook is authoritative for each principle's definition; the **Applied in** cross-links point to the specific policies that concretize the principle in this author's work.

**Framing:** [meta-principle-optimize-for-change](../../../../agenticcookbook/principles/meta-principle-optimize-for-change.md) — every principle below is a strategy for making future change cheaper and safer. When principles appear to conflict, pick the one that leaves the most room to change direction tomorrow.

## Simplicity and staying small

Prefer less code and smaller decisions; speculation and permanence are liabilities.

- **[simplicity](../../../../agenticcookbook/principles/simplicity.md)** — no interleaving of concerns; simplicity over ease. Applied in [scripting](../../setup/required-tools/scripting.md).
- **[yagni](../../../../agenticcookbook/principles/yagni.md)** — build for today's known requirements, not speculative generality.
- **[design-for-deletion](../../../../agenticcookbook/principles/design-for-deletion.md)** — every line of code is a maintenance liability; build disposable software.
- **[dry](../../../../agenticcookbook/principles/dry.md)** — every piece of knowledge has a single, authoritative representation; DRY is about knowledge, not code shape.
- **[small-reversible-decisions](../../../../agenticcookbook/principles/small-reversible-decisions.md)** — if a decision is cheap to reverse, make it fast.

## Structure

How modules and their boundaries are shaped.

- **[separation-of-concerns](../../../../agenticcookbook/principles/separation-of-concerns.md)** — a module should have one reason to change. Applied in [documentation](../../setup/repo-organization/documentation.md), [llm-file-layout](../../setup/repo-organization/llm-file-layout.md), [multi-platform-layout](../../setup/repo-organization/multi-platform-layout.md).
- **[srp](../../../../agenticcookbook/principles/srp.md)** — a module should be answerable to one and only one actor; complements separation-of-concerns (SoC partitions by kind of concern, SRP by who requests the change).
- **[manage-complexity-through-boundaries](../../../../agenticcookbook/principles/manage-complexity-through-boundaries.md)** — well-defined boundaries let subsystems evolve independently. Applied in [file-organization](../../setup/repo-organization/file-organization.md).
- **[composition-over-inheritance](../../../../agenticcookbook/principles/composition-over-inheritance.md)** — compose behavior from small focused pieces.
- **[dependency-injection](../../../../agenticcookbook/principles/dependency-injection.md)** — components receive their dependencies from the outside.
- **[immutability-by-default](../../../../agenticcookbook/principles/immutability-by-default.md)** — default to immutable; add mutability only when profiling demands it.

## Behavior and correctness

What code does at runtime — no hidden state, early failure, predictability.

- **[explicit-over-implicit](../../../../agenticcookbook/principles/explicit-over-implicit.md)** — hidden behavior creates bugs that take days to find. Applied in [required-tools/all](../../setup/required-tools/all.md), [required-tools/windows](../../setup/required-tools/windows.md), [llm-file-layout](../../setup/repo-organization/llm-file-layout.md), [code-signing](../apple-platform-development/code-signing.md), [xcode-projects](../apple-platform-development/xcode-projects.md).
- **[fail-fast](../../../../agenticcookbook/principles/fail-fast.md)** — surface invalid state immediately at the point of origin. Applied in [code-signing](../apple-platform-development/code-signing.md), [repo-hygiene](../repo-hygiene/repo-hygiene.md).
- **[idempotency](../../../../agenticcookbook/principles/idempotency.md)** — operations should be safe to repeat without duplicate side effects. Applied in [setup-scripts](../../setup/repo-organization/setup-scripts.md).
- **[principle-of-least-astonishment](../../../../agenticcookbook/principles/principle-of-least-astonishment.md)** — APIs, UI, and behavior should match expectations. Applied in [scripting](../../setup/required-tools/scripting.md), [documentation](../../setup/repo-organization/documentation.md), [file-organization](../../setup/repo-organization/file-organization.md), [git-naming](../../setup/repo-organization/git-naming.md), [repo-baseline](../../setup/repo-organization/repo-baseline.md).

## Building on what exists

Prefer shipping to inventing; the platform first, then battle-tested OSS, then your own.

- **[native-controls](../../../../agenticcookbook/principles/native-controls.md)** — always use the platform's built-in frameworks before custom implementations. Applied in [swift-version](../apple-platform-development/swift-version.md), [xcode-projects](../apple-platform-development/xcode-projects.md).
- **[open-source-preference](../../../../agenticcookbook/principles/open-source-preference.md)** — when no native solution exists, reach for battle-tested OSS before rolling your own.

## Workflow

How the work itself gets done — phases, feedback, and automation.

- **[make-it-work-make-it-right-make-it-fast](../../../../agenticcookbook/principles/make-it-work-make-it-right-make-it-fast.md)** — separate correctness, design quality, and performance into sequential phases.
- **[tight-feedback-loops](../../../../agenticcookbook/principles/tight-feedback-loops.md)** — the speed of your feedback loop is the speed of your learning. Applied in [repo-hygiene](../repo-hygiene/repo-hygiene.md).
- **[support-automation](../../../../agenticcookbook/principles/support-automation.md)** — applications should expose their capabilities through automation interfaces. Applied in [repo-baseline](../../setup/repo-organization/repo-baseline.md), [setup-scripts](../../setup/repo-organization/setup-scripts.md), [repo-hygiene](../repo-hygiene/repo-hygiene.md).
