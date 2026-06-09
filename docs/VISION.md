# Vision & Ideas

> The product vision behind this dashboard. Written to be public — it's about the
> *idea*, not any specific organization. Private, personal notes live in
> `NOTES.local.md` (git-ignored).

## The problem

Operations work — the steady stream of requests, incidents, and small tasks that
keep a system running — usually lives in chat threads, inboxes, and people's
heads. Two things go wrong:

1. **It's invisible.** Nobody can see, at a glance, what's in flight, what's
   blocked, and on whom.
2. **It doesn't survive collaboration.** The moment two people (or an AI
   assistant and a person) try to update the same shared file, one overwrites the
   other.

## The bet

A shared operational record can be **simple, file-based, and still safe for
concurrent writers** — no database, no server — if you change *how* it's written:

- **Append, never overwrite.** Every change is a new line. History is the file.
- **Fold by id.** The current state is computed by replaying the log.
- **Lock only the append.** A tiny critical section keeps writers from colliding.

This is the same insight behind event sourcing and CRDTs, shrunk to a single
static HTML file and a 100-line Python helper. It means a human and any number of
AI sessions can all log updates to the same board at once, and it always folds to
a consistent view.

## Why this matters for AI-native operations

When an AI assistant handles routine operations work, it needs a **shared memory
it can write to safely** — a place to record "received this request,"
"in-progress," "blocked on team X," "done, here's the resolution." A backend-less,
append-only log is ideal: the AI appends with one command, the human sees it on
the board, and neither stomps the other. The dashboard becomes the contract
between human and AI.

## The bigger picture

This is one half of a pair:

- **[Third Brain — Indexable Knowledge Archive](../../third-brain-archive)** —
  the *memory*: an AI-searchable archive of operational knowledge.
- **This dashboard** — the *workflow*: a concurrency-safe board for the work in
  flight.

Together: knowledge that compounds + work that's visible and collaborative,
both designed so a person and their AI assistant operate as one.

## Ideas / roadmap

- **Single source of truth.** Parse `tasks.md` directly instead of duplicating
  the `TASKS` array in the HTML.
- **Round-trip sync.** "Export changes" already emits a JSON diff; add an
  "apply" path that writes it back to `tasks.md`.
- **Cross-link to the archive.** Resolve an inquiry's `ref` anchor into the
  knowledge archive so an answer is one click away.
- **Org/requester views.** Group by requester or team; surface who's waiting.
- **Metrics.** Time-in-status, throughput, and aging of `waiting` items.
