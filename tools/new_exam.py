"""從乾淨的範本建立新考卷：exam/學號_姓名_考試名稱.ipynb。

    python tools/new_exam.py [考試名稱] [--open] [--yes]

建立前會先顯示 tools/student.json 的學號姓名請你確認；不對可以當場改，改完會存回 student.json。
沒給考試名稱會問你（直接 Enter = 期中考）。
--open：用隨身碟的 VS Code 打開新考卷；--yes：不詢問、直接用 student.json 的資料。
由 5_新增考卷.bat 和 VS Code 的「執行工作 → 新增考卷」呼叫。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
TEMPLATE = WORKSPACE / "tools" / "templates" / "exam_template.ipynb"
STUDENT = WORKSPACE / "tools" / "student.json"
DEFAULT_NAME = "期中考"
EXAMPLE = {"id": "B12345678", "name": "王小明"}      # config/student.example.json 的範例值
ID_RE = re.compile(r"^[A-Za-z]\d{8}$")                 # 例如 B12345678


def load_student(student_file=STUDENT):
    if student_file.is_file():
        return json.loads(student_file.read_text(encoding="utf-8"))
    return {}


def save_student(student, student_file=STUDENT):
    student_file.write_text(json.dumps(student, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def ask_student():
    """請使用者輸入學號姓名，學號格式不對會再確認一次。"""
    while True:
        sid = input("請輸入學號（例如 B12345678）：").strip().upper()
        name = input("請輸入姓名：").strip()
        if not sid or not name:
            print("學號和姓名都不能空白，請重新輸入。")
            continue
        if not ID_RE.match(sid) and input(f"學號「{sid}」的格式不是 1 個英文字母 + 8 個數字，確定要用嗎？(y/N)：").strip().lower() != "y":
            continue
        return {"id": sid, "name": name}


def confirm_student(student_file=STUDENT):
    """顯示目前的學號姓名並確認；需要修改時存回 student.json。回傳確認後的資料。"""
    student = load_student(student_file)
    unset = not student.get("id") or not student.get("name") or student == EXAMPLE
    if unset:
        print("還沒有設定學號姓名（目前是範例資料或空白），請先輸入：")
    else:
        print(f"學號：{student['id']}")
        print(f"姓名：{student['name']}")
        if input("以上學號姓名正確嗎？(Y/n)：").strip().lower() not in ("", "y", "yes"):
            unset = True
    if unset:
        student = ask_student()
        save_student(student, student_file)
        print(f"已儲存到 {student_file}，下次就不用再輸入。")
    return student


def create(name, student, exam_dir=WORKSPACE / "exam", template=TEMPLATE):
    """建立新考卷並回傳路徑；同名檔案已存在時加上 _2、_3…，不會覆蓋。"""
    sid, sname = student.get("id", "學號"), student.get("name", "姓名")
    name = name.strip() or DEFAULT_NAME
    base = f"{sid}_{sname}_{name}"
    path, i = exam_dir / f"{base}.ipynb", 2
    while path.exists():
        path, i = exam_dir / f"{base}_{i}.ipynb", i + 1
    text = (template.read_text(encoding="utf-8")
            .replace("{學號}", sid).replace("{姓名}", sname).replace("{考試名稱}", name))
    exam_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def open_in_vscode(path):
    code = WORKSPACE.parent / "VSCode" / "bin" / "code.cmd"
    if code.is_file():
        # -r：VS Code 已經開著就用同一個視窗
        subprocess.Popen(["cmd", "/c", str(code), "-r", str(WORKSPACE), str(path)])
    else:
        print("找不到隨身碟的 VS Code，請自己打開上面的檔案（JupyterLab 在左側檔案瀏覽器 exam/ 裡）")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    student = load_student() if "--yes" in sys.argv else confirm_student()
    name = args[0] if args else input(f"考試名稱（直接 Enter = {DEFAULT_NAME}）：")
    path = create(name, student)
    print(f"已建立：{path}")
    if "--open" in sys.argv:
        open_in_vscode(path)
