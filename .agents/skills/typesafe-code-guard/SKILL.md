---
name: typesafe-code-guard
description: >-
  Use when navigating codebases, locating obscure business logic, or auditing git diffs
  using the typesafe_find_code and typesafe_audit_diff MCP tools.
---

# TypeSafe Code Guard Skill

This skill guides the AI assistant in using the `typesafe-code-guard` MCP tools for sub-second semantic code discovery and diff verification.

---

## 1. Semantic Code Discovery (`typesafe_find_code`)

### Core Principle: Semantic Intent vs. Dumb Grep
- **Dumb Grep**: Searches literal text strings (`grep "token"`, `grep "timeout"`). Fails when identifiers use synonyms, domain abstractions, or renamed variables (e.g., searching `"session timeout"` misses `IDLE_TTL = 3600`). Causes agents to read endless irrelevant files and bloat the context window.
- **TypeSafe Semantic Discovery**: Evaluates the **meaning, purpose, and behavior** of code against a natural language intent. Pinpoints the exact line range in ~150 ms.

### Formulating Semantic Queries:
Describe the **action**, **business rule**, or **behavior** rather than guessing variable names:

| ❌ BAD (Literal Keyword / Grep Style) | ✅ GOOD (Semantic Intent / Behavior) |
| :--- | :--- |
| `typesafe_find_code(query="token")` | `typesafe_find_code(query="where is the user authentication token refreshed or checked for expiration")` |
| `typesafe_find_code(query="button")` | `typesafe_find_code(query="where is the checkout submit button styling and disabled state handled")` |
| `typesafe_find_code(query="cart")` | `typesafe_find_code(query="where is the shopping cart item count decremented or reset after purchase")` |
| `typesafe_find_code(query="webhook")` | `typesafe_find_code(query="where are incoming Stripe webhook signatures verified against the signing secret")` |

### Targeted Inspection:
`typesafe_find_code` returns the winning file, exact line numbers, and a 15-line preview with confidence scores. Only inspect surrounding lines if strictly necessary; avoid reading whole files.

---

## 2. Diff Reflection & Sanity Checks (`typesafe_audit_diff`)

### Core Principle: Semantic Mirror, Not a Rigid Blocker
Code modifications often have natural ripple effects (e.g., updating a button state may legitimately require adding a flag to global store or updating shared types). `typesafe_audit_diff` acts as a **semantic reflection mirror** to catch accidental regressions and scope creep before reporting completion.

### Calibrated Audit Metrics:
- **`removes_defenses` (> 0.65)**: Indicates defensive code (e.g. `try/catch` blocks, null/undefined checks, input validation guards) was deleted. Restore any essential checks that were inadvertently removed.
- **`leftover_debug` (> 0.75)**: Indicates temporary debugging statements (`console.log`, `print()`, hardcoded mock data, or empty `TODO` stubs) were left behind. Remove them before reporting completion.
- **`touches_state` (> 0.70)**: Indicates global application state, stores, contexts, or database schemas were modified. Reflect on whether modifying global state was strictly necessary for the task or if local state would have been cleaner.
- **`scope_alignment` (> 1.40)**: Indicates substantial scope creep (unrelated files or excessive rewriting). Keep modifications minimal and focused on the requested outcome.

### Self-Correction:
If the audit report highlights critical alerts (such as removed null checks or leftover debug statements), automatically fix them before concluding the turn.

---

## 3. Reference: Building Applications with TypeSafe SDK

If you ever need to build application features using TypeSafe System One directly inside software:
- API endpoint: `POST https://api.typesafe.ai/v1/systemone`
- Flagship model: `jev-latest`
- Primitives: `Choice` (1 of N options), `Score` (rubric scale), `Noul` (True/False probability).
- Python SDK: `pip install typesafe-sdk` (`from typesafe_sdk import TypeSafeClient, Choice, Noul, Score`)
- Live docs: https://docs.typesafe.ai
