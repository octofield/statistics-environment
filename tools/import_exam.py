"""匯入老師給的考卷：把 .ipynb 複製到 exam/（保留原檔名），在最上面加上 import 與初始設定，再打開。

    python tools/import_exam.py [考卷.ipynb ...] [--open]

沒給檔案時會跳出選檔視窗（預設開在「下載」資料夾）；也可以把檔案拖到 5_匯入考卷.bat 上。
不會幫你填學號姓名，只會提醒；匯出 HTML 時如果考卷裡找不到你的學號會再提醒一次。
exam/ 裡已經有同名的考卷時不會覆蓋，會問你要打開已經有的，還是另存一份。
由 5_匯入考卷.bat 和 VS Code 的「執行工作 → 匯入考卷」呼叫。
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import nbformat

WORKSPACE = Path(__file__).resolve().parent.parent
EXAM_DIR = WORKSPACE / "exam"
STUDENT = WORKSPACE / "tools" / "student.json"
EXAMPLE = {"id": "B12345678", "name": "王小明"}      # config/student.example.json 的範例值
ID_RE = re.compile(r"^[A-Za-z]\d{8}$")                 # 例如 B12345678

SETUP_MARK = "# 考試環境的 import 與設定（匯入考卷時自動加上）"
SETUP_CELL = f"""{SETUP_MARK}
import math
import random
import statistics

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sympy as sp
from scipy import stats

import statkit as sk
sk.setup()  # 字體大小 16、中文字型"""


# ------------------------------------------------------------------ 學號姓名（只用來提醒與匯出檢查）
def load_student(student_file=STUDENT):
    """回傳 student.json 的學號姓名；還沒設定（空白或範例資料）時回傳 {}。"""
    try:
        student = json.loads(student_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not student.get("id") or not student.get("name") or student == EXAMPLE:
        return {}
    return student


def save_student(student, student_file=STUDENT):
    student_file.write_text(json.dumps(student, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def ask_student():
    """請使用者輸入學號姓名（直接 Enter 略過），學號格式不對會再確認一次。"""
    while True:
        sid = input("請輸入學號（例如 B12345678；直接 Enter 略過）：").strip().upper()
        if not sid:
            return {}
        name = input("請輸入姓名：").strip()
        if not name:
            print("姓名不能空白，請重新輸入。")
            continue
        if not ID_RE.match(sid) and input(f"學號「{sid}」的格式不是 1 個英文字母 + 8 個數字，確定要用嗎？(y/N)：").strip().lower() != "y":
            continue
        return {"id": sid, "name": name}


# ------------------------------------------------------------------ 選檔
def downloads_dir():
    """「下載」資料夾（使用者搬過位置也找得到），找不到就用家目錄。"""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            from uuid import UUID

            class GUID(ctypes.Structure):
                _fields_ = [("data", ctypes.c_byte * 16)]

            guid = GUID()
            ctypes.memmove(guid.data, UUID("{374DE290-123F-4565-9164-39C4925E467B}").bytes_le, 16)  # FOLDERID_Downloads
            path = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path)) == 0:
                result = Path(path.value)
                ctypes.windll.ole32.CoTaskMemFree(path)
                if result.is_dir():
                    return result
        except Exception:
            pass
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / "Downloads" if (home / "Downloads").is_dir() else home


def pick_files():
    """跳出選檔視窗（置頂，只顯示 .ipynb），回傳選到的檔案 list；取消回傳 []。"""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    paths = filedialog.askopenfilenames(parent=root, title="選擇老師給的考卷（.ipynb）",
                                        initialdir=str(downloads_dir()),
                                        filetypes=[("Jupyter Notebook", "*.ipynb"), ("所有檔案", "*.*")])
    root.destroy()
    return [Path(p) for p in paths]


# ------------------------------------------------------------------ 匯入
def add_setup_cell(nb):
    """在最上面加上 import 與初始設定（已經有 import statkit 的話不加）。回傳有沒有加。"""
    if any(c.cell_type == "code" and "import statkit" in c.source for c in nb.cells):
        return False
    nb.cells.insert(0, nbformat.v4.new_code_cell(SETUP_CELL))
    nb.metadata.setdefault("kernelspec", {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"})
    return True


def free_name(path):
    """原檔名_2.ipynb、原檔名_3.ipynb…中第一個還沒用過的。"""
    i = 2
    while (candidate := path.with_name(f"{path.stem}_{i}{path.suffix}")).exists():
        i += 1
    return candidate


def import_exam(src, exam_dir=EXAM_DIR, ask=input):
    """把 src 匯入 exam_dir（保留原檔名）並加上 setup cell，回傳匯入後的路徑。

    已經在 exam_dir 裡的檔案直接處理；exam_dir 有同名檔案時用 ask 問要打開舊的還是另存。
    """
    src = Path(src).resolve()
    if src.suffix.lower() != ".ipynb":
        raise ValueError(f"{src.name} 不是 .ipynb 檔")
    exam_dir.mkdir(parents=True, exist_ok=True)
    if src.parent == exam_dir.resolve():
        dst = src
    else:
        dst = exam_dir / src.name
        if dst.exists():
            answer = ask(f"exam\\ 裡已經有 {dst.name}（可能是你已經在寫的考卷）。\n"
                         f"直接 Enter = 打開已經有的那份；輸入 n = 另存一份新的：").strip().lower()
            if answer not in ("n", "no"):
                return dst
            dst = free_name(dst)
        shutil.copy2(src, dst)
    nb = nbformat.read(dst, as_version=4)
    if add_setup_cell(nb):
        nbformat.write(nb, dst)
    return dst


def open_in_vscode(path):
    code = WORKSPACE.parent / "VSCode" / "bin" / "code.cmd"
    if code.is_file():
        # -r：VS Code 已經開著就用同一個視窗
        env = {k: v for k, v in os.environ.items() if k != "ELECTRON_RUN_AS_NODE"}
        subprocess.Popen(["cmd", "/c", str(code), "-r", str(WORKSPACE), str(path)], env=env)
    else:
        print("找不到隨身碟的 VS Code，請用 2_啟動JupyterLab.bat，在左側檔案瀏覽器的 exam/ 裡打開它")


def main(argv):
    files = [Path(a) for a in argv if not a.startswith("--")]
    if not files:
        print("請在跳出的視窗選擇老師給的考卷（.ipynb；從 COOL 下載的通常在「下載」資料夾）…")
        files = pick_files()
        if not files:
            print("沒有選擇檔案。")
            return 1
    imported = []
    for f in files:
        try:
            path = import_exam(f)
        except (OSError, ValueError) as e:
            print(f"✖ {f.name}：{e}")
            continue
        imported.append(path)
        print(f"✔ 考卷在：{path}")
    if not imported:
        return 1

    student = load_student()
    if not student:
        print("\n還沒有設定學號姓名（只用來提醒你、以及匯出 HTML 時檢查考卷裡有沒有寫）。")
        student = ask_student()
        if student:
            save_student(student)
    if student:
        print(f"\n★ 記得依老師的格式在考卷裡寫上：學號 {student['id']}、姓名 {student['name']}")
    else:
        print("\n★ 記得依老師的格式在考卷裡寫上學號、姓名")
    print("  最上面那一格是 import 與初始設定，請先執行它。")
    if "--open" in argv:
        for path in imported:
            open_in_vscode(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
