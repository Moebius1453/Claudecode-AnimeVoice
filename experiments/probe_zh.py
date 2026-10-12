"""探测 VOICEVOX 引擎的能力：是否支持 language 参数 / 中文输入会怎么被解析。输出 UTF-8 文件。"""
import json
import urllib.request
import urllib.parse
import pathlib

BASE = "http://127.0.0.1:50021"
OUT = pathlib.Path(__file__).parent
rep = []

# 1) openapi 里 audio_query 的参数
with urllib.request.urlopen(f"{BASE}/openapi.json", timeout=30) as r:
    spec = json.load(r)

params = spec["paths"]["/audio_query"]["post"].get("parameters", [])
rep.append("=== /audio_query parameters ===")
for p in params:
    rep.append(f"  {p['name']}: required={p.get('required')} schema={p.get('schema')}")

# 2) 全局搜 language / multi
rep.append("")
rep.append("=== schema 里出现 'language' 的地方 ===")
hits = 0
for name, sch in spec.get("components", {}).get("schemas", {}).items():
    props = sch.get("properties", {})
    if "language" in props or "languages" in props:
        rep.append(f"  {name}: {list(props.keys())}")
        hits += 1
if not hits:
    rep.append("  (无)")

# 3) 实测：同一句话，中文 vs 日文，看解析出的 mora
def query(text, speaker):
    qs = urllib.parse.urlencode({"text": text, "speaker": speaker})
    req = urllib.request.Request(f"{BASE}/audio_query?{qs}", method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

TESTS = [
    ("中文", "嘿，能听见吗？我是你的助手，这段话是用来试声音的。"),
    ("日文", "ねえ、聞こえる？わたしはあなたの助手です。この声を試しています。"),
]
for label, text in TESTS:
    try:
        q = query(text, 14)  # 冥鳴ひまり
        mora = q["accent_phrases"]
        kana = "".join(m["text"] for p in mora for m in p["moras"]) if mora else "(空)"
        n_phr = len(mora)
        rep.append("")
        rep.append(f"=== {label} ===")
        rep.append(f"  输入: {text}")
        rep.append(f"  accent_phrases 数: {n_phr}")
        rep.append(f"  解析出的读音(mora text 拼接): {kana[:200]}")
        rep.append(f"  首音节: {mora[0]['moras'][0] if mora and mora[0]['moras'] else '(空)'}")
    except Exception as e:
        rep.append("")
        rep.append(f"=== {label} === FAILED: {type(e).__name__}: {e}")

(OUT / "_zh_probe.txt").write_text("\n".join(rep), encoding="utf-8")
print("written")
