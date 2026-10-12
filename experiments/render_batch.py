"""批量试听：同一句日文，用多个候选音色合成，输出到 _人类工作区。
选角依据 = 角色设定（AI/机器人/电子系），不按 F0 排序。
"""
import json
import pathlib
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:50021"
HERE = pathlib.Path(__file__).parent
OUTDIR = HERE.parent / "_人类工作区" / "试听_v1"
OUTDIR.mkdir(parents=True, exist_ok=True)

TEXT = "ねえ、聞こえる？わたしはあなたの助手です。この声を試しています。"

# (序号, 显示名, speaker_id, 备注)
CANDIDATES = [
    ("01", "冥鳴ひまり",         14, "人气最高、声线偏冷静微哑"),
    ("02", "Voidoll",            89, "设定就是 AI/支援型机器人"),
    ("03", "ナースロボ＿タイプＴ", 47, "名字直译=护士机器人，机械感最强"),
    ("04", "琴詠ニア",            74, "安卓系角色"),
    ("05", "小夜/SAYO",           46, "电子/扁平声线"),
    ("06", "No.7",               29, "安卓系角色"),
    ("07", "春日部つむぎ",          8, "主流自然女声（对照组）"),
    ("08", "九州そら",            16, "主流自然女声（对照组）"),
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


manifest = [f"试听文本: {TEXT}", f"引擎: VOICEVOX 0.25.2 (CPU)", ""]
for idx, name, sid, note in CANDIDATES:
    try:
        q = audio_query(TEXT, sid)
        wav = synthesis(q, sid)
        fn = f"{idx}_{name.replace('/', '_')}.wav"
        (OUTDIR / fn).write_bytes(wav)
        manifest.append(f"{idx}  {name}  (speaker={sid})  {len(wav):,} bytes  — {note}")
        print(f"OK   {fn}")
    except Exception as e:
        manifest.append(f"{idx}  {name}  (speaker={sid})  FAILED: {e}")
        print(f"FAIL {name}: {e}")

(HERE / "_render_manifest.txt").write_text("\n".join(manifest), encoding="utf-8")
print("outdir:", OUTDIR)
