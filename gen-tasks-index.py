# -*- coding: utf-8 -*-
"""
gen-tasks-index.py — build a lightweight session-start index (`tasks-index.md`).

Why this exists · 왜 필요한가
    `tasks.md` is the source of truth, and the usual onboarding rule is "read tasks.md first".
    That rule quietly breaks once the file grows: in the internal deployment this repo was
    anonymized from, `tasks.md` reached ~650,000 characters / 2,250 lines — far past what an
    AI assistant can hold in one context. The rule was still written down, so sessions either
    burned their whole budget on it or skipped it and pretended otherwise.

    The fix is not to shrink the source of truth. It is to generate a thin table of contents:
    the live cards, plus **each card's line range** in `tasks.md`, so a session reads the index
    and then pulls only the card it needs (`sed -n 'A,Bp' tasks.md`).
    Internal result: 650k chars -> ~5k chars (about 1/130).

    `tasks.md` 가 커지면 "착수 시 정본을 먼저 읽어라"는 규칙이 물리적으로 실행 불가능해진다.
    정본을 쪼개는 대신, 살아있는 카드 + **카드별 라인 범위**만 담은 목차를 자동 생성해
    필요한 카드만 부분 읽기 하도록 한다.

Where metadata comes from · 메타 출처
    Status/requester/due/next are read from the board's `TASKS` array, not from any hand-kept
    summary table in the markdown. In the internal deployment the same card data lived in three
    hand-maintained places (card body / a kanban summary table / the board array) and the summary
    table was measurably the first to go stale, so it was removed. Keep one source per field.

Usage · 사용
    python gen-tasks-index.py
    Re-run it after adding or editing any card. Do not hand-edit `tasks-index.md`.
"""
import datetime
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "tasks.md")
BOARD = os.path.join(BASE, "task-board.html")
OUT = os.path.join(BASE, "tasks-index.md")

# --- adapt these to your own board · 자기 보드에 맞게 조정 ---------------------
ID_PREFIXES = "DEV|OPS|TS|ADM"
DONE = ("done", "closed", "완료", "종결")
DROPPED = ("cancelled", "canceled", "dropped", "취소", "철회")
RECURRING = ("recurring", "정기", "주례", "월례", "연례")
OPEN_ORDER = {"in-progress": 0, "received": 1, "waiting": 2, "unknown": 3}
MAXLEN = {"title": 70, "req": 34, "due": 30, "next": 130}
# -----------------------------------------------------------------------------

CARD_RE = re.compile(r"^#{1,6}\s+((?:" + ID_PREFIXES + r")-\d{3})\b\s*[—–-]?\s*(.*)$")
DECL_RE = re.compile(r"const\s+TASKS\s*=\s*\[")
OBJ_RE = re.compile(r"\{\s*[\"']?id[\"']?\s*:")
BACKSLASH = chr(92)
NL = chr(10)
VAL_TMPL = r'[\"\']?{name}[\"\']?\s*:\s*"((?:[^"{bs}]|{bs}.)*)"'


def norm_status(raw):
    """Map a free-text status onto the canonical set. Bilingual on purpose."""
    c = re.sub(r"[*`~✅🔵⏸️📥🔁]", "", raw or "").strip().lower()
    if any(k in c for k in RECURRING):
        return "recurring"
    if any(k in c for k in DROPPED):
        return "dropped"
    if "in-progress" in c or "진행중" in c or "in progress" in c:
        return "in-progress"
    if "received" in c or "접수" in c:
        return "received"
    if "waiting" in c or "대기" in c:
        return "waiting"
    if any(k in c for k in DONE):
        return "done"
    return "unknown"


def clean(v, limit=None):
    v = re.sub(r"[*`]", "", str(v or "")).strip()
    v = re.sub(r"\s+", " ", v).replace("|", "/")
    if limit and len(v) > limit:
        v = v[:limit].rstrip() + "…"
    return v


def slice_array(text, open_at):
    """Return text[open_at:] up to the matching ']'. Brackets inside strings are ignored."""
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


def load_board():
    """Read the board's TASKS array.

    Two dialects are supported on purpose: boards whose array was last written by the UI's
    save button are strict JSON (quoted keys); hand-written ones use JS object literals
    (bare keys). Try JSON first, fall back to a per-object regex scan.
    """
    if not os.path.exists(BOARD):
        return {}
    b = io.open(BOARD, encoding="utf-8").read()
    # NB: a plain find("const TASKS") also matches prose inside a card's ailog that happens to
    # mention the array. Match the declaration itself.
    m = DECL_RE.search(b)
    if not m:
        return {}
    raw = slice_array(b, b.index("[", m.start()))
    if raw:
        try:
            return {t["id"]: t for t in json.loads(raw) if t.get("id")}
        except ValueError:
            pass
    arr = b[m.start():]
    starts = [mm.start() for mm in OBJ_RE.finditer(arr)]
    out = {}
    for i, s0 in enumerate(starts):
        s1 = starts[i + 1] if i + 1 < len(starts) else len(arr)
        chunk = arr[s0:s1]
        cid = js_field(chunk, "id")
        if cid:
            out[cid] = {k: js_field(chunk, k)
                        for k in ("id", "cls", "status", "title", "req", "due", "next")}
    return out


