# Changelog · 변경 이력

> Newest first. · 최신이 맨 위. Board/engine feature changes are recorded here (mirrored from the internal original this repo was anonymized from).

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
