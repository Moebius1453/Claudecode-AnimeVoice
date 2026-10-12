#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""say.py — 用 VOICEVOX 把日文念出来。

独立外挂程序，不依赖 Claude。可以自己手动跑：
    python say.py "そろそろ休んだら？"

引擎按需拉起（冷启约 1 秒），用完自动关掉 —— 不做常驻。
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

# ---------------- 配置 ----------------
CONFIG_PATH = pathlib.Path(__file__).resolve().parent / "config.local.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
ENGINE_PATH = os.environ.get("VOICEVOX_ENGINE_EXE") or CONFIG.get("engine_exe")
ENGINE_EXE = pathlib.Path(ENGINE_PATH).expanduser() if ENGINE_PATH else None
ENGINE_DIR = ENGINE_EXE.parent if ENGINE_EXE else None
HOST = "127.0.0.1"
PORT = 50021
BASE = f"http://{HOST}:{PORT}"

# 音色：ナースロボ＿タイプＴ ノーマル
DEFAULT_SPEAKER = 47
# 备选（用户也很满意）：冥鳴ひまり = 14

START_TIMEOUT = 40.0      # 等引擎起来的秒数上限
READY_POLL = 0.3

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------- 引擎生命周期 ----------------
def _get(path: str, timeout: float = 3.0):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def engine_alive(timeout: float = 3.0) -> bool:
    try:
        _get("/version", timeout)
        return True
    except Exception:
        return False


def start_engine() -> subprocess.Popen | None:
    """拉起引擎，返回 Popen；失败返回 None。"""
    if ENGINE_EXE is None:
        print("请在 config.local.json 设置 engine_exe，或设置 VOICEVOX_ENGINE_EXE 环境变量", file=sys.stderr)
        return None
    if not ENGINE_EXE.exists():
        print(f"引擎不存在: {ENGINE_EXE}", file=sys.stderr)
        return None
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(
        [str(ENGINE_EXE), "--host", HOST, "--port", str(PORT), "--output_log_utf8"],
        cwd=str(ENGINE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    deadline = time.time() + START_TIMEOUT
    while time.time() < deadline:
        if proc.poll() is not None:
            print("引擎进程提前退出", file=sys.stderr)
            return None
        if engine_alive(1.5):
            return proc
        time.sleep(READY_POLL)
    print("等引擎超时", file=sys.stderr)
    proc.terminate()
    return None


def stop_engine(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------- 合成 ----------------
def audio_query(text: str, speaker: int) -> dict:
    qs = urllib.parse.urlencode({"text": text, "speaker": speaker})
    req = urllib.request.Request(f"{BASE}/audio_query?{qs}", method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def synthesis(query: dict, speaker: int) -> bytes:
    req = urllib.request.Request(
        f"{BASE}/synthesis?speaker={speaker}",
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def play_wav(path: pathlib.Path) -> None:
    if sys.platform == "win32":
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME)   # 阻塞到播完
    else:
        for cmd in (["aplay", "-q"], ["afplay"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
            try:
                subprocess.run(cmd + [str(path)], check=True)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        print("找不到可用的播放器", file=sys.stderr)


# ---------------- 主流程 ----------------
def main() -> int:
    ap = argparse.ArgumentParser(description="用 VOICEVOX 念日文")
    ap.add_argument("text", nargs="*", help="要念的文本（日文）")
    ap.add_argument("-f", "--file", help="从文件读文本")
    ap.add_argument("-s", "--speaker", type=int, default=DEFAULT_SPEAKER,
                    help=f"speaker id（默认 {DEFAULT_SPEAKER} = ナースロボ＿タイプＴ）")
    ap.add_argument("--speed", type=float, default=None, help="语速 speedScale（引擎默认 1.0）")
    ap.add_argument("--pitch", type=float, default=None, help="音高 pitchScale，单位半音（引擎默认 0.0=不升降）")
    ap.add_argument("--intonation", type=float, default=None, help="抑扬 intonationScale（引擎默认 1.0；调低=更机器腔）")
    ap.add_argument("--volume", type=float, default=None, help="音量 volumeScale（引擎默认 1.0）")
    ap.add_argument("-o", "--out", help="把 wav 存到这个路径（不播放）")
    ap.add_argument("--no-play", action="store_true", help="只合成不播放")
    ap.add_argument("--keep-engine", action="store_true", help="用完不关引擎")
    ap.add_argument("--status", action="store_true", help="只看引擎状态")
    ap.add_argument("--speakers", action="store_true", help="列出全部角色音色")
    args = ap.parse_args()

    if args.status:
        alive = engine_alive()
        print(f"engine on {BASE}: {'UP' if alive else 'DOWN'}")
        if alive:
            print("version =", _get("/version").decode())
        return 0

    # 引擎：本来就在跑就不动它，是我们拉起来的就负责关掉
    started_here = None
    if not engine_alive():
        started_here = start_engine()
        if started_here is None:
            return 1

    try:
        if args.speakers:
            data = json.loads(_get("/speakers"))
            for sp in data:
                for st in sp["styles"]:
                    print(f"{st['id']:>5}  {sp['name']} / {st['name']}")
            return 0

        if args.file:
            text = pathlib.Path(args.file).read_text(encoding="utf-8").strip()
        elif args.text:
            text = " ".join(args.text)
        elif not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            ap.error("没给文本")

        if not text:
            ap.error("文本是空的")

        q = audio_query(text, args.speaker)
        # 只在显式指定时才覆盖 —— 否则一律用引擎自己的默认值。
        # ⚠ pitchScale 的默认是 0.0（半音），不是 1.0；错设成 1.0 会把音量打到 1/3 且整句变形。
        for key, val in (("speedScale", args.speed),
                         ("pitchScale", args.pitch),
                         ("intonationScale", args.intonation),
                         ("volumeScale", args.volume)):
            if val is not None:
                q[key] = val

        wav = synthesis(q, args.speaker)

        if args.out:
            pathlib.Path(args.out).write_bytes(wav)
            print(f"saved: {args.out}")
            return 0

        if args.no_play:
            print(f"synthesized {len(wav)} bytes (not played)")
            return 0

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav)
            tmp = pathlib.Path(f.name)
        try:
            play_wav(tmp)
        finally:
            tmp.unlink(missing_ok=True)
        return 0

    except urllib.error.HTTPError as e:
        print(f"引擎报错 HTTP {e.code}: {e.read()[:300]!r}", file=sys.stderr)
        return 1
    finally:
        if started_here is not None and not args.keep_engine:
            stop_engine(started_here)


if __name__ == "__main__":
    raise SystemExit(main())
