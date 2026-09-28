# Changelog · 변경 이력

> Newest first. · 최신이 맨 위. Board/engine feature changes are recorded here (mirrored from the internal original this repo was anonymized from).

## 2026-09-28 (2) — 📏 Measure the pre-search before tuning it · 고치기 전에 잰다

- **Problem · 문제**: the pre-search hook injects context on every prompt, but nobody knew whether it helped. Tuning the keyword rules by feel is how the internal deployment's rules rotted before.
- 선행검색 훅이 매 질문 맥락을 붙이지만, 그게 도움이 되는지 아무도 몰랐습니다. 감으로 규칙을 고치면 예전처럼 규칙이 낡습니다.
- **Change · 개선**: `prompt_context.py` records each turn (kind, keywords, injected ids) to `hooks/logs/turns.jsonl`; a new Stop hook `stop_turn_audit.py` checks which injected ids the agent actually mentioned (reply text + tool inputs after the turn started, read from the transcript) and writes `audits.jsonl`; `hook_report.py` prints hit rate, use rate, and **keywords that keep finding nothing** — the list to extend the vocabulary with. Optional: set `ARCHIVE_PATH` and the same hook blocks a stop once when the archive changed this turn but neither the inquiry log nor `tasks.md` did ("record it, or finish if it was pure knowledge work").
- 질문마다 무엇을 붙였는지 기록하고, 턴이 끝날 때 그중 에이전트가 실제로 언급한 것을 가려 기록합니다. `hook_report.py`가 적중률·사용률·**자주 못 찾는 키워드**(사전 보강 후보)를 보여 줍니다. 선택: `ARCHIVE_PATH`를 주면 아카이브만 고치고 기록이 없는 턴에 한 번 되묻습니다.
- **Design notes · 설계 주의**: logs hold keywords that may include customer names or document numbers — keep `BOARD_HOOK_LOGDIR` outside any shared folder. Each turn is judged once (a second Stop in the same turn passes through).
- 로그 키워드에 고객명·문서번호가 섞일 수 있으니 `BOARD_HOOK_LOGDIR`은 공유 폴더 밖에 두세요. 한 턴은 한 번만 판정합니다.
- **Verified · 검증**: sample board — a card-id prompt, a reply mentioning it → use rate 1/1; internal deployment — 3 of 7 injected ids correctly detected as used (text + tool input), nudge fires once and the second Stop passes.

## 2026-09-28 — 🪝 Rules become hooks · 규칙을 훅으로

- **Problem · 문제**: every onboarding rule in this repo was a sentence the agent had to remember — "search open cards and past inquiries before answering", "re-run the index generator after a card edit", "run the sync check before you finish". Checkers existed, but nothing *ran* them. In the internal deployment a review found the project had zero hooks: every rule lived in prose that is re-read every turn, and the same slips kept recurring despite the rules.
- 이 레포의 온보딩 규칙은 전부 에이전트가 **기억해서** 지켜야 하는 문장이었습니다 — 「답하기 전에 열린 카드·과거 문의 검색」, 「카드 수정 후 인덱스 재생성」, 「끝내기 전 동기화 점검」. 점검기는 있었지만 **돌려 주는 장치**가 없었습니다. 내부 운영본을 점검해 보니 훅이 0개였고, 규칙이 있는데도 같은 실수가 반복됐습니다.
- **Change · 개선** (`hooks/`, opt-in):
  - `prompt_context.py` (**UserPromptSubmit**) — on every prompt, searches `tasks-index.md`, `inquiry-log.js` (merged by id) and, if present, a knowledge archive's `archive-structure.md`; injects the top 3 per source in ≤1,500 chars. Keywords = code-like tokens in the prompt + words that also occur in your own card titles / archive keywords. A lightweight RAG with no vector DB — at board scale, a vocabulary built from your own index is enough. Prompts with no keyword inject nothing.
  - `stop_board_sync.py` (**Stop**) — if `tasks.md` or `task-board.html` is newer than the last passing check, regenerates the index and runs `check-board-sync.py`; on drift it blocks the stop **once** and hands the report back (`stop_hook_active` prevents a loop). The trigger is file mtime, so edits made through throw-away scripts are caught too.
  - 질문마다 보드 세 곳을 먼저 찾아 상위 3건씩 1,500자 이내로 붙여 주고(벡터 DB 없는 경량 RAG, 키워드 없으면 아무것도 안 붙임), 턴이 끝날 때 카드 파일이 바뀌었으면 인덱스 재생성 + 동기화 점검을 돌려 어긋나면 한 번 막고 고치게 합니다(수정 시각으로 판정 → 스크립트 편집도 포착).
