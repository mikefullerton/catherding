---
name: general-principles
description: Use at the start of non-trivial work, during code review, or when making a design decision — whenever there's a judgment call about code shape, module boundaries, or what to build. Loads the 21 cookbook principles that guide this author's work, grouped by theme, with one-line hooks per principle.
---

# General Principles — guiding heuristics

These are **design heuristics for judgment calls**, not rigid rules. When two principles appear to conflict, prefer the one that leaves the most room to change direction tomorrow — that is the **meta-principle: optimize for change**.

Before making a non-trivial design decision, scan the list below and name the principles in tension. If none apply, proceed. If several do, the choice becomes explicit instead of implicit.

## Simplicity and staying small

Prefer less code and smaller decisions; speculation and permanence are liabilities.

- **simplicity** — no interleaving of concerns; simplicity over ease.
- **yagni** — build for today's known requirements, not speculative generality.
- **design-for-deletion** — every line is a maintenance liability; make code disposable.
- **dry** — every piece of *knowledge* has a single authoritative representation (not every line of code).
- **small-reversible-decisions** — if a decision is cheap to reverse, make it fast.

## Structure

How modules and their boundaries are shaped.

- **separation-of-concerns** — a module should have one reason to change (partition by kind of concern).
- **srp** — a module should be answerable to one actor (partition by who requests the change).
- **manage-complexity-through-boundaries** — well-defined boundaries let subsystems evolve independently.
- **composition-over-inheritance** — compose behavior from small focused pieces.
- **dependency-injection** — components receive their dependencies from the outside.
- **immutability-by-default** — default to immutable; add mutability only when profiling demands it.

## Behavior and correctness

What code does at runtime — no hidden state, early failure, predictability.

- **explicit-over-implicit** — hidden behavior creates bugs that take days to find.
- **fail-fast** — surface invalid state immediately at the point of origin.
- **idempotency** — operations should be safe to repeat without duplicate side effects.
- **principle-of-least-astonishment** — APIs, UI, and behavior should match expectations.

## Building on what exists

Prefer shipping to inventing; the platform first, then battle-tested OSS, then your own.

- **native-controls** — use the platform's built-in frameworks before custom implementations.
- **open-source-preference** — when no native solution exists, reach for battle-tested OSS before rolling your own.

## Workflow

How the work itself gets done — phases, feedback, and automation.

- **make-it-work-make-it-right-make-it-fast** — separate correctness, design quality, and performance into sequential phases.
- **tight-feedback-loops** — the speed of your feedback loop is the speed of your learning.
- **support-automation** — expose capabilities through automation interfaces.

## Meta

- **meta-principle-optimize-for-change** — every principle above is a strategy for making future change cheaper and safer. Use this as the tiebreaker when principles conflict.

## How to use this in practice

- **Starting work:** scan the headings; note any that apply to what you're about to build.
- **Code review:** name the principle a change advances or violates, rather than appealing to taste.
- **Design decision:** when two approaches look equivalent, pick the one with stronger hooks into these principles — especially `design-for-deletion`, `small-reversible-decisions`, and the meta-principle.

## Reference

The policy map with cross-links to the concrete policies that apply each principle:

- [principles-general.md](../../policies/workflow/principles-general/principles-general.md)

Full definitions in the cookbook:

- [agenticcookbook/principles/INDEX.md](../../../agenticcookbook/principles/INDEX.md)

Start at [policies/INDEX.md](../../policies/INDEX.md) to navigate related policies.
