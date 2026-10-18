"""常用統計圖（講義 02a / 02b / 03、HW01–03），預設是講義的淺灰長條、黑框風格。

每個函式都回傳 matplotlib 的 ax，可以再用 ax.set_title(...)、ax.set_xlim(...) 等調整。
"""
import numpy as np
import pandas as pd
from scipy import stats

from ._style import ACCENT, EDGE, FACE, fmt, new_ax
from .desc import _series, freq_table


def hist_classes(x, start=None, width=None, k=None, edges=None, right=False, relative=False,
                 ax=None, xlabel=None, ylabel=None, title=None, show_table=False):
    """依組界畫直方圖（分組跟 sk.freq_table 完全一致）。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        start    : 第一組的下限，例如 0
        width    : 組距，例如 5000
        k        : 組數（可省略，會自動算到涵蓋最大值）
        edges    : 直接指定組界，例如 [160, 164, 168, ...]（給了就不用 start / width）
        right    : False → 組別 [a, b)（作業的寫法）；True → (a, b]
        relative : True → 縱軸畫相對次數；False → 次數
        show_table : True 會一併顯示次數分配表
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        xlabel / ylabel / title : 座標軸名稱、標題（不給就用預設值或資料的欄位名稱）
    回傳
        ax（可以再用 ax.set_title(...) 等調整）
    例
        sk.hist_classes(debt, start=0, width=5000, xlabel='Debt ($)')
    """
    table = freq_table(x, start=start, width=width, k=k, edges=edges, right=right)
    e = table.attrs["edges"]
    ax = new_ax(ax, figsize=(9, 5))
    heights = table["相對次數"] if relative else table["次數"]
    widths = np.diff(e)
    ax.bar(e[:-1], heights, width=widths, align="edge", color=FACE, edgecolor=EDGE)
    ax.set_xticks(e)
    if len(e) > 12:
        ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlabel(xlabel or getattr(x, "name", None) or "Value")
    ax.set_ylabel(ylabel or ("Relative frequency" if relative else "Frequency"))
    if title:
        ax.set_title(title)
    if show_table:
        from IPython.display import display
        display(table)
    return ax


def hist(x, bins=10, normal=False, density=False, ax=None, xlabel=None, ylabel=None, title=None):
    """一般直方圖；normal=True 會疊上同平均數、同標準差的常態曲線，用來判斷是不是鐘形。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        bins     : 組數（整數）或組界（list）
        normal   : True 疊上常態曲線
        density  : True → 縱軸為密度（面積和為 1）；False → 次數
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        xlabel / ylabel / title : 座標軸名稱、標題（不給就用預設值或資料的欄位名稱）
    回傳
        ax
    例
        sk.hist(x, bins=10, normal=True)
    """
    s = _series(x)
    ax = new_ax(ax, figsize=(8, 5))
    counts, edges, _ = ax.hist(s, bins=bins, density=density, color=FACE, edgecolor=EDGE)
    if normal:
        grid = np.linspace(edges[0], edges[-1], 300)
        pdf = stats.norm.pdf(grid, s.mean(), s.std())
        scale = 1 if density else len(s) * np.diff(edges).mean()
        ax.plot(grid, pdf * scale, color=ACCENT, lw=2, label=f"ND({s.mean():.2f}, {s.std():.2f})")
        ax.legend()
    ax.set_xlabel(xlabel or getattr(x, "name", None) or "Value")
    ax.set_ylabel(ylabel or ("Density" if density else "Frequency"))
    if title:
        ax.set_title(title)
    return ax


def ogive(x, start=None, width=None, k=None, edges=None, right=False, relative=True,
          ax=None, xlabel=None, title=None):
    """肩形圖（累積次數折線圖）。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        start    : 第一組的下限，例如 0
        width    : 組距，例如 5000
        k        : 組數（可省略，會自動算到涵蓋最大值）
        edges    : 直接指定組界，例如 [160, 164, 168, ...]（給了就不用 start / width）
        right    : False → 組別 [a, b)（作業的寫法）；True → (a, b]
        relative : True → 累積相對次數（0～1）；False → 累積次數
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        xlabel / title : 橫軸名稱、標題
    回傳
        ax
    例
        sk.ogive(debt, start=0, width=5000)
    """
    table = freq_table(x, start=start, width=width, k=k, edges=edges, right=right)
    e = table.attrs["edges"]
    col = "累積相對次數" if relative else "累積次數"
    ys = [0, *table[col]]
    ax = new_ax(ax, figsize=(8, 5))
    ax.plot(e, ys, marker="o", color=EDGE)
    ax.set_xticks(e)
    ax.set_xlabel(xlabel or getattr(x, "name", None) or "Value")
    ax.set_ylabel("Cumulative relative frequency" if relative else "Cumulative frequency")
    if title:
        ax.set_title(title)
    return ax