- **Design notes · 설계 주의**: hook output is re-read in every later round of the conversation, so it is capped and silent when it has nothing to say. A hook error never blocks the turn. The internal deployment also puts irreversible tool calls (transport creation/release, object deletion) behind `permissions.ask` — a per-call confirmation that complements, not replaces, asking in chat first.
- 훅 출력은 이후 모든 라운드에서 다시 읽히므로 짧게, 할 말이 없으면 침묵합니다. 훅 오류는 턴을 막지 않습니다. 내부 운영본은 되돌리기 어려운 도구 호출(전송요청 생성·릴리즈, 오브젝트 삭제)을 `permissions.ask`로 매번 확인받게 했습니다 — 대화로 먼저 승인받는 절차를 대체하지 않는 최후 관문입니다.
- **Wider lesson · 더 큰 교훈**: the fourth time here that a written rule was replaced by a tool — after the index generator, the stale-index check, and the waiting-card deadline. Checkers made drift *detectable*; hooks make the check *happen*.
- 규칙이 도구로 바뀐 네 번째 사례입니다(인덱스 생성기 · 낡은 인덱스 점검 · 대기 카드 기한 다음). 점검기는 어긋남을 **잡을 수 있게** 했고, 훅은 점검이 **실제로 돌게** 합니다.
- **Verified · 검증**: sample data — card hits for a title phrase and a card id, an inquiry hit for a ticket number (the parser also reads hand-written JS literals), no output for "ok go ahead"; stop hook passes, stays silent on the second run. Internal deployment — 7 sample prompts ~0.4 s each, all three stop paths (silent / regenerate / block then notify-only), and the hook confirmed firing in a live session.

## 2026-09-10 — 📤 Waiting cards now carry a deadline · 대기 카드에 기한을 붙인다

- **Problem · 문제**: a card sat in `waiting` for two weeks because the e-mail it was waiting on had been *drafted but never sent* — an internal stall wearing the costume of an external wait. The board said "waiting for legal", so nobody looked again.
- 어떤 카드가 2주간 「대기」에 멈춰 있었습니다. 기다리던 회신의 **메일이 작성만 되고 발송되지 않았기** 때문입니다 — 외부 회신 대기로 위장한 내부 정체였고, 보드에 「법무팀 대기」로 떠 있으니 아무도 다시 보지 않았습니다.
- **Change · 개선**: the `waiting on` row takes three more fields — `sent`, `due`, `if overdue` — and `gen-tasks-index.py` collects them into an **Awaiting reply** section that flags anything past its due date (and prints an overdue count on stdout). Both the bullet form (`- **waiting on**: …`) and a table row are parsed.
- 「waiting on」 줄에 **발송·회신기한·기한 경과 시 조치**를 함께 적으면, 생성기가 이를 모아 「Awaiting reply」 표로 올리고 기한이 지난 건을 표시합니다(stdout 에도 건수 경고).
- **Design note · 설계 주의**: `sent` defaults to **unconfirmed**, never "not sent". The agent cannot observe whether the human sent it — asserting "not sent" produces the mirror-image error: urging a re-send of something already sent. And because the index is generated at a point in time, the due date is written as *data* and **the session compares it against today's date**.
- 「발송」의 기본값은 **미확인**입니다. 사람이 직접 보내고 말하지 않을 수 있어 에이전트는 발송 여부를 관측할 수 없습니다 — 「안 보냄」으로 단정하면 **이미 보낸 것을 다시 보내라고 권하는 반대 방향 오류**가 납니다. 인덱스는 생성 시점 기준이므로 기한은 데이터로만 싣고 **판정은 세션이 오늘 날짜로** 합니다.
- **Wider lesson · 더 큰 교훈**: third time in this repo that a step left as a written rule rotted. "State what you're waiting on" was already update-rule #3 — it simply had no deadline and no checker behind it. A rule nobody re-reads is a rule that expires.
- 이 레포에서 **규칙으로만 남긴 단계가 낡은 세 번째** 사례입니다. "무엇을 기다리는지 적어라"는 이미 규칙 3번이었지만 **기한도, 점검기도 없었습니다.**
- **Verified · 검증**: parser unit cases (one ordering bug found and fixed — the "if overdue" chunk was being swallowed by the "due" branch), plus end-to-end on the sample board (`TS-001` renders "⏰ 5d overdue").

## 2026-09-01 — ⏱️ The checker now also catches a stale index · 점검기가 낡은 인덱스까지 잡는다

