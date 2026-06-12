# Changelog · 변경 이력

> Newest first. · 최신이 맨 위. Board/engine feature changes are recorded here (mirrored from the internal original this repo was anonymized from).

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
