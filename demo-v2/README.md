# demo-v2 — Scaling demo (v2, verified) · 확장성 데모 (검증됨)

**EN** — A **working, verified** implementation of the v2 optimizations described in [`../docs/SCALING.md`](../docs/SCALING.md), running on **bulk fictional demo data** (315 inquiries / 891 pushes) so the difference is visible at scale.

**KO** — [`../docs/SCALING.md`](../docs/SCALING.md)의 v2 최적화를 **대량 허구 데모 데이터(315건 / 891 push)** 위에서 **실제 구현·검증**한 폴더. 규모가 커졌을 때의 차이를 눈으로 볼 수 있습니다.

## Why · 왜
**EN** — v1 loads **all 891 pushes (~129 KB) every time**. v2 loads only the active recent file (**45 inquiries / 18.4 KB**); the past loads on demand. The human view stays light; the AI's access stays whole.

**KO** — v1은 **매번 891 push(~129KB) 전부**를 로드합니다. v2는 활성 최근 파일(**45건 / 18.4KB**)만 로드하고 과거는 필요할 때 불러옵니다. 사람 화면은 가볍고, AI의 접근은 온전합니다.

## Verified · 검증 결과
| Stage | What · 내용 | Verified · 검증 |
|---|---|---|
| A | Lazy-render ailog (inject only when a card's AI log opens) · ailog 지연 렌더 | 0 → 454 chars on open |
| B | Active/archive split · 활성/아카이브 분리 | board loads 45 → "view past history" merges to 315 |
| helper | `--compact` · 로그 컴팩션 | 126 pushes → 45 (one per id) |
| helper | `--archive-before YYYY-MM-DD` · 완료 항목 분리 | moved done items out of active |

## Files · 파일
- `task-board.html` — v2 board (Stage A + B) · v2 보드
- `inquiry-log.js` — **ACTIVE** (recent) · 활성(최근)
- `inquiry-log-archive-2026H1.js` / `-2025H2.js` — **ARCHIVE**, load on demand · 아카이브(온디맨드)
- `log-inquiry.py` — helper with `--compact` / `--archive-before` · v2 헬퍼
- `gen-demo-data.py` — regenerates the bulk demo data (seeded, reproducible) · 데모 재생성기
- `tasks.md` — sample tasks · 샘플 태스크

## Run · 실행
```bash
python gen-demo-data.py      # (re)generate the bulk demo data · 데모 데이터 (재)생성
start task-board.html        # or serve the folder and open it · 폴더를 서빙해 열기
```
**EN** — Click a task card's "🤖 AI context log" to see lazy injection; click "View past history" to merge the archives into the board.

**KO** — 태스크 카드의 "🤖 AI context log"를 펼치면 지연 주입이, "View past history"를 누르면 아카이브가 보드에 병합되는 것이 보입니다.

## Guardrail · 가드레일 (why AI context isn't broken · AI 맥락이 안 끊기는 이유)
**EN** — "Render local, search global": the browser loads active only, but history search (Grep over `inquiry-log*.js`) and metrics cover **everything**. Completion writes always go to the active file via `log-inquiry.py`. See [`../docs/SCALING.md`](../docs/SCALING.md).

**KO** — "표시는 분리, 검색은 통합": 브라우저는 활성만 로드하지만, 이력 검색(`inquiry-log*.js` 전체 Grep)·지표는 **전부**를 포괄합니다. 완료 기록은 항상 `log-inquiry.py`로 활성 파일에 들어갑니다. 상세는 [`../docs/SCALING.md`](../docs/SCALING.md).
