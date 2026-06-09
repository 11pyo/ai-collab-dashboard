# Ops Task & Inquiry Dashboard

A tiny, dependency-free **operations dashboard**: a kanban board for tasks and a
4-column board for incoming inquiries — designed so **multiple people (or AI
sessions) can write to it at the same time without corrupting it.**

The trick is the inquiry log: it's an **append-only push log, merged by id**.
Every update is one new line; pushing the same id again merges its fields. No
in-place edits, so concurrent writers never clobber each other. A small Python
helper (`log-inquiry.py`) does the appends behind a short file-lock.

> 📌 **Portfolio / demo build.** A sanitized extract of an internal dashboard I
> built to track day-to-day operations work. All tasks, inquiries, names, and
> teams here are **fictional sample data**.

여러 사람·여러 AI 세션이 **동시에 기록해도 깨지지 않는** 운영 대시보드입니다.
문의 로그를 **append-only(한 줄씩 추가) + id 병합** 방식으로 설계해, 같은 id를
다시 push하면 필드가 병합됩니다. 제자리 수정이 없으니 동시 기록 충돌이 없습니다.

---

## Why it's built this way

A shared dashboard that several people edit *will* hit write races: two writers
load the file, both save, one overwrites the other. The usual fix is a database
or a server. This stays a **static HTML file + a flat JS log** — no backend — and
sidesteps the race a different way:

- **Append-only.** `log-inquiry.py` only ever *appends* a `push({...})` line.
- **Merge by id.** The board folds the log left-to-right (`Object.assign`), so a
  later `{id, status}` line updates just those fields of an earlier record.
- **File lock on append.** A short OS lock (`msvcrt` / `fcntl`) around the append
  prevents two writers from losing a line at EOF.

The result: any number of sessions can record received → in-progress → waiting →
done transitions concurrently, and the board always folds to a consistent view.

## What's in it

- **Task kanban** — `tasks.md` is the source of truth; cards are grouped by
  status and colored by class (DEV / OPS / TS / ADM). Card status can be changed
  in-browser (saved to `localStorage`) and **exported as a JSON diff** to sync
  back to `tasks.md`.
- **Inquiry board** — a 4-column board (received / in-progress / waiting / done)
  folded from `inquiry-log.js`, newest first, with requester and type chips.
- **`log-inquiry.py`** — the append-only, id-merging, lock-guarded logger.

## Quick start

```bash
# open the dashboard (no build, no server needed)
#   just open task-board.html in a browser

# log a new inquiry
python log-inquiry.py --new --type simple --q "How do I look up an employee number?" --by alice --req "bob / sales"
# → NEW id=INQ-260104-091500 status=received

# move it along (same id merges)
python log-inquiry.py --id INQ-260104-091500 --status in-progress
python log-inquiry.py --done --id INQ-260104-091500 --a "Use SU01D, address tab." --ref "#tcode-master"
```

Refresh `task-board.html` to see the inquiry board update.

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

No record is ever rewritten, so two simultaneous writers can't overwrite each
other's work — the worst case is two new lines, both kept.

## Files

| File | Role |
|------|------|
| `task-board.html` | The dashboard UI (kanban + inquiry board). Open directly. |
| `tasks.md` | Source of truth for tasks (fictional sample). |
| `inquiry-log.js` | Append-only inquiry push log (fictional sample). |
| `log-inquiry.py` | CLI to append/transition/close inquiries safely. |
| `docs/` | Vision, git workflow, and AI-collaboration notes. |
| `AGENTS.md` | Orientation for AI assistants working in this repo. |

## Card form structure · 카드 폼 구조 (read before editing the form)

Both card types use a **header (summary) + click-to-expand detail** pattern.

- **Project card `.card`** — rendered by `renderTasks()`. Header: class chip · ID · requester · title + yellow `.next` (next action). Click → `.detail` expands (`.open` toggle).
- **Inquiry card `.inq-card`** — rendered by `renderInquiries()`. Header `.inq-head` (always visible, click target): ▸caret `.inq-cy` + type badge + INQ id + requester chip + yellow `.inq-sum` (the question). `.inq-detail` (collapsed): answer + ref link + date/recorder. The toggle is wired via **event delegation on `#inq-board`**, so it keeps working across re-renders.

**Render ≠ data** (keep these straight):

| Card | Render fn | Data source | How to edit |
|------|-----------|-------------|-------------|
| Project | `renderTasks()` | `TASKS` array (in `task-board.html`) | sync with `tasks.md` by hand; browser edits are localStorage-only |
| Inquiry | `renderInquiries()` | `INQUIRY_LOG` (in `inquiry-log.js`) | **append via `log-inquiry.py` only** — never hand-edit |

> ⚠️ If you change the form, keep the `.inq-sum` / `.inq-detail` / `.inq-cy` CSS and the `#inq-board` toggle delegation **together** — they are one set.

**한국어** — 두 카드 모두 **헤더(요약) + 클릭하면 펼쳐지는 상세** 패턴입니다. 프로젝트 카드 `.card`는 `renderTasks()`, 문의 카드 `.inq-card`는 `renderInquiries()`로 렌더하며, 문의 토글은 `#inq-board` **이벤트 위임**(재렌더에도 유지). **렌더 ≠ 데이터**: 프로젝트=`TASKS` 배열(↔ `tasks.md` 수기 동기화, 브라우저 편집은 localStorage만), 문의=`INQUIRY_LOG`(`log-inquiry.py`로만 추가, 직접 편집 금지). 폼 수정 시 `.inq-sum`·`.inq-detail`·`.inq-cy` CSS와 `#inq-board` 토글 위임을 함께 유지하세요.

## Adapting it

- Edit the `TASKS` array in `task-board.html` (keep it in sync with `tasks.md`),
  or wire `tasks.md` parsing in if you prefer a single source.
- Change the status set / class colors in the `<style>` and the `STATUSES` array.
- `log-inquiry.py` writes next to itself, so drop the folder anywhere and it works.

## Requirements

- A browser (the dashboard is a single static file).
- Python 3.6+ for `log-inquiry.py` (standard library only — no pip installs).

## License

MIT — see [LICENSE](LICENSE).