WAIT_HEADS = ("| waiting on", "| 대기 근거")
DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


def _tail(chunk, head_len):
    return chunk[head_len:].strip(" :=")


def parse_wait(cell):
    """Parse a "waiting on" row into {what, sent, due, duedate, then}.

    Row format (either language):
        | Waiting on | reply from X · sent unconfirmed · due 2026-09-05 · if overdue: close |
        | 대기 근거 | 외부회신 — X 앞 메일 · 발송 미확인 · 회신기한 2026-09-05 · 기한 경과 시 종결 |

    NOTE: `sent` defaults to **unconfirmed**, never "not sent". The human may have
    sent it without telling the agent — asserting "not sent" causes the opposite
    error (advising a re-send of something already sent).
    """
    c = re.sub(r"[*`]", "", cell).strip()
    if not c:
        return None
    what, sent, due, then = "", "unconfirmed / 미확인", "", ""
    for chunk in [x.strip() for x in c.split("·")]:
        if not chunk:
            continue
        low = chunk.lower()
        if low.startswith("sent"):
            sent = _tail(chunk, 4) or sent
        elif chunk.startswith("발송"):
            sent = _tail(chunk, 2) or sent
        elif "경과" in chunk or low.startswith("if overdue"):
            then = (chunk.split("시", 1)[-1] if "경과" in chunk else chunk.split(":", 1)[-1]).strip(" :")
        elif low.startswith("due"):
            due = _tail(chunk, 3)
        elif chunk.startswith("회신기한"):
            due = _tail(chunk, 4)
        elif not what:
            what = chunk
    m = DATE_RE.search(due)
    duedate = None
    if m:
        try:
            duedate = datetime.date(*[int(x) for x in m.group(1).split("-")])
        except ValueError:
            duedate = None
    return {"what": what, "sent": sent, "due": due or "—", "duedate": duedate, "then": then}


def wait_cell(line):
    """Return the value of a "waiting on" row — table cell or bullet — else None."""
    st = line.strip()
    plain = re.sub(r"[*`]", "", st).lower()
    if plain.startswith("| waiting on") or plain.startswith("| 대기 근거"):
        cells = st.split("|")
        return cells[2] if len(cells) >= 3 else None
    if plain.startswith("- waiting on") or plain.startswith("- 대기 근거"):
        return st.split(":", 1)[1] if ":" in st else None
    return None


def collect_waits(spans, live):
    """Scan each open card's line range for its "waiting on" row."""
    lines = io.open(SRC, encoding="utf-8").read().split(NL)
    out = []
    for cid in live:
        sp = spans[cid]
        for ln in lines[sp["start"] - 1:sp["end"]]:
            cell = wait_cell(ln)
            if cell is not None:
                w = parse_wait(cell)
                if w:
                    w["id"] = cid
                    out.append(w)
                break
    return out


def load_cards():
    """{id: {title, start, end}} — heading line ranges in tasks.md."""
    lines = io.open(SRC, encoding="utf-8").read().split(NL)
    starts = []
    for i, line in enumerate(lines, start=1):
        m = CARD_RE.match(line)
        if m:
            starts.append((m.group(1), m.group(2).strip(), i))
    spans = {}
    for idx, (cid, title, start) in enumerate(starts):
        end = starts[idx + 1][2] - 1 if idx + 1 < len(starts) else len(lines)
        spans[cid] = {"title": title, "start": start, "end": end}
    return spans, len(lines), sum(len(x) for x in lines)


