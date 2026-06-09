# AGENTS.md — orientation for AI assistants

If you're an AI assistant working in this repo, read this first. It tells you
what the project is, how it's wired, the rules, and how to extend it safely.

## What this is

A dependency-free **operations dashboard**: a kanban board for tasks plus a
4-column board for inquiries. Its defining idea is **concurrency safety without a
backend** — multiple people or AI sessions can record updates at the same time
without overwriting each other. See `README.md` for the full pitch and
`docs/VISION.md` for the why.

## Architecture in one paragraph

The inquiry log (`inquiry-log.js`) is an **append-only push log**. Every update
is a new `window.INQUIRY_LOG.push({...})` line. The dashboard **folds the log by
id** (`Object.assign` in order), so a later `{id, status:"done"}` line just
updates those fields of the earlier record. Because nothing is ever rewritten,
two simultaneous writers can't clobber each other — worst case is two appended
lines, both kept. `log-inquiry.py` performs the appends behind a short OS
file-lock (`msvcrt`/`fcntl`).

## File map

| File | Role | You may edit? |
|------|------|---------------|
| `task-board.html` | UI: renders the task kanban + inquiry board | yes |
| `tasks.md` | **source of truth** for tasks | yes (keep in sync with the `TASKS` array in `task-board.html`) |
| `inquiry-log.js` | append-only inquiry push log | **no — never hand-edit; use `log-inquiry.py`** |
| `log-inquiry.py` | CLI to append/transition/close inquiries | yes (the logic), but preserve append-only + id-merge |
| `docs/` | vision, git, this project's design notes | yes |

## Rules (do not break these)

1. **This is a PUBLIC repo. Only fictional sample data goes in.** Never commit
   real names, customers, internal codes, document numbers, hostnames, or
   credentials. If you add examples, invent them.
2. **Never hand-edit `inquiry-log.js`.** Append through `log-inquiry.py` so the
   append-only + id-merge + lock guarantees hold.
3. **Keep `tasks.md` and the `TASKS` array in `task-board.html` in sync.** They
   represent the same data in two places (markdown source + render).
4. Status vocabulary is fixed: `received → in-progress → waiting → done`.
   `waiting` must state what it's waiting on.

## How to run / test

```bash
# open the board
start task-board.html        # Windows  (or just double-click it)

# exercise the logger
python log-inquiry.py --new --type simple --q "test" --by alice
python log-inquiry.py --id <printed-id> --status in-progress
python log-inquiry.py --done --id <printed-id> --a "resolved"
# then refresh task-board.html
```

Verify: 9 sample push lines fold to 5 unique inquiries; no console errors.

## Good extensions (ideas)

- Parse `tasks.md` directly so the `TASKS` array isn't duplicated.
- A small "import changes" box that applies the exported JSON back into `tasks.md`.
- Filter/search across both boards; per-requester views.
- An inquiry → archive cross-link resolver (the `ref` field).

## Private notes

`NOTES.local.md` (git-ignored) is the human owner's private scratchpad for
vision/ideas that should **not** be public. If it exists, read it for intent, but
**never** copy its contents into committed files.
