# -*- coding: utf-8 -*-
"""Tool gates — stop the agent's repeat mistakes right before / after a tool call.
도구 관문 훅 — 반복된 실수를 도구 호출 직전·직후에 막는다 (2026-09-28 도입).

Wire PreToolUse to your SQL tool(s) and Bash, PostToolUse to the SQL tool(s) and your
source-deploy / activate tools (see settings.example.json). Tool names below are examples
from an SAP ADT MCP server; any tool whose name ends in `__runQuery` is treated as SQL.


PreToolUse (막기 — 실행 전에 고쳐 쓰게 한다)
  ① runQuery: SQL 한 줄이 255자를 넘으면 「Internal server error」가 난다 · `SELECT *` 금지
  ④ Bash: `> "$변수"` 리다이렉션인데 그 변수가 명령 안에서 정해지지도, 환경에 있지도 않으면 차단
          (미설정 변수로 엉뚱한 경로에 쓰거나 셸이 멈춘 사고 3연속 — 공통본 §3)
PostToolUse (알림 — 결과 옆에 한 줄 붙인다)
  ② runQuery 결과에 소수 2자리 값이 있으면: 원화 CURR 은 DB 원본에서 소수점 두 자리를 떼고 말한다
     (×100 누락이 반복됐던 실수)
  ③ 개발계 소스 반영·활성화 직후: 원격 재조회 0줄 diff 확인 + 재테스트 요청 땐 재진입 안내

오류가 나도 도구 호출을 막지 않는다(조용히 통과).
"""
import json
import os
import re
import sys

SQL_LIMIT = 255
SAFE_ENV = {"TEMP", "TMP", "HOME", "PWD", "USERPROFILE", "CLAUDE_PROJECT_DIR", "APPDATA", "LOCALAPPDATA"}


def out(obj):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, ensure_ascii=False))


def deny(reason):
    out({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                "permissionDecisionReason": reason}})


def context(event, text):
    out({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def check_sql(sql):
    long_lines = [i + 1 for i, l in enumerate(sql.splitlines()) if len(l) > SQL_LIMIT]
    if long_lines:
        return ("SQL %s번째 줄이 %d자를 넘습니다 — 개발계 runQuery 는 한 줄 %d자 초과 시 「Internal server error」를 냅니다. "
                "SELECT 목록·WHERE 조건·IN 목록을 여러 줄로 나눠 다시 호출하세요(조인·EXISTS·긴 IN 도 줄만 나누면 됩니다)."
                % (",".join(map(str, long_lines)), SQL_LIMIT, SQL_LIMIT))
    if re.search(r"\bselect\s+(distinct\s+)?\*", sql, re.I):
        return ("`SELECT *` 는 금지입니다(키 + 필요한 컬럼만). 필요한 컬럼을 나열하고, 행 수 제한과 "
                "최신 버전 조건을 붙여 다시 호출하세요. 건수만 필요하면 `COUNT(*)`.")
    return None


def assigned_vars(cmd):
    names = set(re.findall(r"(?:^|[\s;&|(]|export\s+|local\s+|declare\s+(?:-\w+\s+)?)([A-Za-z_]\w*)=", cmd))
    names |= set(re.findall(r"\bfor\s+([A-Za-z_]\w*)\s+in\b", cmd))
    names |= set(re.findall(r"\bread\s+(?:-\w+\s+)*([A-Za-z_]\w*)", cmd))
    return names


def check_bash(cmd):
    targets = re.findall(r"(?<![0-9&])>>?\s*\"?\$\{?([A-Za-z_]\w*)", cmd)
    if not targets:
        return None
    known = assigned_vars(cmd)
    bad = sorted({v for v in targets if v not in known and v not in SAFE_ENV and not os.environ.get(v)})
    if bad:
        return ("리다이렉션 대상 변수 %s 가 이 명령 안에서 정해지지 않았고 환경에도 없습니다 — 빈 값이면 엉뚱한 경로에 쓰거나 "
                "셸이 입력을 기다리며 멈춥니다(공통본 §3). 같은 명령 안에서 변수를 먼저 정하거나 경로를 직접 쓰세요. "
                "파일 편집은 스크립트 파일로." % ", ".join("$" + v for v in bad))
    return None


def has_amount_column(resp):
    """금액일 수 있는 결과인가 — 패킹 10진(P) 컬럼이 있거나 소수 2자리 값이 보이면.
    주의: runQuery 는 P 값을 JSON 숫자로 돌려줘 `.00` 이 떨어진다(56670.00 → 56670) — 값 모양만으로는 못 잡는다."""
    text = resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False)
    text = text.replace('\\"', '"')  # 문자열로 한 번 더 감싼 JSON 도 읽히게
    if re.search(r'"type"\s*:\s*"P"', text):
        return True
    return re.search(r'(?<![\d.])-?\d{1,15}\.\d{2}(?![\d.])', text) is not None


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    except ValueError:
        return
    event, tool = data.get("hook_event_name", ""), data.get("tool_name", "")
    tin = data.get("tool_input") or {}

    if event == "PreToolUse":
        if tool.endswith("__runQuery"):
            r = check_sql(tin.get("sqlQuery", ""))
            if r:
                deny(r)
        elif tool == "Bash":
            r = check_bash(tin.get("command", ""))
            if r:
                deny(r)
        return

    if event == "PostToolUse":
        if tool.endswith("__runQuery") and has_amount_column(data.get("tool_response")):
            context(event, "💱 조회 결과에 금액일 수 있는 값(패킹 10진·소수 2자리)이 있습니다. 원화(KRW) CURR 필드라면 DB 원본값이므로 "
                           "(이 도구는 끝의 .00 을 떼고 보여 준다 — 56670 은 566.70 이 아니라 56,670.00 = 5,667,000원) "
                           "**소수점 두 자리를 떼고(×100) 원으로** 말합니다 — 10.00 = 1,000원. 화면(ALV) 표시값은 그대로. "
                           "외화·수량·비율 필드면 해당 없음.")
        elif tool in ("mcp__mcp-abap-abap-adt-api__setObjectSource", "mcp__mcp-abap-abap-adt-api__activateObjects",
                      "mcp__mcp-abap-abap-adt-api__activateByName"):
            context(event, "🔁 반영·활성화 성공 ≠ 의도한 변경. ① `getObjectSource` 로 원격 소스를 다시 읽어 로컬 수정본과 "
                           "**0줄 diff** 를 확인 ② 소스 맨 위 수정이력 한 줄 ③ 사용자에게 재테스트를 요청할 땐 "
                           "**트랜잭션을 나갔다 다시 들어오거나 재로그인**하라고 함께 안내(열려 있던 세션은 옛 코드로 돈다).")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
