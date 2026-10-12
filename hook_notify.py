#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hook_notify.py — Claude Code hook 的入口包装。

做两件事：
  1. 把 hook 收到的内容追加到 _hook.log（诊断用）
  2. 按事件类型决定「说哪句、冷却多久」，再调 say_timer.py

为什么要包装：直接把 say_timer.py 当 hook 命令的话，
一旦没响就分不清是 **hook 没触发** 还是 **脚本执行失败**。

日志格式（TSV）：时间 \t 事件 \t 结果 \t payload摘要
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
LOG = HERE / "_hook.log"
SAY_TIMER = HERE / "say_timer.py"

# 事件 → (场景, 冷却秒数)
#   comeback = 「来一下」      —— 权限提示刚弹出来
#   missed   = 「我还在等」    —— 超时了人还没回来
# 冷却值是用户 2026-10-08 定的：弹出 30s / 超时 60s
BEHAVIOR = {
    "PermissionRequest": ("comeback", 30),
    "PermissionDenied":  ("missed",   60),
}

# 权限超时到底走哪个事件，尚未实测确认。
# 兜底：任何"工具失败"且内容里提到权限/超时的，一律当超时处理。
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
    """返回 (场景, 冷却) —— 或 None 表示只记日志不出声。"""
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

    # 记一行精简的 payload，方便事后确认到底收到了什么
    detail = json.dumps(
        {k: v for k, v in payload.items() if k in
         ("hook_event_name", "tool_name", "tool_response", "message", "error")},
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
