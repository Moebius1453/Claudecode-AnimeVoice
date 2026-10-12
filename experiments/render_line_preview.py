"""把每个场景的第一句各渲一个 wav，给用户听语气（不播放）。"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from lines import LINES  # noqa: E402

OUT = HERE.parent / "_人类工作区" / "台词预览"
OUT.mkdir(parents=True, exist_ok=True)
SAY = str(HERE.parent / "say.py")

for i, (name, cfg) in enumerate(LINES.items(), 1):
    line = cfg["lines"][0]
    out = OUT / f"{i:02d}_{name}.wav"
    cmd = [sys.executable, SAY, line, "--volume", str(cfg["volume"]),
           "--out", str(out), "--keep-engine"]
    rc = subprocess.run(cmd, capture_output=True)
    print(f"{'OK ' if rc.returncode == 0 else 'FAIL'} {out.name:<22} vol={cfg['volume']:<5} {line}")
    if rc.returncode != 0:
        print("   ", rc.stderr.decode("utf-8", "replace")[:200])

print("\noutdir:", OUT)
