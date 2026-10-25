"""常用統計圖（講義 02a / 02b / 03、HW01–03），預設是講義的淺灰長條、黑框風格。

每個函式都回傳 matplotlib 的 ax，可以再用 ax.set_title(...)、ax.set_xlim(...) 等調整。
"""
import numpy as np
import pandas as pd
from scipy import stats

from ._style import ACCENT, EDGE, FACE, fmt, new_ax
from .desc import _series, freq_table


def hist_classes(x, start=None, width=None, k=None, edges=None, right=False, relative=False,
                 ax=None, xlabel=None, ylabel=None, title=None, show_table=False, fit=None, density=False):
    """依組界畫直方圖（分組跟 sk.freq_table 完全一致），可以疊上分布曲線（HW07：看資料像哪個分布）。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        start    : 第一組的下限，例如 0
        width    : 組距，例如 5000
        k        : 組數（可省略，會自動算到涵蓋最大值）
        edges    : 直接指定組界，例如 [160, 164, 168, ...]（給了就不用 start / width）
        right    : False → 組別 [a, b)（作業的寫法）；True → (a, b]
        relative : True → 縱軸畫相對次數；False → 次數
        density  : True → 縱軸畫密度（相對次數 ÷ 組距，面積和為 1，可以直接跟 pdf 比）
        fit      : 疊上分布曲線：'norm' → 用樣本平均數、樣本標準差的常態；
                   也可以直接給分布，例如 sk.Normal(70, 10)、sk.Expon(0.5)。曲線會依縱軸自動縮放
        show_table : True 會一併顯示次數分配表
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        xlabel / ylabel / title : 座標軸名稱、標題（不給就用預設值或資料的欄位名稱）
    回傳
        ax（可以再用 ax.set_title(...) 等調整）
    例
        sk.hist_classes(debt, start=0, width=5000, xlabel='Debt ($)')
        sk.hist_classes(x, start=-20, width=15, k=12, density=True, fit='norm')
    """
    table = freq_table(x, start=start, width=width, k=k, edges=edges, right=right)
    e = table.attrs["edges"]
    ax = new_ax(ax, figsize=(9, 5))
    widths = np.diff(e)
    if density:
        heights = table["次數"] / table["次數"].sum() / widths
    else:
        heights = table["相對次數"] if relative else table["次數"]
    ax.bar(e[:-1], heights, width=widths, align="edge", color=FACE, edgecolor=EDGE,
           label="Data" if fit is not None else None)
    ax.set_xticks(e)
    if len(e) > 12:
        ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlabel(xlabel or getattr(x, "name", None) or "Value")
    ax.set_ylabel(ylabel or ("Density" if density else "Relative frequency" if relative else "Frequency"))
    if fit is not None:
        _overlay_fit(ax, _series(x), fit, e, density=density, relative=relative)
    if title:
        ax.set_title(title)
    if show_table:
        from IPython.display import display
        display(table)
    return ax


def _overlay_fit(ax, s, fit, edges, density=False, relative=False):
    """在直方圖上疊分布曲線，並印出課程寫法。縱軸是次數時，pdf 要乘上「資料筆數 × 組距」。"""
    from .dist import Normal, _as_dist
    if isinstance(fit, str):
        if fit != "norm":
            raise ValueError("fit 目前只支援 'norm'，其他分布請直接給分布物件，例如 fit=sk.Expon(0.5)")
        d = Normal(s.mean(), s.std())
        how = f"樣本平均數 {s.mean():.4f}、樣本標準差 {s.std():.4f}"
    else:
        d, how = _as_dist(fit), "指定的參數"
    w = float(np.mean(np.diff(edges)))
    scale = 1 if density else (w if relative else len(s) * w)
    grid = np.linspace(edges[0], edges[-1], 400)
    if d.discrete:
        ks = np.arange(int(np.ceil(edges[0])), int(np.floor(edges[-1])) + 1)
        ax.plot(ks, d.frozen.pmf(ks) * scale, "o-", color=ACCENT, lw=2, label=d.label)
    else:
        ax.plot(grid, d.frozen.pdf(grid) * scale, color=ACCENT, lw=2, label=d.label)
    ax.legend()
    print(f"疊上 {d.label}（{how}）")
    factor = "" if density else (f" * {fmt(w)}" if relative else f" * {len(s)} * {fmt(w)}")
    if d.discrete:
        grid_line = f"  xs = np.arange({int(np.ceil(edges[0]))}, {int(np.floor(edges[-1])) + 1})   # 整數點"
        curve = f"plt.plot(xs, {d.code('pmf', 'k', 'xs')}{factor}, 'o-', color='red', label='{d.label}')"
    else:
        grid_line = f"  xs = np.linspace({fmt(edges[0])}, {fmt(edges[-1])}, 300)   # 起點、終點、取幾個點"
        kw = "loc=x.mean(), scale=x.std()" if isinstance(fit, str) else d.kw
        curve = f"plt.plot(xs, stats.{d.name}.pdf(xs, {kw}){factor}, color='red', label='{d.label}')"
    print("課程寫法（疊圖）：\n"
          f"  plt.hist(x, bins=endpoints{', density=True' if density else ''}, facecolor='lightgrey', edgecolor='black', label='Data')\n"
          f"{grid_line}\n  {curve}\n  plt.legend()"
          + ("" if density else "\n  （縱軸是次數，所以 pdf 要乘上 資料筆數 × 組距；用 density=True 就不用乘）"))


