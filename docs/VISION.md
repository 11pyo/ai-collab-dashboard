# Vision & Ideas · 비전과 아이디어

> The product vision behind this dashboard. Written to be public — it's about the *idea*.
> Private, personal notes live in `NOTES.local.md` (git-ignored).
> 이 대시보드의 제품 비전. 공개용으로 *아이디어* 중심. 개인적 메모는 `NOTES.local.md`(gitignore).

---

## English

### The problem
Operations work — the steady stream of requests, incidents, and small tasks that keep a system
running — usually lives in chat threads, inboxes, and people's heads. Two things go wrong:
1. **It's invisible.** Nobody can see, at a glance, what's in flight, what's blocked, and on whom.
2. **It doesn't survive collaboration.** The moment two people (or an AI assistant and a person) try
   to update the same shared file, one overwrites the other.

### Inspiration — Toyota Kanban
The board itself follows the **Kanban method**: visualize work as cards flowing across status
columns. That practice traces directly to the **Toyota Production System's kanban (看板)** — Taiichi
Ohno's just-in-time signaling cards — which the Lean/Agile movement adapted for knowledge work.
So the *work-flow visualization* is inspired by Toyota's kanban. The dashboard's **own** contribution
— a backend-less, append-only, id-merged log that's safe for concurrent writers — is a separate idea,
closer to **event sourcing / log-structured** systems.

### The bet
A shared operational record can be **simple, file-based, and still safe for concurrent writers** — no
database, no server — if you change *how* it's written: append, never overwrite; fold by id; lock only
the append. This is the event-sourcing/CRDT insight shrunk to one static HTML file + a ~100-line
Python helper. A human and any number of AI sessions can all log updates at once, and it always folds
to a consistent view.

### Why this matters for AI-native operations
When an AI assistant handles routine ops work, it needs a **shared memory it can write to safely** — a
place to record "received," "in-progress," "blocked on team X," "done." A backend-less append-only log
is ideal: the AI appends with one command, the human sees it on the board, neither stomps the other.
The dashboard becomes the contract between human and AI.

### The bigger picture
This is one half of a pair:
- **[Third Brain — Indexable Knowledge Archive](https://github.com/11pyo/Third-Party-Brain)** — the
  *memory*: an AI-searchable archive of operational knowledge (the `Third-Party-Brain` repo; this
  dashboard is also mirrored there under `reference-implementation/dashboard/`).
- **This dashboard** — the *workflow*: a concurrency-safe board for the work in flight.

Together: knowledge that compounds + work that's visible and collaboration-safe.

### Ideas / roadmap
- Single source of truth: parse `tasks.md` directly instead of duplicating the `TASKS` array.
- Round-trip sync: the board's "export changes" emits a JSON diff; add an "apply" path back to `tasks.md`.
- Cross-link an inquiry's `ref` anchor into the knowledge archive.
- Org/requester views; time-in-status and aging metrics.

---

## 한국어

### 문제
운영 업무 — 시스템을 굴러가게 하는 요청·장애·잔무의 끊임없는 흐름 — 은 보통 메신저·메일·사람 머릿속에
흩어져 있습니다. 그래서 두 가지가 어긋납니다.
1. **안 보인다.** 무엇이 진행 중이고, 무엇이 누구 때문에 막혔는지 한눈에 알 수 없음.
2. **협업에 취약하다.** 두 사람(또는 AI와 사람)이 같은 공유 파일을 동시에 고치는 순간, 하나가 덮어씀.

### 영감 — 토요타 칸반
보드 자체는 **칸반 방식**을 따릅니다: 작업을 카드로 만들어 상태 컬럼 사이로 흘려보내 시각화. 이 방식은
**토요타 생산방식의 칸반(看板)** — 오노 다이이치의 적시생산(JIT) 신호 카드 — 에서 직접 유래해, Lean·Agile이
지식노동용으로 가져온 것입니다. 즉 *작업 흐름 시각화*가 토요타 칸반에서 영감을 얻었습니다. 다만 이
대시보드의 **고유** 기여 — 무백엔드·추가전용·id병합으로 동시 기록에 안전한 로그 — 는 별개로, **이벤트
소싱/로그 구조** 시스템에 가깝습니다.

### 베팅
공유 운영 기록은 **단순한 파일 기반이면서도 동시 기록에 안전**할 수 있습니다 — DB도 서버도 없이 — *쓰는
방식*만 바꾸면: 덮어쓰지 말고 추가만, id로 접기, 추가 순간만 잠그기. 이는 이벤트 소싱/CRDT의 통찰을 정적
HTML 한 파일 + 100줄짜리 파이썬 헬퍼로 줄인 것입니다. 사람과 임의 개수의 AI 세션이 동시에 기록해도 항상
일관된 화면으로 접힙니다.

### AI 네이티브 운영에 왜 중요한가
AI가 일상 운영을 맡으면 **안전하게 쓸 수 있는 공유 기억**이 필요합니다 — "접수"·"진행중"·"X팀 대기"·"완료"를
기록할 곳. 무백엔드 추가전용 로그가 이상적입니다: AI는 명령 하나로 추가하고, 사람은 보드에서 보고, 서로
덮어쓰지 않습니다. 대시보드가 사람과 AI 사이의 계약이 됩니다.

### 큰 그림
이건 한 쌍의 절반입니다:
- **[제3의 뇌 — 검색 가능 지식 아카이브](https://github.com/11pyo/Third-Party-Brain)** — *기억*: 운영
  지식의 AI 검색 아카이브(`Third-Party-Brain` 레포; 이 대시보드도 거기 `reference-implementation/dashboard/`에 미러).
- **이 대시보드** — *워크플로우*: 진행 중 업무를 위한 동시기록 안전 보드.

함께: 쌓이는 지식 + 보이고 협업에 안전한 업무.

### 아이디어 / 로드맵
- 단일 정본: `TASKS` 배열 중복 대신 `tasks.md`를 직접 파싱.
- 왕복 동기화: 보드의 "변경분 내보내기"가 JSON diff를 뽑음 → `tasks.md`로 되적용하는 "적용" 경로 추가.
- 문의의 `ref` 앵커를 지식 아카이브로 교차 링크.
- 조직/요청자 뷰; 상태 체류시간·노후화 지표.
