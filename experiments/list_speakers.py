"""拉取 VOICEVOX 引擎的全部角色/音色清单，输出 UTF-8 文本，避免控制台乱码。"""
import json
import urllib.request
import pathlib

BASE = "http://127.0.0.1:50021"
OUT = pathlib.Path(__file__).parent

with urllib.request.urlopen(f"{BASE}/speakers", timeout=20) as r:
    speakers = json.load(r)

(OUT / "_speakers_raw.json").write_text(
    json.dumps(speakers, ensure_ascii=False, indent=2), encoding="utf-8"
)

lines = []
total = 0
for sp in speakers:
    styles = sp.get("styles", [])
    total += len(styles)
    parts = []
    for s in styles:
        parts.append(f"{s['name']}(id={s['id']},type={s.get('type')})")
    lines.append(f"{sp['name']}\t[{len(styles)}]\t" + " | ".join(parts))

header = [
    f"characters: {len(speakers)}",
    f"styles(total voices): {total}",
    f"engine version: {json.load(urllib.request.urlopen(BASE + '/version'))}",
    "",
]
(OUT / "_speakers.txt").write_text(
    "\n".join(header + lines), encoding="utf-8"
)
print("written:", OUT / "_speakers.txt")
print("characters =", len(speakers), " styles =", total)