def freq_polygon(x, start=None, width=None, k=None, edges=None, right=False, relative=False,
                 ax=None, xlabel=None, ylabel=None, title=None, with_hist=False):
    """次數多邊形（講義 02a）：把每一組的組中點和次數連成折線，兩端各接一個次數為 0 的點。

    參數
        x, start, width, k, edges, right : 分組方式，跟 sk.freq_table 一樣
        relative : True → 縱軸畫相對次數
        with_hist : True 先畫直方圖再疊上折線
        ax       : 畫在哪個子圖；不給就開一張新圖
        xlabel / ylabel / title : 座標軸名稱、標題
    回傳
        ax
    例
        sk.freq_polygon(values, start=160, width=4, with_hist=True)
    """
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        table = freq_table(x, start=start, width=width, k=k, edges=edges, right=right)
    e = table.attrs["edges"]
    w = e[1] - e[0]
    ys = list(table["相對次數"] if relative else table["次數"])
    mids = list(table["組中點"])
    xs_line = [mids[0] - w] + mids + [mids[-1] + w]
    ys_line = [0] + ys + [0]
    if with_hist:
        ax = hist_classes(x, edges=e, right=right, relative=relative, ax=ax)
    ax = new_ax(ax, figsize=(9, 5))
    ax.plot(xs_line, ys_line, marker="o", color=ACCENT if with_hist else EDGE, lw=2)
    ax.set_xlabel(xlabel or getattr(x, "name", None) or "Value")
    ax.set_ylabel(ylabel or ("Relative frequency" if relative else "Frequency"))
    if title:
        ax.set_title(title)
    print("課程寫法：組中點 mids、次數 counts → plt.plot([mids[0] - 組距] + mids + [mids[-1] + 組距], [0] + counts + [0], marker='o')")
    return ax


def tidy(ax=None, thousands=False, grid=True, bar_labels=False, legend=None, rotate=None, show_code=True):
    """一行讓圖更好看（講義 02b 的原則）：去掉上、右框線、淡格線、千分位、長條上標數值。

    參數
        ax         : 要調整的圖（sk 的畫圖函式會回傳 ax）；不給就用目前這張
        thousands  : True → 縱軸數字加千分位逗號（例如 12,000）；'x' → 橫軸；'both' → 兩個都加
        grid       : True → 加上淡淡的水平格線，方便讀數字
        bar_labels : True → 在每根長條上標數值（長條圖用）；也可以給格式，例如 '{:.1f}'
        legend     : 圖例位置，例如 'upper left'、'best'；None 不動
        rotate     : 橫軸刻度旋轉幾度，例如 45（類別名稱太長時）
        show_code  : True → 印出等價的課程寫法
    回傳
        ax
    例
        ax = sk.bar(df['Region'])
        sk.tidy(ax, bar_labels=True)
    """
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    ax = ax or plt.gca()
    code = []
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    code.append("ax.spines[['top', 'right']].set_visible(False)        # 去掉上、右框線")
    if grid:
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        code.append("ax.grid(axis='y', alpha=0.3); ax.set_axisbelow(True)  # 淡格線、放在長條後面")
    if thousands:
        f = FuncFormatter(lambda v, _: f"{v:,.0f}")
        if thousands in (True, "y", "both"):
            ax.yaxis.set_major_formatter(f)
        if thousands in ("x", "both"):
            ax.xaxis.set_major_formatter(f)
        code.append("ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:,.0f}'))   # 千分位")
    if bar_labels:
        fmt_ = bar_labels if isinstance(bar_labels, str) else "{:,.0f}"
        for c in ax.containers:
            ax.bar_label(c, fmt=fmt_, padding=2, fontsize="small")
        code.append(f"ax.bar_label(ax.containers[0], fmt='{fmt_}', padding=2)   # 長條上標數值")
    if legend:
        ax.legend(loc=legend, frameon=False)
        code.append(f"ax.legend(loc='{legend}', frameon=False)")
    if rotate:
        for t in ax.get_xticklabels():
            t.set_rotation(rotate)
            t.set_ha("right")
        code.append(f"plt.xticks(rotation={rotate}, ha='right')")
    if show_code:
        print("課程寫法（ax = plt.gca()；千分位要 from matplotlib.ticker import FuncFormatter）：\n  " + "\n  ".join(code))
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
    kw = dict(showmeans=showmeans, widths=0.4, medianprops=dict(color=EDGE), boxprops=dict(color=EDGE))
    try:                       # matplotlib ≥ 3.10：vert 要改成 orientation
        ax.boxplot(groups, tick_labels=labels, orientation="vertical" if vert else "horizontal", **kw)
    except TypeError:
        try:                   # matplotlib 3.9
            ax.boxplot(groups, tick_labels=labels, vert=vert, **kw)
        except TypeError:      # matplotlib < 3.9
            ax.boxplot(groups, labels=labels, vert=vert, **kw)
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


