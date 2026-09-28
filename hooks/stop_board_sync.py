# -*- coding: utf-8 -*-
"""Stop hook — when a turn ends with the card files changed, regenerate the index and run the sync check.
Stop 훅 — 카드 파일이 바뀐 채로 턴이 끝나면 인덱스 재생성 + 동기화 점검을 자동으로 돈다.

Two written rules ("re-run gen-tasks-index.py after editing cards", "run check-board-sync.py
before you finish") become one hook. The trigger is file mtime, not which tool edited the
file, so edits made through ad-hoc scripts are caught too.

- Nothing changed since the last passing check → does nothing (zero cost per turn).
- Check fails (exit 1) → blocks the stop once and hands the drift back to the agent.
  On the second Stop of the same turn (`stop_hook_active`) it only notifies — no loop.
"""
import json
import os
import subprocess
import sys

ROOT = os.environ.get("BOARD_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = [os.path.join(ROOT, "tasks.md"), os.path.join(ROOT, "task-board.html")]
INDEX = os.path.join(ROOT, "tasks-index.md")
MARKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_board_sync")


def mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0.0


def run(script):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, script)], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def emit(obj):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, ensure_ascii=False))


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except ValueError:
        data = {}
    if max(mtime(p) for p in SOURCES) <= mtime(MARKER):
        return

    notes = []
    if mtime(SOURCES[0]) > mtime(INDEX):
        code, out = run("gen-tasks-index.py")
        notes.append("tasks-index.md regenerated" + ("" if code == 0 else " FAILED: " + out[-300:]))

    code, out = run("check-board-sync.py")
    if code == 0:
        with open(MARKER, "w", encoding="utf-8") as f:
            f.write("ok")
        emit({"systemMessage": "board sync check passed" + (" · " + ", ".join(notes) if notes else "")})
        return

    tail = "\n".join(out.strip().splitlines()[-25:])
    if data.get("stop_hook_active"):
        emit({"systemMessage": "⚠ tasks.md ↔ task-board.html drift remains — run check-board-sync.py"})
        return
    emit({"decision": "block",
          "reason": "Card files changed and check-board-sync.py failed. Fix the drift below before finishing.\n" + tail})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a broken hook must not trap the turn
        emit({"systemMessage": "stop_board_sync hook error (ignored): " + str(e)[:200]})
