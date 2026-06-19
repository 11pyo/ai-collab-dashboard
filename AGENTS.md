# AGENTS.md — orientation for AI agents · AI 에이전트 온보딩

> If you're an AI assistant working in this repo, read this first.
> 이 레포에서 작업하는 AI라면 이 파일을 먼저 읽으세요.

## What this is · 무엇인가
**EN** — A dependency-free **operations dashboard**: a kanban board for tasks + a 4-column board
for inquiries. Its defining idea is **concurrency safety without a backend** — multiple people or
AI sessions can record updates at once without overwriting each other. The kanban board form is
inspired by the **Toyota Production System's kanban**; the concurrency design (append-only + id
merge) is an event-sourcing-style idea of its own. See `README.md` and `docs/VISION.md`.

**KO** — 서버·DB 없이 도는 **운영 대시보드**: 태스크 칸반 + 문의 4열 보드. 핵심은 **무백엔드 동시기록
안전** — 여러 사람·여러 AI 세션이 동시에 기록해도 서로 덮어쓰지 않습니다. 칸반 보드 형태는 **토요타
생산방식의 칸반**에서 영감, 동시성 설계(추가전용+id병합)는 이벤트 소싱 계열의 별개 아이디어입니다.
자세히는 `README.md`·`docs/VISION.md`.

## Architecture · 구조 (한 문단)
**EN** — `inquiry-log.js` is an **append-only push log**. The board **folds it by id** (`Object.assign`
in order), so a later `{id, status:"done"}` updates only those fields. Nothing is rewritten, so two
writers can't clobber each other. `log-inquiry.py` appends behind a short OS file-lock.

**KO** — `inquiry-log.js`는 **추가전용 푸시로그**입니다. 보드가 **id로 접어**(`Object.assign` 순서대로)
뒤 줄이 해당 필드만 갱신합니다. 아무것도 다시 쓰지 않으니 두 writer가 충돌하지 않습니다.
`log-inquiry.py`가 짧은 OS 파일락 뒤에서 추가합니다.

## File map · 파일 지도
| File | Role · 역할 | Edit? · 수정 |
|------|------|------|
| `task-board.html` | UI: task kanban + inquiry board · 화면 | yes |
| `tasks.md` | source of truth for tasks · 태스크 정본 | yes (keep in sync with the `TASKS` array · `TASKS` 배열과 동기화) |
| `inquiry-log.js` | append-only inquiry log · 추가전용 문의로그 | **no hand-edit · 직접편집 금지 → `log-inquiry.py`** |
| `log-inquiry.py` | append/transition/close CLI · 문의 CLI | yes (preserve append-only+id-merge · 원리 유지) |
| `docs/` | vision · git notes · 비전·git 노트 | yes |

## Rules · 규칙 (절대)
1. **Public repo → fictional sample data only.** No real names/customers/codes/secrets. · 공개 레포 → 가짜 샘플만. 실명·고객·코드·자격증명 금지.
2. **Bilingual docs (KO + EN).** · 문서 한/영 병기.
3. **Never hand-edit `inquiry-log.js`** — append via `log-inquiry.py`. · 문의로그 직접편집 금지.
4. **Keep `tasks.md` and the `TASKS` array in sync.** · 정본과 배열 동기화.
5. Status set is fixed: `received → in-progress → waiting → done`; `waiting` must say what it waits on. · 상태 4종 고정, 대기는 사유 명시.
6. **Card form:** keep the `.inq-sum`/`.inq-detail`/`.inq-cy` CSS and the `#inq-board` toggle delegation together (see README "Card form structure"). · 폼 수정 시 CSS+위임 함께 유지.
7. **Commits: 11pyo only — do NOT add a `Co-Authored-By` trailer.** · 커밋은 11pyo 단독, Co-Authored-By 금지.