# ------------------------------------------------------------------ 多個變數（講義 02a、HW02 / HW03）

def scatter_matrix(df, cols=None, ncols=3):
    """多個變數兩兩畫散佈圖（每個子圖標題附 r），一次看出誰跟誰有關。

    參數
        df       : DataFrame
        cols     : 要畫的欄位，例如 ['Food', 'Income', 'Debt']；不給就用所有數值欄位
        ncols    : 每列放幾張子圖
    回傳
        axes（子圖的 list）
    例
        sk.scatter_matrix(df, ['Food', 'Income', 'Debt'])
    """
    import matplotlib.pyplot as plt
    from itertools import combinations

    from .desc import _numeric_cols

    cols = _numeric_cols(df, cols)
    pairs = list(combinations(cols, 2))
    if not pairs:
        raise ValueError("至少要兩個欄位")
    ncols = min(ncols, len(pairs))
    nrows = -(-len(pairs) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows), squeeze=False)
    axes = list(axes.flat)
    for ax, (x, y) in zip(axes, pairs):
        d = df[[x, y]].dropna()                 # 兩欄一起去掉缺值，才不會錯位
        scatter_r(d[x], d[y], ax=ax)
    for ax in axes[len(pairs):]:
        ax.set_visible(False)
    return axes[:len(pairs)]


def scatter_by(df, x, y, by, ax=None, xlabel=None, ylabel=None, title=None):
    """散佈圖，依類別上不同顏色並加圖例，同時印出每一組的相關係數 r。

    參數
        df       : DataFrame
        x, y     : 橫軸、縱軸的欄位名稱
        by       : 分組的類別欄位，例如 'Region'
        ax       : 畫在哪個子圖；不給就開一張新圖
        xlabel / ylabel / title : 座標軸名稱、標題
    回傳
        ax
    例
        sk.scatter_by(df, 'Debt', 'Food', by='Region')
    """
    ax = new_ax(ax, figsize=(8, 6))
    for name, g in df.groupby(by):
        g = g[[x, y]].dropna()
        ax.scatter(g[x], g[y], label=str(name), alpha=0.8)
        r = g[x].corr(g[y]) if len(g) >= 2 else float("nan")
        print(f"{by} = {name}：n = {len(g)}，r = {r:.4f}")
    print(f"全部：r = {df[x].corr(df[y]):.4f}")
    ax.legend(title=str(by))
    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)
    ax.set_title(title or f"{y} vs {x} by {by}")
    return ax


def box_by(df, value, by, showmeans=False, ax=None, ylabel=None, title=None):
    """依類別分組畫盒鬚圖（例如各地區的食物支出）。

    參數
        df       : DataFrame
        value    : 數值欄位，例如 'Food'
        by       : 分組的類別欄位，例如 'Region'
        showmeans : True 另外標出平均數
        ax       : 畫在哪個子圖；不給就開一張新圖
        ylabel / title : 數值軸名稱、標題
    回傳
        ax
    例
        sk.box_by(df, 'Food', by='Region')
    """
    groups = {str(k): g for k, g in df.groupby(by)[value]}
    return box(groups, showmeans=showmeans, ax=ax, ylabel=ylabel or value,
               title=title or f"{value} by {by}")


def bar_grouped(table, stacked=False, ax=None, xlabel=None, ylabel=None, title=None):
    """分組（並排）或堆疊長條圖：把 pivot_table / crosstab 的結果直接畫出來。

    參數
        table    : DataFrame，列（index）是橫軸的類別、欄（columns）是不同顏色的組別，
                   例如 pd.crosstab(df['Region'], df['Location']) 或 df.pivot_table(...)
        stacked  : False → 並排；True → 堆疊
        ax       : 畫在哪個子圖；不給就開一張新圖
        xlabel / ylabel / title : 座標軸名稱、標題
    回傳
        ax
    例
        t = df.pivot_table(index='Region', columns='Location', values='Food', aggfunc='mean')
        sk.bar_grouped(t)
    """
    table = pd.DataFrame(table)
    k = len(table.columns)
    x = np.arange(len(table.index))
    width = 0.8 / (1 if stacked else k)
    ax = new_ax(ax, figsize=(max(7, 1.2 * len(x) * (1 if stacked else max(1, k / 2))), 5))
    bottom = np.zeros(len(x))
    for j, col in enumerate(table.columns):
        h = table[col].fillna(0).to_numpy(float)
        if stacked:
            ax.bar(x, h, width, bottom=bottom, label=str(col), edgecolor=EDGE)
            bottom += h
        else:
            ax.bar(x + (j - (k - 1) / 2) * width, h, width, label=str(col), edgecolor=EDGE)
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in table.index])
    if k > 1:
        ax.legend(title=None if table.columns.name is None else str(table.columns.name))
    ax.set_xlabel(xlabel or ("" if table.index.name is None else str(table.index.name)))
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    return ax
