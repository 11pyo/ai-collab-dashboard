# SCALING — Upgrade Guide for When Data Grows (v2 blueprint)

> This dashboard is a backend-free single HTML file. As data accumulates (inquiry-log pushes, the AI-reference-log text on cards), the browser can get heavy.
> This document is the blueprint for **when (thresholds) · what · how** to upgrade. When a threshold is reached, have the AI generate v2 based on this document.
> Core premise: this system assumes **all work is delegated to AI while a human supervises**. Therefore every optimization must **never cut off the AI's access to context**.
> ✅ **Verified**: Stages A·B and the helper (`--compact`/`--archive-before`) are implemented and verified in [`demo-v2/`](../demo-v2/) on bulk fictional data (315 inquiries / 891 pushes).

---

## 0. Core principle — "Render local, search global"

Hide past data only in the browser view (for the human) to keep performance up. The **AI's data access always covers everything**. This single principle governs every stage.

Why this causes no bottleneck or confusion for the AI:

1. **The source of truth for knowledge is not the log.** The processing history (`inquiry-log.js`) is just a log; the real knowledge (procedures, lessons, policies) persists in the knowledge archive (e.g. `archive.html`), the card's AI log (`ailog`), and AI memory. Splitting completed items out of the log means **no loss of knowledge access for the AI**.
2. **Grep scans everything regardless of file count.** Even after moving the past into `inquiry-log-archive-*.js`, a wildcard search finds active + archive at once.
3. **A smaller active file makes the AI's daily reads lighter (fewer tokens).** Optimization actually helps the AI.

---

## 1. Thresholds — when to do what

| Data size | Symptom | Stage to apply |
|---|---|---|
| ~dozens (current) | none | **do nothing** (avoid premature optimization) |
| 100+ completed | first load slightly slower | **Stage A** (lazy-render ailog) → **Stage B** (archive completed items) |
| thousands | log file several MB, too many DOM nodes | **Stage C** (log compaction) → **Stage D** (virtualize the Done column) |

Principle: **one stage at a time**, only when symptoms actually appear. Don't pre-apply everything without measuring.

---

## 2. Per-stage design (v2 implementation spec)

### Stage A — Lazy-render the AI reference log (ailog)  ★best value, no side effects
**Problem**: a card's `ailog` text lives fully in the DOM even when collapsed → hundreds of cards explode node/string counts.
**Fix**: don't put ailog text in the DOM initially; inject it once when the `<details>` is opened.

```js
const AILOG = {};                       // id -> ailog text (filled from TASKS/log)
document.querySelectorAll('details.ailog').forEach(d => {
  d.addEventListener('toggle', () => {
    const body = d.querySelector('.ailog-body');
    if (d.open && !body.dataset.filled) {
      body.textContent = AILOG[d.dataset.ailogId] || '';
      body.dataset.filled = '1';        // inject once
    }
  });
});
```
**AI impact**: none. The AI reads source files (tasks.md / TASKS array), not the DOM, so ailog data stays accessible.

### Stage B — Archive completed items  ★biggest file-size reduction
**Problem**: an append-only log grows without bound → full download/parse on every load.
**Fix**: move items completed before a cutoff into a half-year archive file. The view loads only the active set; the past is behind a button.

- Naming (required): `inquiry-log.js` (active) + `inquiry-log-archive-2026H1.js` (past). **Same push format/structure** → Grep/parse compatible.
- `task-board.html`: load only the active set by default. A "View past history" button dynamically injects the archive js as a `<script>` and re-renders.
- **`metrics` and book-material aggregation sum active + archive (everything)** — these are cumulative figures, so dropping the past would shrink the numbers.
- Add a split command to the helper:

```bash
# Move completed items before a date into the archive file (remove from active)
python log-inquiry.py --archive-before 2026-07-01   # -> creates/appends inquiry-log-archive-2026H1.js
```
**Guardrails (block AI impact)**:
- Always search history across all `inquiry-log*.js` (wildcard Grep).
- Completion writes always append to the **active file only**.
- State both lines in AGENTS.md/CLAUDE.md.

### Stage C — Log compaction
**Problem**: many state-transition pushes accumulate per id (received→in-progress→waiting→done) → line count explodes.
**Fix**: rewrite the several pushes of one id into a single merged snapshot of the current state. Keep append-only concurrency safety, but run only at a quiet time.

```bash
python log-inquiry.py --compact                  # merge each id's pushes into one latest line
python log-inquiry.py --compact --keep-history   # back up the time series separately if needed
```
**Caution**: if intermediate time-series steps hold lessons, they must already be preserved in the card `ailog` / knowledge archive / memory (verify before compaction). The log holds "state"; the archive is the source of truth for knowledge.

### Stage D — Virtualize the Done column / "recent N + load more"
**Problem**: rendering hundreds of completed cards into the DOM at once.
**Fix**: render only what's visible. Simplest form: default the Done column to "recent 30" with a "load more" incremental render (a lightweight alternative to full virtual scrolling).

---

## 3. How to have the AI run the upgrade

1. Trigger: **"upgrade the dashboard to v2"** or **"we passed the threshold, optimize."**
2. The AI reads this `SCALING.md` + the current data size and applies **only the relevant stage** (per the threshold table).
3. After each stage, it must pass the **guardrail checklist** (below) to be considered done.
4. Record the change in `CHANGELOG.md` (date, stage, files affected).

### Guardrail checklist (required from Stage B onward)
- [ ] Archive file has the **same format/naming** as active (`inquiry-log-archive-*.js`)
- [ ] History search targets **all** `inquiry-log*.js`
- [ ] Completion writes go to the **active file only**
- [ ] `metrics`/aggregation sums **everything including the archive**
- [ ] AGENTS.md/CLAUDE.md state the above rules

> Pass this checklist and, no matter how much data piles up, **the human view stays light and the AI's context stays whole**. That is the purpose of this document.
