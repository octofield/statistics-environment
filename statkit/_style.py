"""繪圖與顯示的共用設定。"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

# 課程講義的配色：淺灰長條、黑框
FACE = "lightgrey"
EDGE = "black"
HIGHLIGHT = "#2a78d6"   # 機率區間塗色
ACCENT = "#eb6834"      # 對照線（常態曲線、平均數等）

_FONT_DIRS = [Path(__file__).resolve().parent.parent / "fonts"]
_CJK_CANDIDATES = ["Microsoft JhengHei", "Noto Sans TC", "Noto Sans CJK TC",
                   "Microsoft YaHei", "PMingLiU", "MingLiU"]


def _register_bundled_fonts():
    for d in _FONT_DIRS:
        if not d.is_dir():
            continue
        for f in [*d.glob("*.ttf"), *d.glob("*.otf"), *d.glob("*.ttc")]:
            try:
                font_manager.fontManager.addfont(str(f))
            except Exception:
                pass


def _pick_cjk_font():
    installed = {f.name for f in font_manager.fontManager.ttflist}
    return next((n for n in _CJK_CANDIDATES if n in installed), None)


def setup(size=16, dpi=100, cjk=True, quiet=False):
    """套用課程作業的圖表設定，並設定中文字型。每份 notebook 開頭執行一次。

    參數
        size     : 所有文字的字體大小（作業用 16；圖太擠可以改 12）
        dpi      : 圖的解析度，越大圖越大（預設 100）
        cjk      : 是否設定中文字型（先找微軟正黑體，找不到用隨身碟 fonts/ 內的字型）
        quiet    : True 不印出設定結果
    回傳
        使用的中文字型名稱（找不到為 None）
    例
        sk.setup()
        sk.setup(size=12, dpi=120)
    """
    rc = plt.rcParams
    rc["figure.dpi"] = dpi
    rc["figure.autolayout"] = True
    for key in ("font.size", "axes.titlesize", "axes.labelsize",
                "xtick.labelsize", "ytick.labelsize"):
        rc[key] = size
    rc["legend.fontsize"] = size * 0.8
    rc["axes.unicode_minus"] = False

    font = None
    if cjk:
        _register_bundled_fonts()
        font = _pick_cjk_font()
        if font:
            # 直接列在 font.family 才會逐字 fallback（微軟正黑體沒有 ≥ ≤ 等符號，改用 DejaVu Sans）
            rc["font.family"] = [font, "DejaVu Sans"]

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)
    pd.set_option("display.max_rows", 200)

    if not quiet:
        print(f"statkit 已設定：字體大小={size}, dpi={dpi}, 中文字型={font or '（找不到，中文可能變方塊）'}")
    return font


def fmt(v, digits=10):
    """數字轉成程式碼裡好看的寫法：整數就不加小數點；算式（例如 25/60）照原樣。"""
    if getattr(v, "src", None):
        return v.src
    try:
        f = float(v)
    except (TypeError, ValueError):
        return repr(v)
    if f.is_integer() and abs(f) < 1e15:
        return str(int(f))
    return f"{f:.{digits}g}"


def new_ax(ax=None, figsize=None):
    if ax is not None:
        return ax
    _, ax = plt.subplots(figsize=figsize)
    return ax
