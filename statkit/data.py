"""讀考試資料：先速覽、再讀檔。"""
from pathlib import Path

import pandas as pd

_CSV_ENCODINGS = ("utf-8", "utf-8-sig", "cp950")   # cp950 = Big5（Windows 中文 Excel 存的 CSV 常用）


def _read_csv(path):
    last = None
    for enc in _CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc), enc
        except UnicodeDecodeError as e:
            last = e
    raise last


def _columns_table(df):
    rows = []
    for col in df.columns:
        s = df[col]
        sample = s.dropna().head(3).tolist()
        rows.append({"欄位": col, "型態": str(s.dtype), "非空值": int(s.notna().sum()),
                     "缺值": int(s.isna().sum()), "不同值個數": int(s.nunique()),
                     "範例": ", ".join(str(v) for v in sample)})
    return pd.DataFrame(rows).set_index("欄位")


def peek(path, sheet=None, n=5):
    """資料速覽：拿到考試資料時一行看完有哪些工作表、幾列幾欄、欄位型態、缺值、前幾列。

    參數
        path     : 檔案路徑（.xlsx / .xls / .csv），exam/ 裡的 notebook 讀 data/ 要寫 '../data/檔名.xlsx'
        sheet    : Excel 工作表名稱或編號（0 = 第一個）；不給就用第一個
        n        : 顯示前幾列
    回傳
        讀進來的 DataFrame（同時會印出讀檔的程式碼，可以直接貼進答案）
    例
        df = sk.peek('../data/Stat115-1_hw03_data-1.xlsx')
        df = sk.peek('../data/Stat115-1_hw03_data-1.xlsx', sheet='Consumer Food')
    """
    from IPython.display import display

    p = Path(path)
    if not p.exists():
        folder = p.parent if str(p.parent) else Path(".")
        files = sorted(f.name for f in folder.glob("*")) if folder.is_dir() else []
        raise FileNotFoundError(f"找不到 {path}。{folder} 裡有：{files}")

    shown = str(path).replace("\\", "/")      # 程式碼裡用 / 比較好讀，Windows 也能用
    if p.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        with pd.ExcelFile(p) as book:          # 用 with 才會關檔，否則 Windows 上檔案會被鎖住
            names = book.sheet_names
            sheets = {name: book.parse(name) for name in names}
        print(f"工作表（共 {len(names)} 個）：")
        for i, name in enumerate(names):
            r, c = sheets[name].shape
            print(f"  [{i}] {name!r}：{r} 列 × {c} 欄")
        chosen = names[0] if sheet is None else (names[sheet] if isinstance(sheet, int) else sheet)
        df = sheets[chosen]
        code = f"df = pd.read_excel({shown!r}, sheet_name={chosen!r})"
    else:
        df, enc = _read_csv(p)
        code = f"df = pd.read_csv({shown!r}" + ("" if enc == "utf-8" else f", encoding={enc!r}") + ")"
        chosen = None

    print(f"\n{'工作表 ' + repr(chosen) + '：' if chosen is not None else ''}{df.shape[0]} 列 × {df.shape[1]} 欄")
    print(f"讀檔程式碼：{code}\n")
    display(_columns_table(df))
    display(df.head(n))
    return df