- **Problem · 문제**: the session-start index shipped in the previous entry came with a *rule* attached — "re-run `gen-tasks-index.py` after editing cards". A scheduled audit of the internal deployment found that rule had quietly failed: the index was 22 minutes behind its source, and the size line it advertises (`764,764 chars / 2,643 lines`) no longer matched reality. A session starting from it would have read a table of contents missing the newest work — with nothing signalling that.
- 앞선 항목에서 만든 착수 인덱스에는 "카드를 고쳤으면 생성기를 다시 돌려라"라는 **규칙**만 붙어 있었습니다. 정기 감사에서 그 규칙이 조용히 새어 나간 걸 발견했습니다 — 인덱스가 정본보다 22분 낡았고, 인덱스에 적힌 분량도 실제와 달랐습니다. 그 목차로 시작한 세션은 **최신 작업이 빠진 목차**를 읽게 되는데 아무 신호도 없었습니다.
- **Change · 개선**: `check-board-sync.py` gains `check_index_freshness()` — the gate you already run at the end of a card edit now also fails (**exit 1**) when `tasks-index.md` is missing, older than `tasks.md` (mtime, 2s slack), or advertises a size that does not match the source. Each finding carries the exact command that fixes it. Board-sync logic and output format are untouched — this is additive.
- 카드 수정 끝에 이미 돌리던 그 게이트가 **인덱스 부재·mtime 낡음·분량 불일치**도 실패로 잡습니다(종료코드 1). 각 항목에 고치는 명령을 함께 출력합니다. 기존 보드 대조 로직·출력은 그대로(추가만).
- **Implementation note · 구현 주의**: the size comparison must use *exactly* the generator's definition — lines = `split(NL)` count, chars = **sum of line lengths (newlines excluded)**. Counting raw string length instead produced a check that always failed. If you port this, copy the definition, not the intent.
- 분량 비교는 생성기와 **똑같은 정의**를 써야 합니다(줄수=개행수+1, 글자수=**개행 제외**). 전체 문자열 길이로 세면 항상 실패하는 점검이 됩니다.
- **Wider lesson · 더 큰 교훈**: this is the second time in this repo that a step left as a written rule rotted while the same step, once wrapped in a checker, stayed correct. **If a step matters and only a rule guards it, it will rot.** A related documentation audit the same day found an index table whose *count* was right (53) while a row was missing (52 rows) — count parity does not prove list parity; compare ids, not totals.
- 이 레포에서 **규칙으로만 남긴 단계는 낡고, 점검기로 감싼 단계는 살아남는** 사례가 두 번째입니다. 같은 날 문서 감사에서는 **개수(53)는 맞는데 행이 하나 빠진(52행)** 목차도 나왔습니다 — 개수 일치는 목록 일치가 아닙니다. 합계 말고 **id 전수 대조**로 볼 것.
- **Verified · 검증**: internal deployment — stale index reproduced both findings and exit 1; after regenerating, exit 0 with the pre-existing notes unchanged. This repo's sample data: 6 cards, index fresh, exit 0.

## 2026-08-25 — 🧭 Session-start index + board-sync checker · 착수 인덱스·동기화 점검기

- **Problem · 문제**: two failure modes that both stay silent. (1) `tasks.md` is the source of truth and the onboarding rule is "read it first" — but in the internal deployment this repo mirrors, it grew to ~650,000 characters / 2,250 lines, past what an AI assistant can hold in one context, so the rule became unfollowable while still being written down. (2) The same card lived in more than one hand-kept place, and cards added to the markdown but never to the board's `TASKS` array simply never rendered — repeatedly, over months. Nothing errored, so nobody noticed.
- 둘 다 **조용히** 망가지는 실패였습니다. ①`tasks.md`가 65만자/2,250줄로 자라 "착수 시 정본을 먼저 읽어라"는 규칙이 물리적으로 실행 불가능해졌는데 규칙은 그대로 남아 있었고, ②같은 카드를 여러 곳에 손수 적다 보니 정본에만 추가되고 보드 `TASKS` 배열엔 빠진 카드가 몇 달째 화면에 안 뜨고 있었습니다. 아무것도 실패하지 않으니 아무도 몰랐습니다.
- **Change · 개선**:
  - **`gen-tasks-index.py` → `tasks-index.md`** — a generated table of contents holding only the open cards plus **each card's line range** in `tasks.md`, so a session reads the index and then pulls just the card it needs (`sed -n 'A,Bp' tasks.md`). Internal result: **650k chars → ~5k (about 1/130)**. The source of truth is never split.
  - **`check-board-sync.py`** — cross-checks `tasks.md` against the `TASKS` array and **exits 1** on a card present in only one of them, or a status the card body contradicts. It deliberately **never fixes anything**: which side is true is a human call. Title-wording differences and empty AI logs are reported as notes, not failures, and "recurring" is treated as a cadence rather than a status.
  - **One field, one source** — card metadata (status/requester/due/next) now has exactly one home: the `TASKS` array. AGENTS.md rule 4 was extended to forbid adding a third hand-kept copy.
  - Both tools read either board dialect — strict JSON (as the save button writes it) or hand-written JS object literals — and match the `const TASKS = [` declaration by pattern, because a plain text search also hits prose inside a card's AI log that mentions the array.