def box(data, labels=None, vert=True, showmeans=False, ax=None, ylabel=None, title=None):
    """盒鬚圖，可以多組並排比較。

    參數
        data     : 一組資料、多組資料的 list、dict（鍵當標籤）或 DataFrame（每欄一組）
        labels   : 每組的名稱，例如 ['Food', 'Income']
        vert     : True 直的；False 橫的
        showmeans : True 另外標出平均數
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        ylabel / title : 數值軸名稱、標題
    回傳
        ax
    例
        sk.box([food, income, debt], labels=['Food', 'Income', 'Debt'])
    """
    if isinstance(data, pd.DataFrame):
        labels = labels or list(data.columns)
        groups = [_series(data[c]) for c in data.columns]
    elif isinstance(data, dict):
        labels = labels or list(data.keys())
        groups = [_series(v) for v in data.values()]
    elif isinstance(data, (list, tuple)) and data and np.ndim(data[0]) > 0:
        groups = [_series(v) for v in data]
    else:
        groups = [_series(data)]
    labels = labels or [getattr(g, "name", None) or str(i + 1) for i, g in enumerate(groups)]
    ax = new_ax(ax, figsize=(max(5, 2.2 * len(groups)), 5))
    kw = dict(vert=vert, showmeans=showmeans, widths=0.4,
              medianprops=dict(color=EDGE), boxprops=dict(color=EDGE))
    try:
        ax.boxplot(groups, tick_labels=labels, **kw)
    except TypeError:          # matplotlib < 3.9
        ax.boxplot(groups, labels=labels, **kw)
    if ylabel:
        (ax.set_ylabel if vert else ax.set_xlabel)(ylabel)
    if title:
        ax.set_title(title)
    return ax


def scatter_r(x, y, fit=False, ax=None, xlabel=None, ylabel=None, title=None):
    """散佈圖，標題附上相關係數 r；fit=True 會畫最小平方迴歸線並印出方程式。

    參數
        x, y     : 兩組成對的資料（x 在橫軸、y 在縱軸）
        fit      : True 畫迴歸線 ŷ = a + b x
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        xlabel / ylabel / title : 座標軸名稱、標題（不給就用預設值或資料的欄位名稱）
    回傳
        ax
    例
        sk.scatter_r(df['Income'], df['Food'], fit=True)
    """
    a, b = _series(x), _series(y)
    r = a.corr(b)
    ax = new_ax(ax, figsize=(7, 6))
    ax.scatter(a, b, facecolors="none", edgecolors=EDGE)
    xl = xlabel or getattr(x, "name", None) or "x"
    yl = ylabel or getattr(y, "name", None) or "y"
    if fit:
        slope, intercept = np.polyfit(a, b, 1)
        grid = np.linspace(a.min(), a.max(), 100)
        ax.plot(grid, intercept + slope * grid, color=ACCENT, lw=2)
        print(f"迴歸線：ŷ = {intercept:.4f} + {slope:.4f} x")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.set_title(title or f"{yl} vs {xl} (r = {r:.3f})")
    return ax


def _counts(categories, values, sort):
    if values is None:
        s = pd.Series(categories).value_counts(sort=False)
    else:
        s = pd.Series(list(values), index=list(categories))
    if sort:
        s = s.sort_values(ascending=False)
    return s


