# -*- coding: utf-8 -*-
"""
check-board-sync.py — cross-check `tasks.md` against the board's `TASKS` array.

Why this exists · 왜 필요한가
    A task lives in two places: the card body in `tasks.md` (the narrative source of truth)
    and an entry in `const TASKS = [...]` inside `task-board.html` (the structured metadata
    the board renders). Rule 4 in AGENTS.md says keep them in sync — and rules get forgotten.
    In the internal deployment this repo was anonymized from, several cards were added to the
    markdown but never to the array, so they simply never appeared on the board, repeatedly,
    across months. Nobody noticed because nothing failed.

    This turns that silent drift into a loud failure: it exits 1 when the two disagree.
    It does **not** fix anything — which side is true is a human judgement.

    정본(`tasks.md` 카드 본문)과 보드 `TASKS` 배열이 어긋나도 아무도 실패하지 않아
    조용히 누락된다. 이 스크립트는 그 어긋남을 종료코드 1로 드러낸다(고치지는 않는다).

What counts as a real problem · 실패로 치는 것
    - a card in one place and not the other (either direction)
    - a status the card body states that contradicts the board
  Title wording differences are reported as notes, not failures: board titles routinely carry
  an extra qualifier. "Recurring" is treated as a cadence, not a status, so a recurring card
  whose board entry says "waiting" is fine.

Usage · 사용
    python check-board-sync.py     # exit 0 = in sync, 1 = fix something
    Run it at the end of any task-editing session.
"""
import difflib
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TASKS_MD = os.path.join(BASE, "tasks.md")
BOARD = os.path.join(BASE, "task-board.html")

ID_PREFIXES = "DEV|OPS|TS|ADM"
CARD_RE = re.compile(r"^#{1,6}\s+((?:" + ID_PREFIXES + r")-\d{3})\b\s*[—–-]?\s*(.*)$")
# status may be a bullet ("- **status**: done") or a table row ("| status | done |")
STATUS_BULLET_RE = re.compile(r"^\s*[-*]\s*\**\s*(?:status|상태)\s*\**\s*[:：]\s*(.+)$", re.I)
STATUS_ROW_RE = re.compile(r"^\|\s*\**\s*(?:status|상태)\s*\**\s*\|(.+?)\|", re.I)
DECL_RE = re.compile(r"const\s+TASKS\s*=\s*\[")
OBJ_RE = re.compile(r"\{\s*[\"']?id[\"']?\s*:")
BACKSLASH = chr(92)
NL = chr(10)
VAL_TMPL = r'[\"\']?{name}[\"\']?\s*:\s*"((?:[^"{bs}]|{bs}.)*)"'

TITLE_SIMILARITY_FLOOR = 0.7


def norm_status(raw):
    c = re.sub(r"[*`~✅🔵⏸️📥🔁]", "", raw or "").strip().lower()
    if any(k in c for k in ("recurring", "정기", "주례", "월례", "연례")):
        return "recurring"
    if any(k in c for k in ("cancelled", "canceled", "dropped", "취소", "철회")):
        return "dropped"
    if "in-progress" in c or "in progress" in c or "진행중" in c:
        return "in-progress"
    if "received" in c or "접수" in c:
        return "received"
    if "waiting" in c or "대기" in c:
        return "waiting"
    if any(k in c for k in ("done", "closed", "완료", "종결")):
        return "done"
    return "unknown"


def norm_title(t):
    """Keep letters/digits/Hangul only — headings carry class icons the board title lacks."""
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", t or "").lower()


def slice_array(text, open_at):
    depth, i, n = 0, open_at, len(text)
    in_str = esc = False
    quote = ""
    while i < n:
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == BACKSLASH:
                esc = True
            elif ch == quote:
                in_str = False
        elif ch in "\"'":
            in_str, quote = True, ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[open_at:i + 1]
        i += 1
    return None


def js_field(chunk, name):
    m = re.search(VAL_TMPL.format(name=name, bs=BACKSLASH + BACKSLASH), chunk)
    if not m:
        return ""
    try:
        return json.loads('"' + m.group(1) + '"')
    except ValueError:
        return m.group(1)