- `gen-tasks-index.py` → `tasks-index.md`: 살아있는 카드 + **카드별 라인 범위**만 담은 목차를 자동 생성(정본은 안 쪼갬, 내부 실측 65만자→약 5천자 ≒ 1/130). `check-board-sync.py`: 정본↔배열을 교차 대조해 한쪽에만 있는 카드·모순된 상태를 찾고 **종료코드 1**(자동수정 안 함 — 무엇이 사실인지는 사람 판단). 제목 문구 차이·빈 AI로그는 참고로만, '정기'는 상태가 아니라 반복성으로 취급. 카드 메타의 출처를 `TASKS` 배열 하나로 고정하고, 세 번째 수기 사본 금지를 AGENTS.md 규칙 4에 명시.
- **Verified · 검증**: on this repo's sample data both run clean (6 cards, exit 0); injecting three kinds of drift — a card only in `tasks.md`, a card only in the array, and a contradicting status — reproduces all three findings and exit 1.

## 2026-06-19 — 🧹 v2 demo low-severity cleanups · 마이너 보강

- **Polish · 보강**: preserve task-card open/expanded state across re-renders (an expanded AI log stays open *and* filled after a status change, not just visually open); HTML-escape task-card fields too (not only inquiries); the "view past history" button now tolerates a partial archive load and retries only the missing file (no duplicate pushes); `append()` no longer risks a double-write if locking throws after the write succeeded. All re-verified.
- 재렌더(상태 변경 등) 시 태스크 카드 펼침·AI로그 펼침 상태 보존(시각뿐 아니라 본문까지 채워진 채 유지); 태스크 카드 필드도 HTML 이스케이프; '과거 보기' 버튼이 부분 로드를 견디고 실패분만 재시도(중복 push 없음); `append()` 락 예외 시 이중 쓰기 방지. 전부 재검증.

## 2026-06-18 — 🔒 v2 demo hardening: fix data-loss parser, ordering, XSS (post-review) · 리뷰 후 보강

- **Fix · 수정**: an adversarial multi-agent review found a **data-loss bug** — `log-inquiry.py`'s regex push-parser dropped any record whose value contained `});`, so `--compact`/`--archive-before` (which rewrite the file) silently lost data. Replaced with a line-based parser that **aborts (fatal) on any unparseable push line** instead of dropping it; maintenance ops now take the same lock as `append()` and write atomically (`tmp`→`os.replace`); `--archive-before` is append-only to archives (no lossy re-read), buckets by each item's own half-year, validates the date, and skips id-less/undated rows. Board: the inquiry list now sorts by real date (id tiebreak) so "view past history" stays newest-first (was a `.reverse()` regression); inquiry text is HTML-escaped and `ref` is scheme-checked (blocks `javascript:`); removed a redundant double-fold. All re-verified.
- 적대적 멀티에이전트 리뷰가 **데이터 손실 버그** 적발 — 정규식 파서가 값에 `});` 포함 레코드를 삭제해 `--compact`/`--archive-before` 재작성 시 침묵 손실. 라인 기반 파서로 교체(파싱 실패 시 **치명 종료**, 침묵 삭제 금지)·유지보수 op를 `append()`와 동일 락+원자적 쓰기·아카이브 append-only(손실 재적용 제거)·항목 날짜 반기 버킷·날짜 검증·id없음/날짜없음 스킵. 보드: 문의 목록을 실제 날짜 정렬로(‘과거 보기’ 최신순 유지, `.reverse()` 회귀 수정)·HTML 이스케이프+ref 스킴 검증(`javascript:` 차단)·이중 fold 제거. 전부 재검증.

## 2026-06-18 — 🧪 v2 scaling demo: verified reference implementation · v2 데모 검증 구현

