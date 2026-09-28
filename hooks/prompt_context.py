# -*- coding: utf-8 -*-
"""UserPromptSubmit hook — search the board before the agent answers.
UserPromptSubmit 훅 — 에이전트가 답하기 전에 보드를 먼저 검색해 붙여 준다.

The onboarding rule "search open cards and past inquiries before answering" used to be
a sentence in AGENTS.md. Here a hook does it on every prompt and injects a short block
(top 3 per source, <= 1,500 chars) into the agent's context.

Sources (each optional — missing files are skipped):
  - tasks-index.md    open cards + their line ranges in tasks.md (gen-tasks-index.py)
  - inquiry-log.js    inquiry history, merged by id (log-inquiry.py)
  - archive-structure.md  table rows `| n | `id` | title | keywords |` of a knowledge
                      archive (see 11pyo/Third-Party-Brain), if you keep one next to the board

Keywords = code-like tokens in the prompt (card IDs, ticket numbers, transaction codes,
host names) + words that also appear in the card titles / archive keywords.
No vector DB: at this scale a vocabulary built from your own index is enough.
Any error exits silently — a hook must never block the prompt.
"""
import json
import os
import re
import sys

ROOT = os.environ.get("BOARD_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "tasks-index.md")
INQ = os.path.join(ROOT, "inquiry-log.js")
STRUCT = os.path.join(ROOT, "archive-structure.md")

TOP_N = 3
MAX_TOKENS = 25
MAX_CHARS = 1500
STOP = {
    # English filler
    "this", "that", "with", "from", "what", "when", "which", "have", "should", "would", "could",
    "about", "there", "their", "into", "then", "than", "them", "they", "your", "please", "thanks",
    "again", "still", "just", "also", "some", "make", "does", "done", "need", "want", "check",
    "status", "update", "card", "cards", "board", "task", "tasks", "item", "items", "report",
    # Korean filler (2+ chars)
    "변경", "조회", "처리", "관리", "요청", "문의", "확인", "운영", "개발", "화면", "오류", "방법",
    "추가", "수정", "삭제", "등록", "작업", "업무", "정리", "내용", "결과", "상태", "담당", "진행",
    "완료", "대기", "접수", "이번", "그대로", "아니면", "그리고", "시스템", "프로그램", "담당자",
}
UPPER_STOP = {"HTTP", "HTTPS", "HTML", "JSON", "TODO", "NULL", "TRUE", "FALSE"}


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def squash(s):
    return re.sub(r"\s+", "", s).lower()


def code_tokens(prompt):
    out = []
    for p in (r"\b[A-Z]{2,5}-[0-9][0-9-]*\b",                # card / inquiry ids
              r"\b[A-Za-z][A-Za-z0-9_]*[0-9][A-Za-z0-9_]*\b",  # codes with a digit
              r"\b[A-Z][A-Z_]{3,}\b"):                        # ALLCAPS identifiers
        for t in re.findall(p, prompt):
            if len(t) < 3 or t.upper() in UPPER_STOP or re.fullmatch(r"[0-9-]+", t):
                continue
            if re.fullmatch(r"[0-9a-f]{12,}", t):  # agent/session ids, hashes
                continue
            if t.lower() not in (x.lower() for x in out):
                out.append(t)
    return out[:MAX_TOKENS]


def index_rows(text):
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*\*\*([A-Z]{2,5}-\d+)\*\*\s*\|(.*)$", line)
        if m:
            cells = [c.strip() for c in m.group(2).split("|")]
            rows.append({"id": m.group(1), "title": cells[0] if cells else "",
                         "status": cells[1] if len(cells) > 1 else "",
                         "lines": cells[-2] if len(cells) > 2 else "", "text": line})
    return rows


def struct_rows(text):
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", line)
        if m:
            rows.append({"id": m.group(1), "title": m.group(2), "kw": m.group(3)})
    return rows


def inquiry_rows(text):
    merged = {}
    for line in text.splitlines():
        m = re.match(r"^window\.INQUIRY_LOG\.push\((\{.*\})\);\s*$", line)
        if not m:
            continue
        body = m.group(1)
        try:
            d = json.loads(body)  # the helper writes strict JSON
        except ValueError:
            try:  # hand-written JS literal: quote bare keys ({id:"…"} → {"id":"…"})
                d = json.loads(re.sub(r'([{,]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', body))
            except ValueError:
                continue
        if "id" in d:
            merged.setdefault(d["id"], {}).update({k: v for k, v in d.items() if v != ""})
    return list(merged.values())


def vocabulary(irows, srows):
    vocab = set()
    texts = [r["title"] for r in irows] + [r["title"] + " , " + r["kw"] for r in srows]
    for t in texts:
        for w in re.split(r"[\s,，·/()—:;|`*#'\"]+", t):
            w = w.strip(".-")
            if w.lower() in STOP:
                continue
            if re.search(r"[가-힣]", w) and len(w) >= 2:
                vocab.add(w)
            elif re.fullmatch(r"[A-Za-z][A-Za-z-]{3,}", w):
                vocab.add(w.lower())
    return vocab


def matched_words(prompt, vocab):
    ps, pl = squash(prompt), prompt.lower()
    hits = []
    for w in vocab:
        if re.search(r"[가-힣]", w):
            if squash(w) in ps:
                hits.append(w)
        elif re.search(r"\b" + re.escape(w) + r"\b", pl):
            hits.append(w)
    hits.sort(key=len, reverse=True)
    kept = []  # a longer term absorbs the shorter one it contains
    for w in hits:
        if not any(squash(w) in squash(k) for k in kept):
            kept.append(w)
    return kept[:MAX_TOKENS]


def rank(rows, key, codes, words):
    scored = []
    for r in rows:
        text = key(r)
        low, sq = text.lower(), squash(text)
        s = 2 * sum(1 for t in codes if t.lower() in low) + sum(1 for w in words if squash(w) in sq)
        if s >= 2:
            scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for _, r in scored:  # the index lists some cards in more than one table
        if r.get("id") in seen:
            continue
        seen.add(r.get("id"))
        out.append(r)
        if len(out) >= TOP_N:
            break
    return out


def clip(s, n):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    try:
        prompt = json.loads(raw).get("prompt", "")
    except ValueError:
        return
    if len(prompt.strip()) < 6 or prompt.lstrip().startswith("/"):
        return
    if "<agent-message" in prompt or "[Subagent hand-back]" in prompt:
        return  # a subagent's report, not a new question — the searching already happened

    irows, qrows, srows = index_rows(read(IDX)), inquiry_rows(read(INQ)), struct_rows(read(STRUCT))
    codes = code_tokens(prompt)
    words = matched_words(prompt, vocabulary(irows, srows))
    if not codes and not words:
        return  # nothing to search on → inject nothing (zero context cost)

    cards = rank(irows, lambda r: r["text"], codes, words)
    arts = rank(srows, lambda r: r["id"] + " " + r["title"] + " " + r["kw"], codes, words)
    inqs = rank(qrows, lambda r: " ".join(str(r.get(k, "")) for k in ("q", "a", "req")), codes, words)

    out = ["[board pre-search · hook] keywords: " + clip(", ".join(codes + words), 200)]
    if not (cards or arts or inqs):
        out.append("no match in cards / archive / past inquiries — search directly if needed")
    for r in cards:
        out.append("■ card {} — {} ({}) · tasks.md {}".format(r["id"], clip(r["title"], 70),
                                                         clip(r["status"], 12), clip(r["lines"], 20)))
    for r in arts:
        out.append("■ archive #{} — {}".format(r["id"], clip(r["title"], 90)))
    for r in inqs:
        out.append("■ inquiry {} ({} · {}) {} → {}".format(r.get("id"), r.get("date", ""), r.get("status", ""),
                                                         clip(r.get("q", ""), 80), clip(r.get("a", ""), 70) or "(no answer)"))
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                             "additionalContext": "\n".join(out)[:MAX_CHARS]}}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
