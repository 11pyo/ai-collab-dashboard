# -*- coding: utf-8 -*-
"""
log-inquiry.py — append-only logger for the inquiry board (inquiry-log.js).

The whole point: it is **append-only** (one push line per call) and **merges by id**,
so multiple sessions / people can write concurrently without clobbering each other.
A short OS file-lock guards the append so two writers can't lose a line at EOF.

Status flow: received → in-progress → waiting → done
(rendered as a 4-column board in task-board.html; the done column scrolls).

① receive (new inquiry comes in): logged as "received" → top of the received column
   python log-inquiry.py --new --type simple --q "summary" --by alice [--date 2026-01-04]
   → remember the id printed as 'NEW id=INQ...'.

② transition / fill in (same id):
   python log-inquiry.py --id INQ123 --status in-progress
   python log-inquiry.py --id INQ123 --status waiting
   python log-inquiry.py --done --id INQ123 --a "resolution summary" --ref "#anchor"   # = done

If an inquiry is answered the moment it arrives, pass --a (or --status done) in ① to finish it.
type examples: simple | request | urgent   /   status: received | in-progress | waiting | done

Why a Python helper instead of editing inquiry-log.js by hand:
the file is an append-only push log; hand-editing invites concurrent-write corruption.
Always go through this helper.
"""
import argparse, json, sys, io, os, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inquiry-log.js")
VALID = ("received", "in-progress", "waiting", "done")

def ensure():
    if not os.path.exists(LOG):
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("window.INQUIRY_LOG = window.INQUIRY_LOG || [];\n")

def _lock(lf):
    # short OS lock: stops two sessions writing the same EOF and dropping a line.
    # a plain append("a") is NOT atomic on Windows (lseek→write race). best-effort.
    try:
        if os.name == "nt":
            import msvcrt
            lf.seek(0); msvcrt.locking(lf.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lf, fcntl.LOCK_EX)
    except Exception:
        pass

def _unlock(lf):
    try:
        if os.name == "nt":
            import msvcrt
            lf.seek(0); msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lf, fcntl.LOCK_UN)
    except Exception:
        pass

def append(obj):
    ensure()
    line = "window.INQUIRY_LOG.push(" + json.dumps(obj, ensure_ascii=False) + ");\n"
    lockpath = LOG + ".lock"
    try:
        with open(lockpath, "a+") as lf:        # lock gate (content irrelevant)
            _lock(lf)
            try:
                with open(LOG, "a", encoding="utf-8") as f:
                    f.write(line)               # atomic append while holding the lock
            finally:
                _unlock(lf)
    except Exception:
        with open(LOG, "a", encoding="utf-8") as f:   # even if locking fails, keep the record
            f.write(line)

ap = argparse.ArgumentParser()
ap.add_argument("--new",  action="store_true", help="receive: log a new inquiry")
ap.add_argument("--done", action="store_true", help="mark done (= --status done)")
ap.add_argument("--id",   default="", help="target id for transition/fill (from --new output)")
ap.add_argument("--status", default="", help="received|in-progress|waiting|done")
ap.add_argument("--date", default="", help="YYYY-MM-DD (today)")
ap.add_argument("--type", default="", help="simple|request|urgent")
ap.add_argument("--q",    default="", help="inquiry summary")
ap.add_argument("--a",    default="", help="resolution / answer summary")
ap.add_argument("--by",   default="", help="who logged it")
ap.add_argument("--ref",  default="", help="archive anchor (optional, e.g. #ts-account-auth)")
ap.add_argument("--req",  default="", help="requester / team (shown as a chip next to the id, e.g. alice/sales)")
ap.add_argument("--archive-before", default="", metavar="YYYY-MM-DD",
                help="v2: move DONE inquiries dated before this date into inquiry-log-archive-<YYYYHN>.js (removed from active)")
ap.add_argument("--compact", action="store_true",
                help="v2: rewrite the active log, folding each id's pushes into one current-state line")
x = ap.parse_args()

# ── v2 maintenance ops (these REWRITE files; not append-only — run at a quiet time) ──
import re
def _read_pushes(path):
    if not os.path.exists(path):
        return []
    txt = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"window\.INQUIRY_LOG\.push\((\{.*?\})\);", txt):
        try:
            out.append(json.loads(m.group(1)))
        except Exception:
            pass
    return out

def _fold(rows):
    by, order = {}, []
    for r in rows:
        if not r.get("id"):
            continue
        if r["id"] not in by:
            order.append(r["id"]); by[r["id"]] = {}
        by[r["id"]].update(r)
    return [by[i] for i in order]

def _write_log(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write("window.INQUIRY_LOG = window.INQUIRY_LOG || [];\n")
        for r in rows:
            f.write("window.INQUIRY_LOG.push(" + json.dumps(r, ensure_ascii=False) + ");\n")

if x.compact:
    rows = _read_pushes(LOG)
    folded = _fold(rows)
    _write_log(LOG, folded)
    print("COMPACT %s: %d pushes -> %d (one per id)" % (os.path.basename(LOG), len(rows), len(folded)))
    sys.exit(0)

if x.archive_before:
    cutoff = x.archive_before
    rows = _read_pushes(LOG)
    folded = _fold(rows)
    move_ids = {r["id"] for r in folded if r.get("status") == "done" and (r.get("date") or "") < cutoff}
    if not move_ids:
        sys.exit("[archive] nothing to move (no DONE items dated before %s)" % cutoff)
    mm = int(cutoff[5:7]) if len(cutoff) >= 7 else 1
    tag = "%sH%d" % (cutoff[:4], 1 if mm <= 6 else 2)
    arch = os.path.join(os.path.dirname(LOG), "inquiry-log-archive-%s.js" % tag)
    keep  = [r for r in rows if r["id"] not in move_ids]
    moved = [r for r in rows if r["id"] in move_ids]
    _write_log(arch, _read_pushes(arch) + moved)   # append to (or create) the archive
    _write_log(LOG, keep)                           # rewrite active without the moved ids
    print("ARCHIVE -> %s : moved %d ids (%d pushes); active now %d pushes"
          % (os.path.basename(arch), len(move_ids), len(moved), len(keep)))
    sys.exit(0)

if x.status and x.status not in VALID:
    sys.exit("[error] --status must be one of " + "|".join(VALID))

if x.new:
    iid = x.id or ("INQ-" + time.strftime("%y%m%d-%H%M%S"))   # e.g. INQ-260104-143022 (readable unique code)
    status = x.status or ("done" if x.a else "received")
    obj = {"id": iid, "date": x.date, "type": (x.type or "simple"), "q": x.q,
           "by": x.by, "req": x.req, "a": x.a, "ref": x.ref, "status": status}
    append(obj)
    print("NEW id=" + iid + " status=" + status)
elif x.id:
    obj = {"id": x.id}
    if x.done:
        obj["status"] = "done"
    elif x.status:
        obj["status"] = x.status
    for k in ("a", "ref", "q", "by", "req", "date", "type"):   # only update fields that were given
        v = getattr(x, k)
        if v:
            obj[k] = v
    if len(obj) == 1:
        sys.exit("[error] --id alone changes nothing (need --status/--done/--a/--ref ...)")
    append(obj)
    print("UPDATE id=" + x.id + (" status=" + obj["status"] if "status" in obj else ""))
else:
    sys.exit("[error] specify --new (receive) or --id (transition/done)")
