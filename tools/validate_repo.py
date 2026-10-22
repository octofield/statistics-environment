"""檢查 repo 的檔案是否正確（CI 與本機都可以跑）。

    python tools/validate_repo.py            # 全部檢查
    python tools/validate_repo.py --fast     # 不執行 notebook

檢查項目：
- config/ 的 JSONC 設定、tasks、snippets 都能解析；Python snippets 填入預設值後語法正確
- .ps1：有 UTF-8 BOM（Windows PowerShell 5.1 讀中文需要）、PowerShell 語法正確
- .bat / .cmd：只能有 ASCII（cmd 會把多位元組字元切錯位）、CRLF 換行
- .command / .sh：LF 換行、bash 語法正確；setup/、tools/ 的 Python 語法正確
- notes/、templates/ 的 notebook 都能從頭執行
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from sync_vscode_settings import load_jsonc  # noqa: E402

SKIP_DIRS = {".git", "build", "dist", "handouts", "homework", "node_modules", "__pycache__", ".ipynb_checkpoints"}
errors = []


def files(*patterns):
    for pattern in patterns:
        for p in sorted(ROOT.rglob(pattern)):
            if not SKIP_DIRS.intersection(p.relative_to(ROOT).parts):
                yield p


def fail(path, msg):
    errors.append(f"{path.relative_to(ROOT)}: {msg}")


def check_config():
    for p in [*files("config/*.json"), *files("config/*.code-snippets")]:
        try:
            load_jsonc(p)
        except Exception as e:
            fail(p, f"JSON 解析失敗：{e}")
    snippets = load_jsonc(ROOT / "config" / "stat.code-snippets")
    for name, s in snippets.items():
        if not s.get("description"):
            fail(ROOT / "config" / "stat.code-snippets", f"{name} 缺少 description")
        if s.get("scope") == "python":
            text = "\n".join(s["body"])
            text = re.sub(r"\$\{\d+\|([^,|]*)[^|]*\|\}", r"\1", text)
            for _ in range(3):
                text = re.sub(r"\$\{\d+:([^{}]*)\}", r"\1", text)
            text = re.sub(r"\$\d+", "", text).replace("\\}", "}")
            try:
                compile(text, name, "exec")
            except SyntaxError as e:
                fail(ROOT / "config" / "stat.code-snippets", f"{name} 的 Python 語法錯誤：{e}")


def check_scripts():
    ps1 = list(files("*.ps1"))
    for p in ps1:
        if not p.read_bytes().startswith(b"\xef\xbb\xbf"):
            fail(p, "缺少 UTF-8 BOM（Windows PowerShell 5.1 會把中文讀成亂碼）")
    if ps1 and sys.platform == "win32":
        quoted = ",".join("'" + str(p).replace("'", "''") + "'" for p in ps1)
        cmd = ("$bad = 0; foreach ($f in @(" + quoted + ")) { $e = $null; $t = $null; "
               "[void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$t, [ref]$e); "
               "foreach ($x in $e) { $bad++; Write-Output ($f + ':' + $x.Extent.StartLineNumber + ': ' + $x.Message) } }; exit $bad")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
        for line in r.stdout.splitlines():
            errors.append(f"PowerShell 語法錯誤：{line}")
    for p in files("*.bat", "*.cmd"):
        data = p.read_bytes()
        if any(b > 127 for b in data):
            fail(p, "含有非 ASCII 字元（cmd 會解析錯誤，請改成英文）")
        if re.search(rb"(?<!\r)\n", data):
            fail(p, "不是 CRLF 換行（.gitattributes 應該會自動處理，請重新 checkout）")
    bash = shutil.which("bash")
    for p in files("*.command", "*.sh"):
        if b"\r\n" in p.read_bytes():
            fail(p, "不是 LF 換行（bash 遇到 CRLF 會出錯；.gitattributes 應該會自動處理，請重新 checkout）")
        elif bash:
            r = subprocess.run([bash, "-n", str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                fail(p, f"bash 語法錯誤：{r.stderr.strip()[:300]}")
    for p in files("setup/*.py", "tools/*.py"):
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as e:
            fail(p, f"Python 語法錯誤：{e}")


def check_notebooks():
    import os

    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    os.environ["PYTHONPATH"] = str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")
    os.environ.setdefault("MPLBACKEND", "Agg")
    for p in [*files("notes/*.ipynb"), *files("templates/*.ipynb")]:
        try:
            nb = nbformat.read(p, as_version=4)
            nbformat.validate(nb)
            ExecutePreprocessor(timeout=300, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(p.parent)}})
            print(f"  ✔ {p.relative_to(ROOT)}")
        except Exception as e:
            fail(p, f"執行失敗：{str(e).splitlines()[0][:300]}")


if __name__ == "__main__":
    print("檢查設定與 snippets…")
    check_config()
    print("檢查 PowerShell / bat / cmd…")
    check_scripts()
    if "--fast" not in sys.argv:
        print("執行 notebook…")
        check_notebooks()
    if errors:
        print(f"\n{len(errors)} 個問題：")
        for e in errors:
            print("  ✗", e)
        sys.exit(1)
    print("\n全部通過")
