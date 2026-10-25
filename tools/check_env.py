"""考試環境檢查：套件、statkit、中文字型、HTML 匯出、AI 擴充。

由 4_環境檢查.bat 執行；也可以直接 python tools/check_env.py。
"""
import importlib
import os
import shutil
import socket
import sys
import tempfile
import warnings
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
ROOT = WORKSPACE.parent
sys.path.insert(0, str(WORKSPACE))

PACKAGES = ["numpy", "pandas", "matplotlib", "scipy", "sympy", "statsmodels", "openpyxl",
            "seaborn", "ipywidgets", "IPython", "ipykernel", "nbconvert", "nbformat"]
# 精靈可以不裝 JupyterLab；有 2_啟動JupyterLab.bat 才檢查
JUPYTERLAB_PACKAGES = ["jupyterlab", "notebook"]
AI_WORDS = ("copilot", "chatgpt", "openai", "codeium", "tabnine", "continue", "cody", "jupyter-ai",
            "jupyter_ai", "claude", "gemini", "intellicode")

results = []


def report(ok, name, detail=""):
    results.append(ok)
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {name}{'：' + detail if detail else ''}")


def check_packages():
    print(f"Python {sys.version.split()[0]}　（{sys.executable}）")
    has_lab = any(ROOT.glob("2_*.bat"))
    if not has_lab:
        print("[INFO] 沒有安裝 JupyterLab（建立時取消勾選），略過 jupyterlab、notebook")
    for name in PACKAGES + (JUPYTERLAB_PACKAGES if has_lab else []):
        try:
            mod = importlib.import_module(name)
            report(True, name, getattr(mod, "__version__", ""))
        except Exception as e:
            report(False, name, f"無法 import：{e}")
    # uv 產生的執行檔搬到別的位置（複製到隨身碟）就會出現「uv trampoline failed to canonicalize script path」
    if os.name == "nt":
        from fix_launchers import nonportable
        bad = nonportable()
        report(not bad, "命令列執行檔可攜（jupyter、pylsp…複製到隨身碟也能用）",
               f"{', '.join(bad[:8])}{' …' if len(bad) > 8 else ''}；請執行 python workspace\\tools\\fix_launchers.py" if bad else "")
        check_jupyter_subcommand()


def check_jupyter_subcommand():
    """VS Code 匯出 HTML 時執行 `python -m jupyter nbconvert`，jupyter 會在 PATH 上找 jupyter-nbconvert：
    要找到隨身碟的那一個，不能是考場電腦（或自己電腦）上其他 Python 的。"""
    import subprocess
    import sysconfig
    scripts = Path(sysconfig.get_path("scripts")).resolve()
    found = shutil.which("jupyter-nbconvert")
    r = subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--version"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = bool(found) and Path(found).resolve().parent == scripts and r.returncode == 0
    detail = f"用到的是 {found}" if found and Path(found).resolve().parent != scripts else (r.stderr.strip().splitlines() or [""])[-1][:150]
    report(ok, "VS Code 匯出 HTML 會用到隨身碟的 nbconvert", "" if ok else detail)


def check_statkit():
    try:
        from statkit import selftest
        report(selftest.run(verbose=True), "statkit 自我測試")
    except Exception as e:
        report(False, "statkit", repr(e))