def bar(categories, values=None, sort=False, horizontal=False, ax=None, xlabel=None, ylabel=None, title=None):
    """長條圖。只給 categories（原始類別資料）會自動計次；也可以給 categories + values。

    參數
        categories : 類別資料（例如 ['A', 'B', 'A', ...]），或類別名稱
        values   : 每個類別的數值（可省略，省略就自動計次）
        sort     : True 由大到小排序
        horizontal : True 畫橫條圖
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        xlabel / ylabel / title : 座標軸名稱、標題（不給就用預設值或資料的欄位名稱）
    回傳
        ax
    例
        sk.bar(df['Region'])
        sk.bar(['A', 'B', 'C'], [10, 15, 12])
    """
    s = _counts(categories, values, sort)
    ax = new_ax(ax, figsize=(max(6, 0.8 * len(s)), 5))
    if horizontal:
        ax.barh(s.index.astype(str), s.values, color=FACE, edgecolor=EDGE)
    else:
        ax.bar(s.index.astype(str), s.values, color=FACE, edgecolor=EDGE)
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel or ("Frequency" if values is None else ""))
    if title:
        ax.set_title(title)
    return ax


def pie(categories, values=None, ax=None, title=None):
    """圓餅圖，標示百分比。

    參數
        categories : 類別資料或類別名稱
        values   : 每個類別的數值（可省略，省略就自動計次）
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        title    : 標題
    回傳
        ax
    例
        sk.pie(df['Region'])
    """
    s = _counts(categories, values, sort=False)
    ax = new_ax(ax, figsize=(6, 6))
    ax.pie(s.values, labels=s.index.astype(str), autopct="%1.1f%%", startangle=90, counterclock=False,
           wedgeprops=dict(edgecolor="white"))
    ax.set_aspect("equal")
    if title:
        ax.set_title(title)
    return ax


def pareto(categories, values=None, ax=None, ylabel="Frequency", title=None):
    """柏拉圖：由大到小的長條 + 累積百分比折線（右側座標軸）。

    參數
        categories : 類別資料或類別名稱
        values   : 每個類別的數值（可省略，省略就自動計次）
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        ylabel / title : 左側座標軸名稱、標題
    回傳
        ax（左側長條圖的座標軸）
    例
        sk.pareto(grades)
    """
    s = _counts(categories, values, sort=True)
    ax = new_ax(ax, figsize=(max(6, 0.8 * len(s)), 5))
    labels = s.index.astype(str)
    ax.bar(labels, s.values, color=FACE, edgecolor=EDGE)
    ax.set_ylabel(ylabel)
    ax2 = ax.twinx()
    ax2.plot(labels, s.cumsum() / s.sum() * 100, color=ACCENT, marker="o")
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("Cumulative %")
    if title:
        ax.set_title(title)
    return ax


def stem_leaf(x, stem_unit=10, leaf_unit=1):
    """文字版莖葉圖（只支援非負數）。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        stem_unit : 莖的單位，例如 10 → 172 的莖是 17
        leaf_unit : 葉的單位，例如 1 → 172 的葉是 2；資料有小數可以用 0.1
    回傳
        無（直接印出）
    例
        sk.stem_leaf(values, stem_unit=10)
    """
    s = _series(x)
    if (s < 0).any():
        raise ValueError("莖葉圖目前只支援非負數")
    m = round(stem_unit / leaf_unit)
    scaled = sorted(int(round(v / leaf_unit)) for v in s)
    stems = {}
    for v in scaled:
        stems.setdefault(v // m, []).append(v % m)
    lo, hi = min(stems), max(stems)
    width = len(str(hi))
    print(f"莖 | 葉　（莖單位 = {fmt(stem_unit)}，葉單位 = {fmt(leaf_unit)}）")
    for st in range(lo, hi + 1):
        leaves = " ".join(str(l) for l in stems.get(st, []))
        print(f"{st:>{width}} | {leaves}")


def qq_plot(x, ax=None, title="Normal Q-Q plot"):
    """常態 Q-Q 圖：點越接近直線，資料越接近常態分布。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        title    : 標題
    回傳
        ax
    例
        sk.qq_plot(df['Income'])
    """
    s = _series(x)
    ax = new_ax(ax, figsize=(6, 6))
    (osm, osr), (slope, intercept, _) = stats.probplot(s, dist="norm")
    ax.scatter(osm, osr, facecolors="none", edgecolors=EDGE)
    ax.plot(osm, intercept + slope * np.asarray(osm), color=ACCENT, lw=2)
    ax.set_xlabel("Theoretical quantiles")
    ax.set_ylabel("Sample quantiles")
    ax.set_title(title)
    return ax
