#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""say_timer.py — 定时/脚本触发出声。定时器用它，长任务也可以直接用它。

    python say_timer.py                 # 按当前时段自动挑一个场景
    python say_timer.py -S done         # 指定场景（长任务跑完就调这个）
    python say_timer.py -S chatter -n 2 # 连说两句
    python say_timer.py --list          # 看有哪些场景
    python say_timer.py --dry-run       # 只打印不发声
    python say_timer.py -S comeback --cooldown 120   # 冷却：120秒内只响一次
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import pathlib
import random
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).parent
STATE = HERE / "_say_state.json"
LOCK = HERE / "_say.lock"
SAY = HERE / "say.py"
PY = sys.executable or "python"

LOCK_STALE = 30.0     # 锁文件超过这个秒数视为"上家崩了"，抢过来
LOCK_WAIT = 5.0       # 等锁的上限

sys.path.insert(0, str(HERE))
from lines import LINES, TIMER_POOL  # noqa: E402

# 时段 → 场景倾向
def pick_scenario(now: dt.datetime) -> str:
    h = now.hour
    if h >= 23 or h < 6:
        return "late"          # 深夜
    return random.choice(TIMER_POOL)


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"recent": []}


def save_state(st: dict) -> None:
    st["recent"] = st.get("recent", [])[-12:]
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def pick_line(scenario: str, st: dict) -> str:
    pool = LINES[scenario]["lines"]
    recent = set(st.get("recent", []))
    fresh = [x for x in pool if x not in recent]
    line = random.choice(fresh or pool)          # 全说过一轮才允许重复
    st.setdefault("recent", []).append(line)
    return line


def speak(text: str, volume: float, extra: list[str]) -> int:
    cmd = [PY, str(SAY), text]
    if volume != 1.0:
        cmd += ["--volume", str(volume)]
    cmd += extra
    return subprocess.run(cmd).returncode


@contextlib.contextmanager
def claim_lock():
    """跨进程互斥锁（用 O_CREAT|O_EXCL 建锁文件，原子）。

    yield True = 拿到锁；yield False = 等超时了，应该放弃本次。
    ⚠ 只用来包住「查冷却 + 挑句 + 占位 + 落盘」这一小段，
      **发声要放在锁外面** —— 别占着锁播 5 秒音频。
    """
    deadline = time.time() + LOCK_WAIT
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                age = time.time() - LOCK.stat().st_mtime
            except OSError:
                age = 0.0
            if age > LOCK_STALE:            # 上家崩了没解锁，抢过来
                try:
                    LOCK.unlink()
                except OSError:
                    pass
                continue
            if time.time() >= deadline:
                yield False
                return
            time.sleep(0.05)
    try:
        yield True
    finally:
        try:
            LOCK.unlink()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="定时/脚本触发出声")
    ap.add_argument("-S", "--scenario", help="场景名（不指定则按时间自动挑）")
    ap.add_argument("-n", "--count", type=int, default=1, help="说几句")
    ap.add_argument("--list", action="store_true", help="列出场景")
    ap.add_argument("--dry-run", action="store_true", help="只打印不发声")
    ap.add_argument("--keep-engine", action="store_true", help="说完不关引擎")
    ap.add_argument("--cooldown", type=float, default=0.0,
                    help="冷却秒数：距上次出声不足这个时间就静默跳过（默认 0=不限制）")
    args = ap.parse_args()

    if args.list:
        for name, cfg in LINES.items():
            print(f"{name:10} vol={cfg['volume']:<5} {len(cfg['lines'])} 句")
        print(f"\n定时器会从这里挑: {TIMER_POOL}")
        return 0

    scenario = args.scenario or pick_scenario(dt.datetime.now())
    if scenario not in LINES:
        print(f"没有这个场景: {scenario}", file=sys.stderr)
        return 1

    volume = LINES[scenario]["volume"]
    extra = ["--keep-engine"] if args.keep_engine else []

    # ── 锁内：查冷却 → 挑句 → **立刻占位** → 落盘 ──────────────────────
    # ⚠ 必须先占位再发声。之前是"发声结束后才写时间戳"，
    #   两个并发进程（async hook 会并发）在整整 5 秒的发声期间都能通过冷却检查 → 双响。
    lines_to_say: list[str] = []
    with claim_lock() as got:
        if not got:
            print(f"[lock] [{scenario}] 另一实例正在处理，跳过")
            return 0

        st = load_state()
        spoken_at = st.setdefault("last_spoken_by_scenario", {})

        if args.cooldown > 0 and not args.dry_run:
            gap = time.time() - float(spoken_at.get(scenario, 0))
            if gap < args.cooldown:
                print(f"[cooldown] [{scenario}] 距上次 {gap:.0f}s < {args.cooldown:.0f}s，跳过")
                return 0

        for _ in range(max(1, args.count)):
            lines_to_say.append(pick_line(scenario, st))

        if not args.dry_run:
            now = time.time()
            spoken_at[scenario] = now        # ⭐ 先占位
            st["last_spoken"] = now          # 兼容旧字段
            save_state(st)                   # ⭐ 立刻落盘

    # ── 锁外：发声（别占着锁播音频）────────────────────────────────
    for line in lines_to_say:
        print(f"[{scenario}] {line}")
        if not args.dry_run:
            rc = speak(line, volume, extra)
            if rc != 0:
                return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
