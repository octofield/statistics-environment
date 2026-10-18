"""從 notes/、templates/ 的 markdown 抽出所有公式，輸出 JSON 給 check_math.js 用 KaTeX 檢查。

    python tools/ci/extract_math.py > math.json
    node tools/ci/check_math.js math.json
"""
import json
import re
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[2]
sources = []
for nb_path in [*sorted((ROOT / "notes").glob("*.ipynb")), *sorted((ROOT / "templates").glob("*.ipynb"))]:
    nb = nbformat.read(nb_path, as_version=4)
    sources += [(f"{nb_path.name}#cell{i}", c.source) for i, c in enumerate(nb.cells) if c.cell_type == "markdown"]
sources += [(md.name, md.read_text(encoding="utf-8")) for md in sorted((ROOT / "templates").glob("*.md"))]

out = []
for where, text in sources:
    text = re.sub(r"(```|~~~).*?\1", "", text, flags=re.S)     # 程式碼區塊
    text = re.sub(r"`[^`\n]*`", "", text)                        # 行內程式碼
    text = text.replace(r"\$", "")                               # 跳脫的錢字號
    for m in re.finditer(r"\$\$(.+?)\$\$", text, flags=re.S):
        out.append({"where": where, "display": True, "tex": m.group(1)})
    text = re.sub(r"\$\$(.+?)\$\$", "", text, flags=re.S)
    for m in re.finditer(r"\$([^$\n]+?)\$", text):
        out.append({"where": where, "display": False, "tex": m.group(1)})
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
