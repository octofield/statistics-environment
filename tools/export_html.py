"""把 .ipynb 匯出成 HTML（圖片內嵌），並做繳交前檢查。

    python tools/export_html.py 檔案.ipynb [更多.ipynb] [--execute]

--execute：先從頭重新執行整份 notebook（等於 Restart & Run All），確認沒有「隱藏狀態」。
沒有給檔案時，會列出 exam/ 裡的 notebook 讓你選。
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_exam import load_student  # noqa: E402


def lint(nb, path):
    warns = []
    # 考卷保留老師的原檔名，所以只檢查內容裡有沒有寫學號（tools/student.json 有設定時）
    sid = load_student().get("id", "")
    if sid and not any(sid.lower() in c.source.lower() for c in nb.cells):
        warns.append(f"考卷裡找不到你的學號 {sid}，記得依老師的格式寫上學號、姓名")
    code_cells = [c for c in nb.cells if c.cell_type == "code" and c.source.strip()]
    never_run = [i for i, c in enumerate(code_cells, 1) if c.get("execution_count") is None]
    if never_run:
        warns.append(f"有 {len(never_run)} 個 code cell 沒有執行（輸出是空的）")
    counts = [c.get("execution_count") for c in code_cells if c.get("execution_count") is not None]
    if counts != sorted(counts) or (counts and counts[0] != 1):
        warns.append("cell 的執行順序不是從上到下（建議加 --execute 重新跑一次）")
    errors = [c for c in code_cells for o in c.get("outputs", []) if o.get("output_type") == "error"]
    if errors:
        warns.append(f"有 {len(errors)} 個 cell 的輸出是錯誤訊息")
    widgets = [c for c in code_cells for o in c.get("outputs", [])
               if "application/vnd.jupyter.widget-view+json" in o.get("data", {})]
    if widgets:
        warns.append("有互動元件（例如 sk.explore()），HTML 裡不會顯示，請把產生的程式碼貼到另一個 cell")
    return warns


def export(path, execute=False):
    path = Path(path).resolve()
    if path.suffix.lower() != ".ipynb":
        raise ValueError(f"{path.name} 不是 notebook，請先切換到要匯出的 .ipynb 分頁再執行")
    nb = nbformat.read(path, as_version=4)
    if execute:
        print("重新執行中…")
        ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(
            nb, {"metadata": {"path": str(path.parent)}})
        nbformat.write(nb, path)
    for w in lint(nb, path):
        print("  ⚠", w)
    body, _ = HTMLExporter(embed_images=True).from_notebook_node(nb)
    out = path.with_suffix(".html")
    out.write_text(body, encoding="utf-8")
    print(f"  ✔ 已匯出：{out}（{len(body) // 1024} KB）")
    backup(path, out)
    return out


def backup(nb_path, html_path):
    """把這次的 ipynb 和 html 加上時間戳記複製到同資料夾的 _backup/，改壞了可以拿回上一版。"""
    folder = nb_path.parent / "_backup"
    folder.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for src in (nb_path, html_path):
        shutil.copy2(src, folder / f"{src.stem}_{stamp}{src.suffix}")
    print(f"  ✔ 已備份到：{folder}（{nb_path.stem}_{stamp}.*）")


def choose():
    files = sorted((WORKSPACE / "exam").glob("*.ipynb"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("exam/ 裡沒有 notebook。可以直接把 .ipynb 拖到 3_匯出HTML.bat 上。")
        return []
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    pick = input("要匯出哪一個？（輸入編號，直接 Enter = 1）：").strip() or "1"
    return [files[int(pick) - 1]]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    execute = "--execute" in sys.argv
    targets = [Path(a) for a in args] or choose()
    if targets and not execute and not args:
        execute = input("要先從頭重新執行一次嗎？（建議，y/N）：").strip().lower() == "y"
    for t in targets:
        print(f"\n{t.name}")
        try:
            export(t, execute=execute)
        except Exception as e:
            print(f"  ✗ 失敗：{e}")
