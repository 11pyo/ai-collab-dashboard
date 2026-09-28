# -*- coding: utf-8 -*-
"""Stop hook — measure whether the pre-search was used, and nudge when work went unrecorded.
Stop 훅 — 턴이 끝날 때 두 가지를 본다 (2026-09-28 도입).

(1) Which injected cards / archive rows / inquiries did the agent actually mention this turn
    (reply text + tool inputs after the turn started)? → hook_report.py aggregates hit/use rates.
(2) If a knowledge archive (ARCHIVE_PATH env, optional) changed this turn but neither
    inquiry-log.js nor tasks.md did, block the stop once and ask whether to record it.


① 효과 측정: 이번 턴 시작 때 선행검색 훅(prompt_context.py)이 붙여 준 카드·아티클·선례 중
   AI가 실제로 응답·도구 호출에서 언급한 것이 무엇인지 기록한다 → `hook_report.py` 로 적중률 집계.
② 기록 누락 알림: 이번 턴에 archive.html 은 바뀌었는데 문의 기록(inquiry-log.js)·카드(tasks.md)는
   그대로면, 턴 종료를 한 번 막고 「기록할 건이면 기록하라」고 돌려준다(아니면 그대로 끝내면 된다).
   계기: 아카이브만 여러 번 고치고 대시보드엔 흔적이 남지 않은 날이 있었다.

턴마다 한 번만 판정한다(같은 턴의 두 번째 Stop 은 통과).
"""
import datetime
import json
import os
import sys

ROOT = os.environ.get("BOARD_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGDIR = os.environ.get("BOARD_HOOK_LOGDIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
TURNS = os.path.join(LOGDIR, "turns.jsonl")
AUDITS = os.path.join(LOGDIR, "audits.jsonl")
ARCHIVE = os.environ.get("ARCHIVE_PATH", "")  # optional
RECORDS = [os.path.join(ROOT, "inquiry-log.js"), os.path.join(ROOT, "tasks.md")]


def last_line_match(path, pred, tail_bytes=200000):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - tail_bytes))
            lines = f.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if pred(d):
            return d
    return None


def parse_ts(s):
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def turn_text(transcript, since):
    """이번 턴(since 이후) AI의 응답 글과 도구 입력을 한 문자열로."""
    parts = []
    try:
        with open(transcript, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 3000000))
            lines = f.read().decode("utf-8", errors="replace").splitlines()
    except (OSError, TypeError):
        return ""
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant":
            continue
        t = parse_ts(d.get("timestamp", ""))
        if not t or t < since:
            continue
        for c in (d.get("message", {}).get("content") or []):
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif c.get("type") == "tool_use":
                parts.append(json.dumps(c.get("input", {}), ensure_ascii=False))
    return "\n".join(parts)


def mtime_utc(p):
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc)
    except OSError:
        return None


def emit(obj):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, ensure_ascii=False))


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except ValueError:
        data = {}
    session = data.get("session_id", "")
    turn = last_line_match(TURNS, lambda d: d.get("session") == session)
    if not turn:
        return
    if last_line_match(AUDITS, lambda d: d.get("session") == session and d.get("turn") == turn["ts"]):
        return  # 이 턴은 이미 판정함(두 번째 Stop)
    since = parse_ts(turn["ts"])
    if not since:
        return

    hits = turn.get("hits") or []
    text = turn_text(data.get("transcript_path"), since) if hits else ""
    used = [h for h in hits if h.lstrip("#") in text]

    am = mtime_utc(ARCHIVE) if ARCHIVE else None
    archive_changed = bool(am and am >= since)
    recorded = any((m := mtime_utc(p)) and m >= since for p in RECORDS)

    try:
        os.makedirs(LOGDIR, exist_ok=True)
        with open(AUDITS, "a", encoding="utf-8") as f:
            f.write(json.dumps({"session": session, "turn": turn["ts"], "kind": turn.get("kind"),
                                "hits": hits, "used": used, "archive_changed": archive_changed,
                                "recorded": recorded}, ensure_ascii=False) + "\n")
    except OSError:
        pass

    if archive_changed and not recorded and not data.get("stop_hook_active"):
        emit({"decision": "block",
              "reason": "이번 턴에 archive.html 을 고쳤는데 문의 기록(inquiry-log.js)·카드(tasks.md)는 그대로입니다. "
                        "사용자 요청·문의·작업 건이면 log-inquiry.py(--new/--done) 또는 카드 갱신으로 기록하세요. "
                        "순수 지식 정리라 기록할 건이 아니면 그대로 끝내도 됩니다."})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        emit({"systemMessage": "stop_turn_audit 훅 오류(무시하고 진행): " + str(e)[:200]})
