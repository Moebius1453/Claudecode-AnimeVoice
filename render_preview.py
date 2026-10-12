#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_preview.py — 把某个场景的全部台词渲成 wav，供用户试听。

    python render_preview.py              # 默认渲 comeback
    python render_preview.py missed       # 渲指定场景
    python render_preview.py --all        # 渲全部场景

默认输出到项目的 _人类工作区，可用 --out-dir 指定输出根目录。
文件名按序号排，用户听完直接说"第几句"就行。
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
SAY = HERE / "say.py"
OUTROOT = HERE / "_人类工作区"

sys.path.insert(0, str(HERE))
from lines import LINES  # noqa: E402


def render(scenario: str, outroot: pathlib.Path) -> int:
    cfg = LINES[scenario]
    outdir = outroot / f"{scenario}_试听"
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"=== {scenario}  (volume={cfg['volume']}, {len(cfg['lines'])} 句) ===")
    ok = 0
    for i, line in enumerate(cfg["lines"], 1):
        p = outdir / f"{i:02d}.wav"
        r = subprocess.run(
            [sys.executable, str(SAY), line, "--volume", str(cfg["volume"]),
             "--out", str(p), "--keep-engine"],
            capture_output=True, text=True, encoding="utf-8",
        )
        mark = "OK " if r.returncode == 0 else "FAIL"
        print(f"  {mark} {i:02d}  {line}")
        ok += r.returncode == 0
    print(f"-> {outdir}\n")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="渲染场景台词供试听")
    ap.add_argument("scenario", nargs="?", default="comeback", help="场景名（默认 comeback）")
    ap.add_argument("--all", action="store_true", help="渲全部场景")
    ap.add_argument("--out-dir", type=pathlib.Path, default=OUTROOT, help="试听输出根目录")
    args = ap.parse_args()

    names = list(LINES) if args.all else [args.scenario]
    unknown = [n for n in names if n not in LINES]
    if unknown:
        print(f"没有这些场景: {unknown}\n可选: {list(LINES)}", file=sys.stderr)
        return 1

    for n in names:
        render(n, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