- **Change · 개선**: `demo-v2/` implements and **verifies** the SCALING.md stages on bulk fictional data (315 inquiries / 891 pushes): **Stage A** lazy-render ailog (0 → 454 chars on open), **Stage B** active/archive split (board loads 45 active → "view past history" merges to 315), helper **`--compact`** (126 → 45 pushes) and **`--archive-before`** (moves done items out of active). v1 would load ~129 KB every time; v2 loads 18.4 KB active. Includes `gen-demo-data.py` (seeded, reproducible) and a README.
- `demo-v2/`에 SCALING.md 단계들을 대량 허구 데이터(315건 / 891 push)로 구현·**검증**: **Stage A**(ailog 지연 렌더, 펼침 시 0→454자), **Stage B**(활성/아카이브 분리 — 보드 45건 → '과거 보기'로 315건 병합), 헬퍼 **`--compact`**(126→45)·**`--archive-before`**. v1=매번 ~129KB, v2=활성 18.4KB. 재현 생성기 `gen-demo-data.py`·README 포함.

## 2026-06-18 — 📈 Scaling guide: data-growth upgrade blueprint · 데이터 누적 업그레이드 설계도

- **Problem · 문제**: as the inquiry log and card AI-logs accumulate, this single-file board can get heavy. Naive optimization (hiding/splitting past data) risks cutting an AI assistant off from past context — fatal when work is fully AI-delegated.
- **Change · 개선**: added `docs/SCALING.md` (+ `docs/SCALING.en.md`) — a staged upgrade blueprint governed by one principle, **"Render local, search global"**: hide the past only in the human view, keep the AI's data access whole. Includes thresholds (do-nothing → lazy-render ailog → archive completed → compaction → virtualized Done column), exact change points with code snippets, and a guardrail checklist so history search stays global and metrics stay cumulative.
- 문의 로그·카드 AI로그가 쌓이면 단일 파일 보드가 무거워질 수 있는데, 섣부른 최적화는 AI의 과거 맥락 접근을 끊을 수 있습니다(전적 AI 위임 시 치명적). `docs/SCALING.md`(+영문) 추가 — **"표시는 분리, 검색은 통합"** 원칙의 단계별 업그레이드 설계도. 임계점·정확한 변경점·코드 스니펫·가드레일 체크리스트(과거 검색은 전체 대상, 지표는 누적 합산) 포함.

## 2026-06-12 — 🤖 AI context log: two-layer cards · 카드 2층 구조

- **Problem · 문제**: long-running dev cards accumulate a time-series of fixes, insights, and AI-committed policies. You can't shorten it — the AI needs the full, verbatim context to stay accurate — but humans drown in it.
- **Change · 개선**: each card is now **body + collapsed log**:
  - **Body** (`detail`) — curated, current-state, for humans. Read this and stop.
  - **🤖 AI context log** (`ailog`) — a collapsible section below the body holding the time-series work log, lessons, and AI policies. **Humans can skip it; AI assistants are instructed (AGENTS.md) to always read it.**
  - Works in edit mode like any other field, and 💾 save writes it to the file. Cards without `ailog` look exactly as before.
- 카드가 **본문(사람용 — 잘 정리된 현재 상태) + 접힘 🤖 AI 참조 로그(AI용 — 시계열 작업로그·교훈·AI 방침)** 2층 구조가 됐습니다. **내용을 줄이지 않고도(AI 문맥 전부 보존) 사람 눈에는 깔끔한 본문만** 보입니다. AI는 AGENTS.md 규칙에 따라 접힌 로그까지 자동 정독합니다.

## 2026-06-10 — 💾 save reliability · 저장 신뢰성

- Server-less ✏️ edit + **💾 save-to-file** (File System Access API; non-Chromium falls back to download).
- Remembered file handle (IndexedDB) with an **app-unique key + filename validation** — fixes a real incident where two tools sharing one key overwrote each other's files on `file://`.
- **Save-stamp mismatch banner** ("your last save didn't land in this file"), no silent cancel, round-trip size verification, save button disabled at 0 changes.
- ✏️편집·💾파일 저장(원클릭), 파일 위치 기억(앱 고유 키+파일명 검증), 저장 도장 대조 경고 배너, 취소·실패 무음 금지.

## 2026-06-09 — initial public release · 최초 공개

- Kanban task board + append-only inquiry log (id-merge concurrency safety), `log-inquiry.py` helper CLI, bilingual docs (KO/EN), AI onboarding via `AGENTS.md`.
- 칸반 태스크 보드 + 추가전용(append-only) 문의 로그(id 병합 동시성 안전), 헬퍼 CLI, 한/영 문서, AI 자동 온보딩.