def load_cards():
    lines = io.open(TASKS_MD, encoding="utf-8").read().split(NL)
    starts = []
    for i, line in enumerate(lines, start=1):
        m = CARD_RE.match(line)
        if m:
            starts.append((m.group(1), m.group(2).strip(), i))
    out = {}
    for idx, (cid, title, start) in enumerate(starts):
        end = starts[idx + 1][2] - 1 if idx + 1 < len(starts) else len(lines)
        status = None
        for line in lines[start:end]:
            m = STATUS_BULLET_RE.match(line) or STATUS_ROW_RE.match(line)
            if m:
                status = norm_status(m.group(1))
                break
        out[cid] = {"title": title, "line": start, "status": status}
    return out


def load_board():
    b = io.open(BOARD, encoding="utf-8").read()
    # NB: find("const TASKS") also hits prose inside a card's ailog mentioning the array.
    m = DECL_RE.search(b)
    if not m:
        sys.exit("`const TASKS = [` not found in task-board.html — check the file.")
    raw = slice_array(b, b.index("[", m.start()))
    out = {}
    if raw:
        try:
            for t in json.loads(raw):
                if t.get("id"):
                    out[t["id"]] = {"title": t.get("title") or "",
                                    "status": norm_status(t.get("status")),
                                    "ailog_len": len(t.get("ailog") or "")}
            return out
        except ValueError:
            pass  # hand-written JS object literals: fall through to the scan below
    arr = b[m.start():]
    starts = [mm.start() for mm in OBJ_RE.finditer(arr)]
    for i, s0 in enumerate(starts):
        s1 = starts[i + 1] if i + 1 < len(starts) else len(arr)
        chunk = arr[s0:s1]
        cid = js_field(chunk, "id")
        if cid:
            out[cid] = {"title": js_field(chunk, "title"),
                        "status": norm_status(js_field(chunk, "status")),
                        "ailog_len": len(js_field(chunk, "ailog"))}
    return out


def main():
    cards = load_cards()
    board = load_board()
    problems, notes = [], []

    print("tasks.md cards: {} · board TASKS: {}".format(len(cards), len(board)))
    print("-" * 66)

    for cid in sorted(set(cards) - set(board)):
        problems.append("[not on board] {} — in tasks.md (L{}) but missing from the TASKS array; "
                        "it will not render".format(cid, cards[cid]["line"]))
    for cid in sorted(set(board) - set(cards)):
        problems.append("[not in tasks.md] {} — in the TASKS array but no card body in the "
                        "source of truth".format(cid))

    for cid in sorted(set(cards) & set(board)):
        cs, bs = cards[cid]["status"], board[cid]["status"]
        if cs and cs != bs:
            if "recurring" in (cs, bs):
                notes.append("[recurring] {} — card says '{}', board says '{}' "
                             "(cadence vs current state — fine)".format(cid, cs, bs))
            else:
                problems.append("[status mismatch] {} — card body '{}' vs board '{}'".format(
                    cid, cs, bs))
        ratio = difflib.SequenceMatcher(
            None, norm_title(cards[cid]["title"]), norm_title(board[cid]["title"])).ratio()
        if ratio < TITLE_SIMILARITY_FLOOR:
            notes.append("[title differs {:.0%}] {}".format(ratio, cid)
                         + NL + "      tasks.md: " + cards[cid]["title"][:80]
                         + NL + "      board   : " + board[cid]["title"][:80])

    empty = [cid for cid in sorted(board) if not board[cid]["ailog_len"]]
    if empty:
        notes.append("[no AI log] {} card(s) have an empty ailog: {}".format(
            len(empty), ", ".join(empty)))

    if notes:
        print("ℹ️ notes ({}) — not failures · 참고".format(len(notes)))
        for n in notes:
            print("  · " + n)
        print()

    if not problems:
        print("✅ in sync — tasks.md and the board agree. · 어긋남 없음")
        return 0

    print("⛔ must fix ({}) · 반드시 맞출 것".format(len(problems)))
    for p in problems:
        print("  - " + p)
    print()
    print("This script never edits your files — decide which side is right, fix it, re-run.")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
