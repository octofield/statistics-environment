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


def check_import_exam():
    """匯入考卷：保留原檔名、setup cell 在標題之後且只加一次、原本的 cell 不動、同名檔案不覆蓋、資料檔一起複製。"""
    import tempfile

    import nbformat
    sys.path.insert(0, str(ROOT / "tools"))
    import import_exam

    src_file = ROOT / "tools" / "import_exam.py"
    quiet = {"report": lambda _: None}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        title, code = "# Midterm\n\nStudent ID:", "df = pd.read_excel('midterm_data.xlsx')"
        teacher = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(title),
                                                   nbformat.v4.new_code_cell(code)])
        nbformat.write(teacher, tmp / "Stat115_midterm.ipynb")
        (tmp / "midterm_data.xlsx").write_bytes(b"fake")
        exam = tmp / "exam"
        first = import_exam.import_exam(tmp / "Stat115_midterm.ipynb", exam, ask=lambda _: "", **quiet)
        nb = nbformat.read(first, as_version=4)
        setup = [c for c in nb.cells if import_exam.SETUP_MARK in c.source]
        if first.name != "Stat115_midterm.ipynb":
            fail(src_file, f"沒有保留原檔名：{first.name}")
        if len(setup) != 1 or nb.cells[1] is not setup[0]:
            fail(src_file, "setup cell 沒有加在標題（第一個 markdown cell）之後")
        if [c.source for c in nb.cells if c is not setup[0]] != [title, code]:
            fail(src_file, "原本的 cell 被改動了")
        if not (exam / "midterm_data.xlsx").is_file():
            fail(src_file, "考卷用到的資料檔沒有一起複製到 exam/")
        # 學生已經開始作答後又匯入一次：Enter → 打開原本那份（不覆蓋）；n → 另存 _2
        nb.cells.append(nbformat.v4.new_code_cell("answer = 42"))
        nbformat.write(nb, first)
        again = import_exam.import_exam(tmp / "Stat115_midterm.ipynb", exam, ask=lambda _: "", **quiet)
        if again != first or "answer = 42" not in again.read_text(encoding="utf-8"):
            fail(src_file, "同名考卷被覆蓋了")
        copy = import_exam.import_exam(tmp / "Stat115_midterm.ipynb", exam, ask=lambda _: "n", **quiet)
        if copy.name != "Stat115_midterm_2.ipynb":
            fail(src_file, f"另存的檔名不對：{copy.name}")
        # 已經在 exam/ 裡的檔案：原地處理，setup cell 不會重複加
        import_exam.import_exam(first, exam, ask=lambda _: "", **quiet)
        if sum(import_exam.SETUP_MARK in c.source for c in nbformat.read(first, as_version=4).cells) != 1:
            fail(src_file, "setup cell 重複加了")
    if not re.fullmatch(r"\d+\.\d+\.\d+", (ROOT / "VERSION").read_text(encoding="utf-8").strip()):
        fail(ROOT / "VERSION", "版本號要是 X.Y.Z 的格式")


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
    print("檢查匯入考卷、版本號…")
    check_import_exam()
    if "--fast" not in sys.argv:
        print("執行 notebook…")
        check_notebooks()
    if errors:
        print(f"\n{len(errors)} 個問題：")
        for e in errors:
            print("  ✗", e)
        sys.exit(1)
    print("\n全部通過")
