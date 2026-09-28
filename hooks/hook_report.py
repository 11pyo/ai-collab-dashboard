# -*- coding: utf-8 -*-
"""Pre-search hook report — `python hooks/hook_report.py [--days 14]`.
선행검색 훅 효과 집계 (2026-09-28 도입).

turns.jsonl(질문마다 훅이 무엇을 찾았나) + audits.jsonl(AI가 그중 무엇을 실제로 언급했나)을 합쳐
적중률·사용률·일치 없음 비율과, 일치 없음이 잦은 키워드(사전에 없는 말 → 검색 규칙 개선 후보)를 보여 준다.
"""
import argparse
import collections
import datetime
import json
import os
import sys

LOGDIR = os.environ.get("BOARD_HOOK_LOGDIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def load(name):
    out = []
    try:
        with open(os.path.join(LOGDIR, name), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=a.days)

    def recent(d, key):
        try:
            return datetime.datetime.fromisoformat(d[key]) >= since
        except (KeyError, ValueError):
            return False

    turns = [t for t in load("turns.jsonl") if recent(t, "ts")]
    audits = {(x["session"], x["turn"]): x for x in load("audits.jsonl") if recent(x, "turn")}
    kinds = collections.Counter(t.get("kind") for t in turns)
    searched = [t for t in turns if t.get("kind") == "searched"]
    with_hits = [t for t in searched if t.get("hits")]
    no_match = [t for t in searched if not t.get("hits")]

    hit_total = used_total = judged = 0
    for t in with_hits:
        au = audits.get((t.get("session"), t.get("ts")))
        if au is None:
            continue
        judged += 1
        hit_total += len(au.get("hits") or [])
        used_total += len(au.get("used") or [])
    missed_kw = collections.Counter(k for t in no_match for k in (t.get("keywords") or []))
    nudges = sum(1 for x in audits.values() if x.get("archive_changed") and not x.get("recorded"))

    pct = lambda n, d: "-" if not d else "%d%%" % round(100 * n / d)
    print("선행검색 훅 효과 — 최근 %d일" % a.days)
    print("  질문 %d건: 검색 %d · 키워드 없음 %d · 짧은 말 %d · 하위 에이전트 보고 %d" % (
        len(turns), len(searched), kinds.get("nokeyword", 0), kinds.get("short", 0), kinds.get("handback", 0)))
    print("  검색한 질문 중 일치 있음 %s (%d/%d)" % (pct(len(with_hits), len(searched)), len(with_hits), len(searched)))
    print("  붙여 준 항목 중 AI가 실제 언급 %s (%d/%d, 판정된 턴 %d)" % (pct(used_total, hit_total), used_total, hit_total, judged))
    print("  기록 누락 알림 %d회" % nudges)
    if missed_kw:
        print("  일치 없음이 잦은 키워드(사전 보강 후보): " + ", ".join("%s(%d)" % kv for kv in missed_kw.most_common(10)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
