# Operations Task Board — source of truth (`tasks.md`)

> Tracks **in-progress work** for a system-operations role in one place, so
> development items and operations items don't get tangled. `task-board.html`
> renders this as a kanban view; this markdown file is the canonical source.
>
> ⚠️ All tasks below are **fictional sample data** for demonstration.

---

## Classification (DEV vs OPS — never mix them up)

| Class | Meaning | Color | ID example |
|-------|---------|-------|-----------|
| **DEV** | Development / programming (source changes) | 🟦 blue | `DEV-001` |
| **OPS** | Operations (data processing, transfers — no coding) | 🟩 green | `OPS-001` |
| **TS** | Troubleshooting (incident / error response) | 🟧 orange | `TS-001` |
| **ADM** | Admin / docs / approvals | ⬜ gray | `ADM-001` |

## Status

| Status | Meaning |
|--------|---------|
| 📥 **received** | Just came in; understanding/triage |
| 🔵 **in-progress** | Actively being worked |
| ⏸️ **waiting** | Blocked externally (approval / reply / another team) — **say what you're waiting on** |
| ✅ **done** | Finished (record result + date) |

## Update rules

1. New task → add a new ID here (prefix = class), then add a card in `task-board.html`.
2. Status change → update status + "next action" + a dated log line; sync the board.
3. `waiting` **must** state what it's waiting on.
4. On done, record the result + date.
5. **Never** put secrets (accounts, passwords, real data) in tasks.

When referencing a task, always write it as `ID — title` (not the bare ID).

---

## Tasks (sample)

### DEV-001 — Add a unit-price column to the sales-proposal screen
- **status**: in-progress
- **requester**: marketing
- **detail**: Show per-line unit price (NETPR) on the proposal screen for review.
- **next action**: spec confirmed; implementation on the dev client, then transport.

### DEV-002 — Monthly billing automation report
- **status**: received
- **requester**: finance
- **detail**: Auto-generate the monthly billing summary instead of manual export.

### OPS-001 — Year-end org restructure: re-map sales proposals
- **status**: done (2026-01-09)
- **requester**: sales ops
- **detail**: Reassign open proposals to the new org units after restructuring.
- **result**: 100% re-mapped and reconciled.

### OPS-002 — Monthly cloud-cost allocation filing
- **status**: in-progress
- **requester**: IT / finance
- **detail**: Allocate the monthly cloud subscription cost across cost centers and file the request.

### TS-001 — Tax-invoice dump at month-end
- **status**: waiting
- **requester**: finance
- **detail**: ABAP dump when issuing a corrective tax invoice.
- **waiting on**: Basis team to grant ST22 access for root-cause analysis.

### ADM-001 — Quarterly access-control review report
- **status**: received
- **requester**: IT GRC
- **detail**: Compile the quarterly user-access review for the controls report.
