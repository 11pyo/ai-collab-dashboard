# Ops Task & Inquiry Dashboard

**🌐 Language: [한국어](./README.md) · English (this page)** · 💬 [Discussions](https://github.com/11pyo/ai-collab-dashboard/discussions)

> A tiny, dependency-free **operations dashboard** — a kanban board for tasks and a 4-column board for
> inquiries — built so **multiple people (or AI sessions) can write to it at the same time without
> corrupting it.**
> 📌 Portfolio/demo build — all data is fictional sample data.

> 🌍 **Any team — not just IT.** The samples have an IT/ops flavor (classes DEV/OPS/TS/ADM, SAP-ish
> examples), but it works for **any team's task/request tracking** — marketing, a research lab, customer
> support, admin, etc. Swap the classes, statuses, and data for your own.

> 🧭 **Two repos (separate tools):** 🗂️ **ai-collab-dashboard** (this repo) = the task board · 🧠 **[Third-Party-Brain](https://github.com/11pyo/Third-Party-Brain)** = the AI-searchable knowledge brain. *This dashboard runs fully on its own — no archive required.*

## 🤖 Build / run with an AI
**✅ Demo included.** Clone and it **runs right away** with sample tasks + inquiries. Hand the folder to
your AI and say **"Read `AGENTS.md` and set this up"** — it offers an easy choice (it won't just pop
open the file):
- **Ⓐ See the demo** → open `task-board.html` (explore the sample as-is).
- **Ⓑ Set it up for me** → the AI asks for your **task list, status set, and classification**, then
  fills them in (replacing the sample; it won't invent data).

**✏️ Edit directly (no Claude, no server)** — the **Edit** button (bottom-right) lets you fix cards in place, **➕ add** / 🗑 delete tasks, and **💾 Save** writes back to the file. Chrome/Edge save in place; other browsers download. (Simple edits don't need to go through Claude.)

**🤖 AI context log — two-layer cards (new)** — long-running dev cards accumulate a time-series of fixes and insights, and **you can't shorten it without the AI losing context.** So each card is now two layers: top = a **curated body** (for humans — the current state, well organized), bottom = a collapsible **🤖 AI context log** (work log, lessons, policies the AI committed to — the card's `ailog` field). **Humans only read the body; AI assistants automatically read the collapsed log too** (rule in AGENTS.md). Keep appending without cluttering the screen. History: [CHANGELOG.md](./CHANGELOG.md)

> 💡 **Nervous about "overwriting the existing file"?** It's not someone else's file — you're just **updating your own file with the edits you just made**; nothing is wiped, your changes are merged in. **The first time only**, pick `task-board.html` and confirm "overwrite"; after that it **remembers the location** and saves in one click (no folder-hunting). You can keep the page **open** while saving. If it still makes you uneasy, copy the original once as a backup the first time.

**Standalone** — works fully **without the archive** (Third-Party-Brain); they're separate tools.
**Prereqs:** a browser; Python 3.6+ for the `log-inquiry.py` helper (nothing to install).

## What it is
A server-less ops board that runs on one static HTML file plus a small Python helper. Two boards on one screen:
- **Task kanban** — work in flight, grouped by status (received · in-progress · waiting · done).
- **Inquiry board** — incoming inquiries in the same four columns.

The trick: the inquiry log is **append-only + merged by id** — every update is a new line, and pushing the same id again merges its fields. No in-place edits, so concurrent writers never clobber each other.

## Inspiration — Toyota Kanban
The board form (work as **cards** flowing across status **columns**) traces its lineage to the **Toyota Production System's kanban (看板)** just-in-time signaling, which carried into the Lean/Agile *Kanban method*. So the **work-flow visualization is inspired by Toyota's kanban.**
> That said, this dashboard's **distinctive part (append-only + id-merge concurrency safety, no backend)** is not from Toyota — it's closer to **event sourcing / log-structured** ideas. Toyota = the board/flow-visualization root; the concurrency design is its own thing.

## Why it's built this way
A shared file that several people edit *will* hit write races (two open it, both save, one overwrites the other). The usual fix is a database or a server. This stays a **static HTML file + flat JS log** and sidesteps the race differently:
- **Append-only.** `log-inquiry.py` only ever appends a `push({...})` line.
- **Merge by id.** The board folds the log left-to-right (`Object.assign`), so a later `{id, status}` updates just those fields.
- **Lock only the append.** A short OS lock (`msvcrt`/`fcntl`) stops two writers losing a line at EOF.

The result: any number of sessions can record received → in-progress → waiting → done concurrently, and the board always folds to a consistent view.

## What's in it
| File | Role |
|------|------|
| `task-board.html` | The dashboard UI (kanban + inquiry board). Open directly. |
| `tasks.md` | Source of truth for tasks (fictional sample). |
| `inquiry-log.js` | Append-only inquiry push log (fictional sample). |
| `log-inquiry.py` | CLI to append/transition/close inquiries safely. |
| `docs/` | Vision and git-workflow notes. |
| `AGENTS.md` | Orientation for AI assistants working in this repo. |

## Quick start
**① Open the dashboard** — double-click `task-board.html` (no server).

**② Just tell your AI to log inquiries** — you don't type commands. Say *"log this inquiry"*, *"move it to in-progress"*, *"answer and close it"*, and the AI runs `log-inquiry.py` **for you**. (The whole point: you don't memorize a CLI — **the AI records it for you, safely.**)

**③ Refresh** `task-board.html` to see it update.

<details><summary>↳ What the AI actually runs (expand only if you'd rather type it yourself)</summary>

```bash
# log a new inquiry
python log-inquiry.py --new --type simple --q "How to find an employee number?" --by alice --req "bob / sales"
# → NEW id=INQ-260104-091500 status=received

# move it along (same id merges)
python log-inquiry.py --id INQ-260104-091500 --status in-progress
python log-inquiry.py --done --id INQ-260104-091500 --a "Use SU01D, address tab." --ref "#tcode-master"
```
</details>

## How concurrency-safety works (the core idea)
```
log-inquiry.py (writer A) ──┐                       inquiry-log.js (append-only)
log-inquiry.py (writer B) ──┤   short file-lock ►   push({id:7, status:"received"})
log-inquiry.py (writer C) ──┘   around append       push({id:7, status:"in-progress"})
                                                     push({id:9, status:"received"})
                                                     push({id:7, status:"done", a:"..."})
                                                              │
                          task-board.html  ◄── fold by id (Object.assign, in order)
                                                              ▼
                                            id 7 → {status:"done", a:"..."},  id 9 → {received}
```
No record is ever rewritten, so two simultaneous writers can't overwrite each other — worst case is two appended lines, both kept.

## Card form structure (read before editing the form)
Both card types use a **header (summary) + click-to-expand detail** pattern.
- **Project card `.card`** — rendered by `renderTasks()`. Header: class chip · ID · requester · title + yellow `.next` (next action). Click → `.detail` expands (`.open` toggle).
- **Inquiry card `.inq-card`** — rendered by `renderInquiries()`. Header `.inq-head` (always visible, click target): ▸caret `.inq-cy` + type badge + INQ id + requester chip + yellow `.inq-sum` (the question). `.inq-detail` (collapsed): answer + ref link + date/recorder. Toggle is wired via **event delegation on `#inq-board`**, so it survives re-renders.

**Render ≠ data** (keep these straight):

| Card | Render fn | Data source | How to edit |
|------|-----------|-------------|-------------|
| Project | `renderTasks()` | `TASKS` array (in `task-board.html`) | sync with `tasks.md` by hand; browser edits are localStorage-only |
| Inquiry | `renderInquiries()` | `INQUIRY_LOG` (in `inquiry-log.js`) | **append via `log-inquiry.py` only** — never hand-edit |

> ⚠️ If you change the form, keep the `.inq-sum` / `.inq-detail` / `.inq-cy` CSS and the `#inq-board` toggle delegation **together**.

## Adapting it
- Replace the `TASKS` array in `task-board.html` with your own (sync with `tasks.md`).
- Change the status set / class colors in the `<style>` and the `STATUSES` array.
- `log-inquiry.py` writes next to itself, so drop the folder anywhere and it works.

## Requirements
- A browser (the dashboard is a single static file).
- Python 3.6+ for `log-inquiry.py` (standard library only — no installs).

## License
MIT — see [LICENSE](LICENSE).