def check_font():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import statkit as sk
    font = sk.setup(quiet=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig, ax = plt.subplots()
        ax.set_title("中文標題測試：平均數與標準差")
        fig.canvas.draw()
        plt.close(fig)
    missing = [w for w in caught if "missing" in str(w.message).lower()]
    report(bool(font) and not missing, "中文字型", font or "找不到中文字型")


def export_notebook(nb_path, out_dir):
    """執行一本 notebook 並匯出 HTML，回傳 (ok, 名稱, 說明)。在子程序裡跑，所以不直接 report。"""
    import nbformat
    from nbconvert import HTMLExporter
    from nbconvert.preprocessors import ExecutePreprocessor
    name = f"執行並匯出 {nb_path.relative_to(WORKSPACE)}"
    try:
        nb = nbformat.read(nb_path, as_version=4)
        ExecutePreprocessor(timeout=180, kernel_name="python3").preprocess(
            nb, {"metadata": {"path": str(nb_path.parent)}})
        body, _ = HTMLExporter(embed_images=True).from_notebook_node(nb)
        (out_dir / (nb_path.stem + ".html")).write_text(body, encoding="utf-8")
        return True, name, f"{len(body) // 1024} KB"
    except Exception as e:
        return False, name, (str(e).splitlines() or [repr(e)])[0][:200]


def check_export():
    try:
        import nbformat  # noqa: F401
        from nbconvert import HTMLExporter  # noqa: F401
        from nbconvert.preprocessors import ExecutePreprocessor  # noqa: F401
    except Exception as e:
        report(False, "nbconvert", repr(e))
        return
    targets = [WORKSPACE / "00_索引.ipynb", *sorted((WORKSPACE / "notes").glob("*.ipynb"))]
    for nb_path in targets:
        if not nb_path.exists():
            report(False, f"執行並匯出 {nb_path.name}", "找不到檔案")
    targets = [p for p in targets if p.exists()]
    out_dir = Path(tempfile.mkdtemp(prefix="statexam_"))
    # 每本 notebook 都要開一個 kernel、等它執行完，同時跑幾本會快很多；結果照原本的順序印
    with ProcessPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 1, len(targets)))) as pool:
        for ok, name, detail in pool.map(export_notebook, targets, repeat(out_dir)):
            report(ok, name, detail)
    shutil.rmtree(out_dir, ignore_errors=True)


def check_ai_extensions():
    vs_dir = ROOT / "VSCode"
    if not vs_dir.is_dir():
        print("[INFO] 找不到 VSCode 資料夾（只用 JupyterLab 的話可以忽略）")
        return
    # 使用者安裝的擴充 + VS Code 內建的擴充
    ext_dirs = [vs_dir / "data" / "extensions", *vs_dir.glob("*/resources/app/extensions")]
    found = [p.name for d in ext_dirs if d.is_dir() for p in d.iterdir()
             if p.is_dir() and any(w in p.name.lower() for w in AI_WORDS)]
    report(not found, "VS Code 沒有 AI 擴充", ", ".join(found) if found else "")
    # 在 Mac 上建立的環境：擴充應該已經由 finish_setup.py 裝好
    pending = vs_dir / "data" / "pending-vsix"
    if pending.is_dir():
        left = any(pending.glob("*.vsix"))
        report(not left, "VS Code 擴充已安裝",
               "還有沒裝好的 .vsix，請執行 1_啟動VSCode.bat 或再跑一次環境檢查" if left else "")

    settings_path = vs_dir / "data" / "user-data" / "User" / "settings.json"
    if settings_path.is_file():
        from sync_vscode_settings import AI_PREFIXES, load_jsonc
        settings = load_jsonc(settings_path) or {}
        def disables(v):    # 例如考試設定的 "github.copilot.enable": {"*": false}
            return v is False or (isinstance(v, dict) and v and all(x is False for x in v.values()))
        ai_keys = [k for k, v in settings.items()
                   if k.startswith(AI_PREFIXES) and not k.startswith("chat.") and not disables(v)]
        ok = settings.get("chat.disableAIFeatures") is True and not ai_keys
        detail = "chat.disableAIFeatures 不是 true" if settings.get("chat.disableAIFeatures") is not True else ""
        report(ok, "VS Code 設定已關閉 AI", detail or ", ".join(ai_keys))
    try:
        import importlib.util
        bad = [m for m in ("jupyter_ai", "jupyter_ai_magics") if importlib.util.find_spec(m)]
        report(not bad, "Python 沒有 AI 套件", ", ".join(bad))
    except Exception:
        pass


def check_network():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=1.5).close()
        print("[INFO] 目前有網路。考前演練請把網路關掉再跑一次，確認斷網也能用。")
    except OSError:
        print("[INFO] 目前沒有網路（這正是考試的情況）。")


if __name__ == "__main__":
    version_file = Path(__file__).with_name("VERSION")
    version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "（舊版，沒有版本號）"
    print(f"統計學考試環境 v{version}　（有新版時，用新版的初始化精靈選同一個建立位置再執行一次就能更新）")
    for title, fn in [("套件", check_packages), ("statkit", check_statkit), ("中文字型", check_font),
                      ("HTML 匯出（實際執行 notebook）", check_export), ("AI 擴充", check_ai_extensions),
                      ("網路", check_network)]:
        print(f"\n===== {title} =====")
        fn()
    failed = results.count(False)
    print("\n" + ("全部通過，可以上考場！" if not failed else f"有 {failed} 項沒通過，請看上面的 FAIL。"))
    sys.exit(1 if failed else 0)