def main():
    if not os.path.exists(SRC):
        sys.exit("tasks.md not found: " + SRC)
    spans, n_lines, n_chars = load_cards()
    if not spans:
        sys.exit("No card headings found. Check ID_PREFIXES / heading format.")
    board = load_board()

    meta = {}
    for cid, t in board.items():
        meta[cid] = {
            "title": clean(t.get("title"), MAXLEN["title"]),
            "status": norm_status(t.get("status")),
            "req": clean(t.get("req"), MAXLEN["req"]),
            "due": clean(t.get("due"), MAXLEN["due"]),
            "next": clean(t.get("next"), MAXLEN["next"]),
        }

    live, recur, closed, unlisted = [], [], [], []
    for cid in sorted(spans):
        m = meta.get(cid)
        if m is None:
            unlisted.append(cid)
        elif m["status"] == "recurring":
            recur.append(cid)
        elif m["status"] in ("done", "dropped"):
            closed.append(cid)
        else:
            live.append(cid)
    live.sort(key=lambda c: (OPEN_ORDER.get(meta[c]["status"], 9), c))

    o = ["# Task index — session start · 세션 착수 인덱스", "",
         "> ⚠️ **Generated file. Do not hand-edit.** · 자동 생성물, 손으로 고치지 말 것.",
         "> Source of truth is `tasks.md`; re-run `python gen-tasks-index.py` after editing it.",
         "", "**How to use · 읽는 법**",
         "1. Read this index to see what is actually open.",
         "2. Then read **only that card's line range** from `tasks.md` "
         "— e.g. `sed -n '60,88p' tasks.md`.",
         "3. When working a card, read the body **and** its AI context log.",
         "",
         "- {} cards — open {} / recurring {} / closed {}{} · `tasks.md` {:,} chars / {:,} lines".format(
             len(spans), len(live), len(recur), len(closed),
             " / ⚠️ not on board {}".format(len(unlisted)) if unlisted else "", n_chars, n_lines),
         "", "---", "", "## 🔥 Open · 살아있는 카드", ""]

    if live:
        o += ["| ID | Title | Status | Requester | Due | Next action | tasks.md lines |",
              "|---|---|---|---|---|---|---|"]
        for cid in live:
            m, sp = meta[cid], spans[cid]
            o.append("| **{}** | {} | {} | {} | {} | {} | L{}–{} ({} lines) |".format(
                cid, m["title"], m["status"], m["req"], m["due"], m["next"],
                sp["start"], sp["end"], sp["end"] - sp["start"] + 1))
    else:
        o.append("_Nothing open._")

    waits = collect_waits(spans, live)
    today = datetime.date.today()
    o += ["", "## 📤 Awaiting reply · 회신·응답 대기", ""]
    if waits:
        o += ["> Generated on **{}**. Compare the due dates below with **today's date** and, "
              "if one has passed, ask the human once: *did you send it? did a reply come back?*".format(today.isoformat()),
              "> ⚠️ `sent` defaults to **unconfirmed** — the human may have sent it without telling you. "
              "Never record \"not sent\" unless they said so.",
              "",
              "| ID | Waiting on | Sent | Due | If overdue |", "|---|---|---|---|---|"]
        for w in sorted(waits, key=lambda x: (x["duedate"] or datetime.date.max, x["id"])):
            over = ""
            if w["duedate"] and (today - w["duedate"]).days > 0:
                over = " ⏰**{}d overdue**".format((today - w["duedate"]).days)
            o.append("| **{}** | {} | {} | {}{} | {} |".format(
                w["id"], w["what"] or "—", w["sent"], w["due"], over, w["then"] or "—"))
    else:
        o.append("_Nothing awaiting a reply._")

    o += ["", "## 🔁 Recurring · 정기 카드 (run when triggered)", ""]
    if recur:
        o += ["| ID | Title | Cadence / trigger | Next action | tasks.md lines |", "|---|---|---|---|---|"]
        for cid in recur:
            m, sp = meta[cid], spans[cid]
            o.append("| **{}** | {} | {} | {} | L{}–{} |".format(
                cid, m["title"], m["due"], m["next"], sp["start"], sp["end"]))
    else:
        o.append("_None._")

    o += ["", "## ✅ Closed · 종료 카드 (reference only)", ""]
    for cid in closed:
        sp, m = spans[cid], meta[cid]
        mark = "❌ " if m["status"] == "dropped" else ""
        o.append("- {}**{}** — {} · L{}–{}".format(mark, cid, m["title"], sp["start"], sp["end"]))
    if not closed:
        o.append("_None._")

    if unlisted:
        o += ["", "## ⚠️ Missing from the board · 보드에 없는 카드", "",
              "These exist in `tasks.md` but not in the `TASKS` array — "
              "they do not render on the board and have no status/due metadata.", ""]
        o += ["- **{}** — {} · L{}–{}".format(cid, spans[cid]["title"],
                                              spans[cid]["start"], spans[cid]["end"])
              for cid in unlisted]
    o.append("")

    io.open(OUT, "w", encoding="utf-8", newline=NL).write(NL.join(o))
    over_n = len([w for w in waits if w["duedate"] and w["duedate"] < today])
    print("wrote {}".format(OUT))
    if over_n:
        print("  ⏰ {} reply deadline(s) passed - see the 'Awaiting reply' section".format(over_n))
    print("  {} cards (open {} / recurring {} / closed {} / not-on-board {})".format(
        len(spans), len(live), len(recur), len(closed), len(unlisted)))
    print("  tasks.md {:,} chars -> index {:,} chars".format(n_chars, sum(len(x) for x in o)))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
