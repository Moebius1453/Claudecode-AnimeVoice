#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 hook 事件调用语音脚本并记录诊断结果。"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
LOG = HERE / "_hook.log"
SAY_TIMER = HERE / "say_timer.py"

BEHAVIOR = {
    "PermissionRequest": ("comeback", 30),
    "PermissionDenied":  ("missed",   60),
    "PostToolUse":       ("chatter",  300),
}

FALLBACK_EVENTS = {"PostToolUseFailure", "StopFailure"}
FALLBACK_KEYWORDS = ("permission", "timed out", "timeout", "denied")


def append_log(event: str, result: str, detail: str = "") -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}\t{event}\t{result}"
    if detail:
        line += f"\t{detail}"
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def decide(event: str, payload: dict):
    """返回场景和冷却秒数；无匹配时返回 None。"""
    if event in BEHAVIOR:
        return BEHAVIOR[event]
    if event in FALLBACK_EVENTS:
        blob = json.dumps(payload, ensure_ascii=False).lower()
        if any(k in blob for k in FALLBACK_KEYWORDS):
            return ("missed", 60)
    return None


def main() -> int:
    event = "?"
    payload: dict = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            payload = json.loads(raw)
            event = payload.get("hook_event_name") or payload.get("event") or "unknown"
    except Exception:
        pass

    # 工具输出可能包含文件内容，不写入日志。
    detail = json.dumps(
        {k: v for k, v in payload.items() if k in
         ("hook_event_name", "tool_name", "message", "error")},
        ensure_ascii=False,
    )[:300]

    decision = decide(event, payload)
    if decision is None:
        append_log(event, "logged-only", detail)
        return 0

    scenario, cooldown = decision

    try:
        proc = subprocess.run(
            [sys.executable, str(SAY_TIMER), "-S", scenario,
             "--cooldown", str(cooldown)],
            capture_output=True, text=True, encoding="utf-8", timeout=90,
        )
        out = (proc.stdout or "").strip().replace("\n", " | ")
        if proc.returncode != 0:
            append_log(event, f"FAIL rc={proc.returncode} {(proc.stderr or '')[:200]}", detail)
        elif "cooldown" in out:
            append_log(event, f"suppressed: {out}", detail)
        else:
            append_log(event, f"spoke: {out}", detail)
        return 0
    except Exception as e:
        append_log(event, f"EXCEPTION {type(e).__name__}: {e}", detail)
        return 0          # 永远返回 0，别让 hook 报错干扰 Claude Code


if __name__ == "__main__":
    raise SystemExit(main())
