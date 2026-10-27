---
name: software-design-philosophy
description: >
  Software design philosophy guide based on John Ousterhout's "A Philosophy of Software Design."
  Use this skill during: code reviews, architecture discussions, API design, module decomposition decisions,
  refactoring guidance, complexity analysis, naming and commenting improvements, error handling strategy design.
  Trigger when the user mentions "code is too complex", "how to split modules", "interface design",
  "reduce coupling", "deep/shallow modules", "information leakage", "error handling", "code readability",
  "design philosophy", "pull complexity down", "define errors out of existence", or similar topics.
  Also trigger for any code review where design quality feedback is requested.
---

# A Philosophy of Software Design — Distilled Guide

> Source: John Ousterhout, *A Philosophy of Software Design*
> Central thesis: **The core challenge of software design is managing complexity.**

---

## I. Complexity: Know the Enemy

### Definition

Complexity is anything related to the structure of a software system that makes it **hard to understand and modify**. Complexity is not the same as system size — a small system can be complex, and a large well-designed system can be manageable.

### Three Symptoms of Complexity

1. **Change Amplification**: A seemingly simple change requires code modifications in many different places.
2. **Cognitive Load**: Developers must absorb a large amount of information to complete a task safely. Note: fewer lines of code ≠ simpler — sometimes more code is actually simpler because it reduces cognitive load.
3. **Unknown Unknowns**: It's unclear which code must be modified or what information is needed to complete a task. This is the most dangerous symptom.

### Two Root Causes

1. **Dependencies**: A piece of code cannot be understood or modified in isolation; it relates to other code that must also be considered.
2. **Obscurity**: Important information is not obvious — vague names, missing docs, implicit conventions, hidden constraints.

### Key Insight

- **Complexity is incremental**: It's not caused by a single catastrophic error; it accumulates through thousands of small decisions.
- Therefore you must adopt a **zero-tolerance** mindset — every bit of "minor" complexity matters.

---

## II. Strategic vs. Tactical Programming

### Tactical Programming (Anti-pattern)
- Goal: get features working as quickly as possible.
- Mindset: "Just make it work", "We'll refactor later."
- Result: complexity accumulates fast, tech debt spirals out of control.

### Strategic Programming (Recommended)
- Goal: produce great design; working code is a byproduct.
- Mindset: **invest roughly 10–20% of development time in design improvements.**
- Practices:
  - Look for opportunities to improve design with every change.
  - Working code is not enough — design quality matters equally.
  - The increments of software development should be **abstractions**, not features.

---

## III. Deep Modules: The Most Important Design Concept

### Core Metaphor

Think of a module as a rectangle:
- **Width** = complexity of its interface
- **Height/Depth** = amount of functionality hidden inside

**Deep module**: simple interface, rich implementation. (Good design)
**Shallow module**: complex interface, does very little. (Bad design 🚩)

### Classic Examples

- **Deep**: Unix file I/O — just 5 syscalls (open, read, write, lseek, close) expose a powerful file system.
- **Shallow**: Java I/O — reading a file requires composing FileInputStream, BufferedInputStream, ObjectInputStream, etc.

### Practical Principles

- Design interfaces so the **most common usage is as simple as possible**.
- A simple interface matters more than a simple implementation.
- Rare use cases can accept more complex calling patterns, but the common path should never pay for them.

---

## IV. Information Hiding and Information Leakage

### Information Hiding
- Each module should encapsulate **design decisions** (knowledge), exposing only a simplified interface.
- Hidden information includes: data structures, algorithms, low-level mechanisms, policy decisions.
- Information hiding minimizes inter-module dependencies.

### Information Leakage 🚩 Red Flag
- When the same design decision is reflected in multiple modules, information has leaked.
- **Temporal decomposition** is a common source: splitting modules by execution order (rather than by information hiding) causes steps to share excessive knowledge.

### Fixing Leakage
- Merge shared knowledge into a single module.
- If merging isn't possible, unify the shared information behind a single deep module.

---

## V. General-Purpose vs. Special-Purpose Modules

### Core Principle: General-purpose modules are usually deeper.

- A general interface is simpler than a specialized one because it covers more use cases with fewer methods.
- When designing a new module, ask: **What is the most general-purpose interface that still feels natural?**

---

## VI. Different Layers, Different Abstractions

- Different layers should expose different abstractions; avoid leaking low-level details upward.
- Each layer should hide complexity for layers above it.

---

## VII. Pull Complexity Downward

- Put complexity in the places where it can be managed best (often deeper modules).
- Avoid forcing callers to handle special cases.

---

## VIII. Define Errors Out of Existence

- Prefer designs that eliminate error cases rather than handling them everywhere.
- If an error case is common, consider changing the interface or invariants.

---

## IX. Design It Twice

- The first design is rarely the best; explore alternatives.
- Use the first design as a baseline, then refine.

---

## X. Comments: The Why, Not the What

- Comments should describe things not obvious from code: intent, rationale, constraints.
- Comments that restate code are noise.

### Comment Layers

- **Interface comments**: describe *what* and *why* — no implementation details.
- **Implementation comments**: explain *how* and *why this approach*.
- **Cross-module comments**: document design decisions and dependencies spanning modules.

---

## XI. The Art of Naming

- Names are lightweight documentation.
- If something is hard to name, the design may be unclear.

---

## XII. Consistency

- Handle the same thing the same way across the system.
- Consistency reduces cognitive load.

---

## XIII. Code Should Be Obvious

- Obviousness is the ultimate test of good design.
- If readers struggle, simplify naming, factoring, and comments.

---

## XIV. Red Flags Quick Reference

| Signal | Meaning |
|--------|---------|
| **Shallow Module** | Interface is nearly as complex as its implementation |
| **Information Leakage** | Same design decision reflected in multiple modules |
| **Temporal Decomposition** | Modules split by execution order, not information hiding |
| **Overexposure** | Common API forces callers to know about rarely-used features |
| **Pass-Through Method** | Method just forwards args to another method |
| **Repetition** | Non-trivial code duplicated across locations |
| **Special-General Mixture** | General-purpose and special-purpose code intertwined |
| **Conjoined Methods** | Understanding one method requires another |
| **Comment Repeats Code** | Comment is just translation of code |
| **Vague Name** | Name too generic |
| **Hard to Pick Name** | Naming struggle implies design issue |
| **Hard to Describe** | Long docs needed implies too complex |
| **Non-Obvious Code** | Behavior not easily understood |

---

## XV. Design Principles Summary

1. Complexity is incremental — sweat the small stuff.
2. Working code isn't enough.
3. Make continual small investments in design.
4. Modules should be deep.
5. Common usage should be simple.
6. Simple interface beats simple implementation.
7. General-purpose modules are deeper.
8. Separate general-purpose and special-purpose code.
9. Different layers, different abstractions.
10. Pull complexity downward.
11. Define errors out of existence.
12. Design it twice.
13. Comments explain the non-obvious.
14. Design for reading.
15. Increments should be abstractions.

---

## Usage Guide

Reference this guide in the following scenarios:

- **Code review**: Use the Red Flags quick reference to spot design problems.
- **API/Interface design**: Aim for deep modules; keep common usage simple.
- **Module decomposition**: Split based on information hiding, not execution order.
- **Error handling**: Prefer "define errors out of existence".
- **Refactoring**: Spend 10–20% of each change improving design.
- **Naming and comments**: Names should be precise; comments cover what code can't.