## When asked to "set this up" · "셋업해줘" 하면 — offer a choice, don't just open the file
**Don't just pop open `task-board.html`.** Offer two paths:
- **Ⓐ Demo** → open `task-board.html` (ships with sample tasks + inquiries) and walk the user through it.
- **Ⓑ Theirs** → a ~1-minute setup: ask for the user's **task list, status set, and classification**,
  then fill `tasks.md` + the `TASKS` array; start a fresh `inquiry-log.js` (append via `log-inquiry.py`).

**그냥 파일만 띄우지 말 것** — 선택지 제시: **Ⓐ 데모**(`task-board.html` 열고 샘플로 안내) / **Ⓑ 내 걸**(팀 태스크·상태·분류를 묻고 `tasks.md`+`TASKS` 채우기, 문의는 `log-inquiry.py`로 새로 시작).

**Standalone · 단독 동작:** this dashboard does **NOT** need the archive (`Third-Party-Brain`) — it runs fully on its own. The inquiry `ref` field can point to an archive anchor, but it's optional; with no archive those links are simply inert. · 아카이브 **없이 단독 완전 동작**. `ref`는 선택(아카이브 앵커 연결용), 아카이브가 없으면 그 링크는 비활성일 뿐.

**✏️ Users can self-edit · 직접 수정 가능:** `task-board.html` has a built-in **Edit** button (server-less; edits the file via the File System Access API, else download). For small task tweaks/adds, point the user to it — no need to route every little edit through the AI. The inquiry log is still append-only via `log-inquiry.py`. · 카드 간단 수정·추가는 페이지의 **✏️ 편집** 버튼으로 사용자가 직접(클로드 불필요). 문의 로그는 여전히 `log-inquiry.py`로만.

**🤖 Two-layer cards — you MUST read the collapsed AI log · 카드 2층 구조:** each task card = a **curated body** (`detail`, for humans) + a collapsed **🤖 AI context log** (`ailog` — time-series work log, lessons, policies the AI committed to). **When working on a card, AI assistants MUST read both** — the log holds settled decisions and pitfalls; skipping it causes re-asking and re-inventing. Humans only need the body. Updating a card: **append** new events to `ailog` (never compress or delete — the AI needs verbatim context), and rewrite `detail`/`next` to the clean current state for humans. · 카드 = **본문**(`detail`·사람용) + 접힘 **`ailog`**(시계열 로그·교훈·AI 방침). **AI는 카드 작업 시 둘 다 반드시 정독**(로그에 기확정 사항·함정 — 안 읽으면 재질문·재발명). 사람은 본문까지만. 갱신 = `ailog`에 시계열 **append(축약·삭제 금지)** + 본문·next는 현재 상태로 재정리.

## How to run / test · 실행·테스트
```bash
start task-board.html         # Windows (or double-click)
python log-inquiry.py --new --type simple --q "test" --by alice
python log-inquiry.py --done --id <printed-id> --a "resolved"
# refresh task-board.html · 새로고침
```
Verify: 9 sample push lines fold to 5 inquiries; inquiry cards expand on header click; no console errors.
검증: 푸시 9줄 → 문의 5건으로 접힘, 헤더 클릭 시 펼침, 콘솔 에러 0.

## Notes · 비고
- **Scaling/perf · 확장성**: when data grows large, follow `docs/SCALING.md` — a staged upgrade blueprint under **"render local, search global"** (hide the past only in the human view, keep the AI's access to context whole). · 데이터가 커지면 `docs/SCALING.md`의 단계별 업그레이드를 따른다(**표시는 분리, 검색은 통합** — 사람 화면만 과거를 숨기고 AI의 맥락 접근은 온전히).
- This is part of a pair with the knowledge archive **`11pyo/Third-Party-Brain`** (this dashboard is
  mirrored there under `reference-implementation/dashboard/`). · 지식 아카이브 `11pyo/Third-Party-Brain`과
  한 쌍(거기 `reference-implementation/dashboard/`에 미러본).
- `*.local.md` is git-ignored private notes — read for intent, never copy into committed files. ·
  `*.local.md`는 비공개(gitignore) — 의도 파악용, 커밋 파일에 옮기지 말 것.
