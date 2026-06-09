# Git workflow & repo setup · Git 워크플로우·설정

> A practical reference for working with this repo (for you and for AI assistants).
> 이 레포 작업용 실무 레퍼런스(사람·AI 공용).

---

## Identity · 커밋 신원
**EN** — This is a **public** repo. To avoid leaking a work email, it commits under a GitHub no-reply
identity, set **locally** for this repo only:
**KO** — **공개** 레포라 회사 이메일 노출을 막기 위해, **이 레포에만** 로컬로 GitHub no-reply 신원을 씁니다:
```bash
git config user.name  "11pyo"
git config user.email "90027796+11pyo@users.noreply.github.com"
```
Your global git identity is untouched. · 전역 git 신원은 건드리지 않습니다. (`git config user.email`로 확인)

> ⚠️ **Commits are 11pyo only — do NOT add a `Co-Authored-By` trailer.** (Removing the "claude"
> contributor was an explicit request.) · **커밋은 11pyo 단독 — `Co-Authored-By` 트레일러 넣지 말 것**
> (contributor에서 'claude' 제거는 명시적 요청이었음).

## Remote · 원격
```bash
git remote add origin https://github.com/11pyo/ai-collab-dashboard.git
git branch -M main
git push -u origin main      # 이후엔 git push
```

## Everyday flow · 일상 흐름
```bash
git status                 # what changed · 무엇이 바뀌었나
git add -A                 # stage (respects .gitignore) · 스테이징
git commit -m "message"    # commit · 커밋
git push                   # publish · 푸시
git pull                   # get remote changes · 원격 변경 받기
```

## Commit message style · 커밋 메시지
**EN** — Short imperative subject + optional body explaining *why*. No co-author trailer.
**KO** — 짧은 명령형 제목 + 필요 시 *왜*를 설명하는 본문. 공동저자 트레일러 없음.
```
feat(dashboard): add round-trip sync from the board to tasks.md

The Export button emitted a JSON diff but there was no way to apply it.
This wires "Apply" to rewrite the matching task statuses in tasks.md.
```

## What is NOT committed (`.gitignore`) · 커밋 제외 항목
| Pattern · 패턴 | Why · 이유 |
|---------|-----|
| `inquiry-log.js.lock` | runtime lock from `log-inquiry.py` · 런타임 락 |
| `__pycache__/`, `*.pyc` | Python build artifacts · 파이썬 캐시 |
| `.omc/`, `.claude/`, `.mcp.json` | local AI-tooling state (machine paths/secrets) · 로컬 AI 도구 상태 |
| `NOTES.local.md`, `*.local.md` | **private** vision/idea notes — never public · 비공개 메모 |
| `.vscode/`, `.idea/`, `.DS_Store` | editor/OS noise · 편집기·OS 잡파일 |

> **Golden rule · 황금률:** public repo ships **fictional sample data only**. Before committing,
> ensure no real names/customers/codes/secrets slipped in (`git diff --cached`). · 공개 레포는 **가짜
> 샘플만**. 커밋 전 실명·고객·코드·자격증명 혼입 점검(`git diff --cached`).

## Branching (optional) · 브랜치 (선택)
```bash
git checkout -b feature/round-trip-sync
git push -u origin feature/round-trip-sync
gh pr create --fill          # needs gh authenticated · gh 인증 필요
```

## Handy `gh` commands · 유용한 gh 명령
```bash
gh repo view --web           # open in browser · 브라우저로 열기
gh auth status               # check login · 로그인 확인
```

## Auth notes (this machine) · 인증 메모 (이 PC)
**EN** — Auth used a fine-grained PAT via the `GH_TOKEN` env var (PowerShell stdin piping corrupted
the token). Pushes used a Basic auth header — `http.extraheader=AUTHORIZATION: basic <base64(x-access-token:TOKEN)>`
— so the token is never written to `.git/config`.
**KO** — 인증은 fine-grained PAT를 `GH_TOKEN` 환경변수로 사용(파워셸 stdin 파이프가 토큰을 깨뜨림). 푸시는
Basic 헤더(`http.extraheader=AUTHORIZATION: basic <base64(x-access-token:TOKEN)>`)로 — 토큰이 `.git/config`에
저장되지 않습니다.
