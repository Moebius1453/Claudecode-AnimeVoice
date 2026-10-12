"""音色融合：同一份 audio_query（来自主音色）分别喂给两个 speaker，
两轨逐样本对齐，再按比例混合 —— 得到真正的"音色融合"而不是重唱。

输出到 _人类工作区\\试听_v2_混音\\
"""
import io
import json
import pathlib
import urllib.parse
import urllib.request
import wave

import numpy as np

BASE = "http://127.0.0.1:50021"
HERE = pathlib.Path(__file__).parent
OUTDIR = HERE.parent / "_人类工作区" / "试听_v2_混音"
OUTDIR.mkdir(parents=True, exist_ok=True)

TEXT = "ねえ、聞こえる？わたしはあなたの助手です。この声を試しています。"

MAIN_ID, MAIN_NAME = 47, "ナースロボ＿タイプＴ"   # 试听 03
BLEND_ID, BLEND_NAME = 14, "冥鳴ひまり"          # 试听 01

# (文件名前缀, 混入比例)
RATIOS = [
    ("r00", 0.00),   # 纯 3 号，参照
    ("r10", 0.10),
    ("r20", 0.20),
    ("r30", 0.30),
    ("r45", 0.45),
    ("r60", 0.60),
]


def audio_query(text, speaker):
    qs = urllib.parse.urlencode({"text": text, "speaker": speaker})
    req = urllib.request.Request(f"{BASE}/audio_query?{qs}", method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def synthesis(query, speaker):
    req = urllib.request.Request(
        f"{BASE}/synthesis?speaker={speaker}",
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def read_wav(b):
    with wave.open(io.BytesIO(b), "rb") as w:
        return w.getparams(), np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def write_wav(path, params, samples):
    with wave.open(str(path), "wb") as w:
        w.setparams(params)
        w.writeframes(samples.astype(np.int16).tobytes())


def rms(x):
    return float(np.sqrt(np.mean((x.astype(np.float64) / 32768.0) ** 2)))


# 一份 query 喂两个 speaker —— 这是"逐样本对齐"的关键
q_main = audio_query(TEXT, MAIN_ID)
wav_main = synthesis(q_main, MAIN_ID)
wav_blend = synthesis(q_main, BLEND_ID)      # 同一份 query！

p_main, s_main = read_wav(wav_main)
p_blend, s_blend = read_wav(wav_blend)

print(f"main  : params={p_main[:4]} samples={len(s_main)}")
print(f"blend : params={p_blend[:4]} samples={len(s_blend)}")
assert p_main[:4] == p_blend[:4], "参数不一致，无法逐样本混合"

# 长度对齐（同一 query 应当等长，保险起见取短的）
n = min(len(s_main), len(s_blend))
s_main, s_blend = s_main[:n].astype(np.float64), s_blend[:n].astype(np.float64)

# 等响度归一：让比例真正代表"音色占比"，而不是"音量占比"
g_main = 0.1 / max(rms(s_main), 1e-9)
g_blend = 0.1 / max(rms(s_blend), 1e-9)
s_main_n, s_blend_n = s_main * g_main, s_blend * g_blend
print(f"rms main={rms(s_main):.4f} blend={rms(s_blend):.4f} (等响度归一后混合)")

# 相关性：证明两轨确实是对齐的（接近 1 = 逐样本对齐）
corr = float(np.corrcoef(s_main_n, s_blend_n)[0, 1])
print(f"correlation(main, blend) = {corr:.4f}   (越接近 1 越说明逐样本对齐)")

rows = [f"文本: {TEXT}", f"主音色 speaker={MAIN_ID}  混入 speaker={BLEND_ID}",
        f"correlation = {corr:.4f}", ""]

for tag, r in RATIOS:
    mixed = s_main_n * (1.0 - r) + s_blend_n * r
    peak = np.max(np.abs(mixed))
    if peak > 0:
        mixed = mixed / peak * 0.95        # 防削波，留 ~0.45dB 余量
    fn = f"{tag}_混入{int(r*100):02d}%.wav"
    write_wav(OUTDIR / fn, p_main, np.clip(mixed, -32768, 32767))
    rows.append(f"{fn}   {int(r*100)}% {BLEND_NAME}")
    print("wrote", fn, "peak_before_norm=%.0f" % peak)

(HERE / "_blend_manifest.txt").write_text("\n".join(rows), encoding="utf-8")
print("outdir:", OUTDIR)
