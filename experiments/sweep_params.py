"""护士机器人T（speaker 47）参数化微调扫参。
方向：① 风格切换（换真音色）② 压低抑扬（机器腔）③ 音高/语速
输出到 _人类工作区\\试听_v3_参数\\
"""
import json
import pathlib
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:50021"
HERE = pathlib.Path(__file__).parent
OUTDIR = HERE.parent / "_人类工作区" / "试听_v3_参数"
OUTDIR.mkdir(parents=True, exist_ok=True)

TEXT = "ねえ、聞こえる？わたしはあなたの助手です。この声を試しています。"

# (文件名, 说明, speaker_id, query 覆写)
VARIANTS = [
    ("v00_baseline",        "基准：47 ノーマル 默认参数", 47, {}),
    ("v01_style_rakuraku",  "风格：48 楽々",            48, {}),
    ("v02_style_kyoufu",    "风格：49 恐怖",            49, {}),
    ("v03_style_naisho",    "风格：50 内緒話",          50, {}),
    ("v04_into070",         "抑扬 0.70（微平）",         47, {"intonationScale": 0.70}),
    ("v05_into050",         "抑扬 0.50（机器人腔）",      47, {"intonationScale": 0.50}),
    ("v06_into030",         "抑扬 0.30（极平）",         47, {"intonationScale": 0.30}),
    ("v07_pitch090",        "音高 0.90（略低沉）",       47, {"pitchScale": 0.90}),
    ("v08_pitch080",        "音高 0.80（低沉）",         47, {"pitchScale": 0.80}),
    ("v09_slow090",         "语速 0.90（略慢）",         47, {"speedScale": 0.90}),
    ("v10_kyoufu_into060",  "49 恐怖 + 抑扬 0.60",      49, {"intonationScale": 0.60}),
    ("v11_flat_deep",       "抑扬 0.50 + 音高 0.85",     47, {"intonationScale": 0.50, "pitchScale": 0.85}),
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


rows = [f"文本: {TEXT}", "角色: ナースロボ＿タイプＴ (speakers 47/48/49/50)", ""]
ok = 0
for fn, note, sid, over in VARIANTS:
    try:
        q = audio_query(TEXT, sid)
        q.update(over)
        wav = synthesis(q, sid)
        name = f"{fn}.wav"
        (OUTDIR / name).write_bytes(wav)
        rows.append(f"{name:<26} spk={sid}  {over}  — {note}")
        print(f"OK  {name}")
        ok += 1
    except Exception as e:
        rows.append(f"{fn} FAILED: {e}")
        print(f"FAIL {fn}: {e}")

(HERE / "_param_manifest.txt").write_text("\n".join(rows), encoding="utf-8")
print(f"\n{ok}/{len(VARIANTS)} rendered -> {OUTDIR}")
