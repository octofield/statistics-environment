"""敘述統計（講義 03a / 03b、HW02 / HW03）。

慣例跟講義一致：
- 四分位數、百分位數用 statistics.quantiles（預設 method='exclusive'）；
  pandas 的 .quantile() 是 'inclusive'，兩者結果可能不同，describe() 會兩個都列。
- 偏態 = m3 / s^3、峰態 = m4 / s^4（m 為母體動差、s 為樣本標準差），跟講義公式相同。
"""
import math
import statistics

import numpy as np
import pandas as pd

from ._style import fmt


def _series(x):
    s = pd.Series(x).dropna()
    return s.astype(float)


def _std_note(ddof):
    return "樣本標準差 s (ddof=1)" if ddof == 1 else "母體標準差 σ (ddof=0)"


def quantiles(x, n=4, method="exclusive"):
    """等分點：n=4 為四分位數、n=100 為百分位數（跟講義一樣用 statistics.quantiles）。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        n        : 分成幾等分（4 → Q1、Q2、Q3；100 → 第 1～99 百分位數）
        method   : 'exclusive'（講義、statistics 預設）或 'inclusive'（等於 pandas 的 .quantile）
    回傳
        n - 1 個切點的 list
    例
        q1, q2, q3 = sk.quantiles(x)
        p90 = sk.quantiles(x, n=100)[89]
    """
    return statistics.quantiles(list(_series(x)), n=n, method=method)


def describe(x, method="exclusive", digits=4):
    """一次算出常用的敘述統計量，並附上每一項的標準寫法（可以直接抄進答案）。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        method   : 四分位數算法，'exclusive'（講義）或 'inclusive'（pandas）；兩種都會列出
        digits   : 顯示到小數第幾位
    回傳
        DataFrame：統計量 / 值 / 寫法
    例
        sk.describe(df['Debt'])
    """
    s = _series(x)
    v = list(s)
    n = len(v)
    mean = statistics.mean(v)
    q1, q2, q3 = statistics.quantiles(v, n=4, method=method)
    p_q1, p_q3 = s.quantile(0.25), s.quantile(0.75)
    sd = statistics.stdev(v)
    m3 = sum((t - mean) ** 3 for t in v) / n
    m4 = sum((t - mean) ** 4 for t in v) / n
    modes = statistics.multimode(v)
    mode_txt = "無（每個值都只出現一次）" if len(modes) == n else ", ".join(fmt(m) for m in modes)

    rows = [
        ("個數 n", n, "len(x)"),
        ("平均數", mean, "statistics.mean(x)"),
        ("中位數", statistics.median(v), "statistics.median(x)"),
        ("眾數", mode_txt, "statistics.multimode(x)"),
        ("最小值", min(v), "min(x)"),
        (f"Q1（{method}）", q1, f"statistics.quantiles(x, n=4)[0]"),
        (f"Q3（{method}）", q3, f"statistics.quantiles(x, n=4)[2]"),
        ("Q1（pandas）", p_q1, "pd.Series(x).quantile(0.25)"),
        ("Q3（pandas）", p_q3, "pd.Series(x).quantile(0.75)"),
        ("最大值", max(v), "max(x)"),
        ("全距", max(v) - min(v), "max(x) - min(x)"),
        (f"IQR（{method}）", q3 - q1, "Q3 - Q1"),
        ("母體變異數 σ²", statistics.pvariance(v), "statistics.pvariance(x)"),
        ("樣本變異數 s²", statistics.variance(v), "statistics.variance(x)"),
        ("母體標準差 σ", statistics.pstdev(v), "statistics.pstdev(x)"),
        ("樣本標準差 s", sd, "statistics.stdev(x)"),
        ("變異係數 CV = s / x̄", sd / mean if mean else float("nan"), "statistics.stdev(x) / statistics.mean(x)"),
        ("平均絕對離差 MAD", statistics.mean([abs(t - mean) for t in v]), "statistics.mean([abs(v - mean) for v in x])"),
        ("偏態 m3 / s³", m3 / sd ** 3, "sum((v - mean) ** 3 for v in x) / n / s ** 3"),
        ("峰態 m4 / s⁴", m4 / sd ** 4, "sum((v - mean) ** 4 for v in x) / n / s ** 4"),
    ]
    if min(v) > 0:
        rows.append(("幾何平均數", statistics.geometric_mean(v), "statistics.geometric_mean(x)"))

    df = pd.DataFrame(rows, columns=["統計量", "值", "寫法"]).set_index("統計量")
    df["值"] = [round(t, digits) if isinstance(t, float) else t for t in df["值"]]
    return df


def freq_table(x, start=None, width=None, k=None, edges=None, right=False, digits=4):
    """次數分配表（含組中點、相對次數、累積次數），並印出眾數組。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        start    : 第一組的下限，例如 0
        width    : 組距，例如 5000
        k        : 組數（可省略，會自動算到涵蓋最大值）
        edges    : 直接指定組界，例如 [160, 164, 168, ...]（給了就不用 start / width）
        right    : False → 組別 [a, b)（作業的寫法）；True → (a, b]
        digits   : 顯示到小數第幾位
    回傳
        DataFrame；.attrs['edges'] 是組界、.attrs['modal'] 是眾數組的組中點
    例
        sk.freq_table(debt, start=0, width=5000)
        sk.freq_table(values, edges=range(160, 196, 4))
    """
    s = _series(x)
    if edges is None:
        if start is None or width is None:
            raise ValueError("請給 start 和 width（例如 start=0, width=5000），或直接給 edges=[...]")
        if k is None:
            k = math.ceil((s.max() - start) / width)
            if not right and start + k * width <= s.max():
                k += 1
            k = max(k, 1)
        edges = [start + i * width for i in range(k + 1)]
    edges = list(edges)

    cats = pd.cut(s, bins=edges, right=right, include_lowest=right)
    counts = cats.value_counts(sort=False)
    outside = int(cats.isna().sum())

    lo, hi = edges[:-1], edges[1:]
    br = ("(", "]") if right else ("[", ")")
    df = pd.DataFrame({
        "組別": [f"{br[0]}{fmt(a)}, {fmt(b)}{br[1]}" for a, b in zip(lo, hi)],
        "下限": lo,
        "上限": hi,
        "組中點": [(a + b) / 2 for a, b in zip(lo, hi)],
        "次數": counts.values.astype(int),
    })
    total = df["次數"].sum()
    df["相對次數"] = (df["次數"] / total).round(digits)
    df["累積次數"] = df["次數"].cumsum()
    df["累積相對次數"] = (df["累積次數"] / total).round(digits)

    top = df["次數"].max()
    modal = df.loc[df["次數"] == top, ["組別", "組中點"]]
    print(f"眾數組：{', '.join(modal['組別'])}　→　眾數（組中點）= {', '.join(fmt(m) for m in modal['組中點'])}")
    if outside:
        print(f"⚠ 有 {outside} 筆資料落在組界外，沒被算進表裡，請調整 start / width / edges")

    df.attrs["edges"] = edges
    df.attrs["right"] = right
    df.attrs["modal"] = list(modal["組中點"])
    return df


def grouped_stats(midpoints, freqs, sample=True):
    """分組資料的平均數與變異數（用組中點近似每筆資料）。

    參數
        midpoints : 各組的組中點
        freqs     : 各組的次數
        sample    : True → 樣本變異數（除以 n − 1）；False → 母體變異數（除以 n）
    回傳
        dict：n、mean、var、std
    例
        t = sk.freq_table(x, start=0, width=5000)
        sk.grouped_stats(t['組中點'], t['次數'])
    """
    m = np.asarray(midpoints, float)
    f = np.asarray(freqs, float)
    n = f.sum()
    mean = (m * f).sum() / n
    ss = (f * (m - mean) ** 2).sum()
    var = ss / (n - 1) if sample else ss / n
    out = {"n": n, "mean": mean, "var": var, "std": math.sqrt(var)}
    print(f"分組平均數 = {mean:.4f}，{'樣本' if sample else '母體'}變異數 = {var:.4f}，標準差 = {math.sqrt(var):.4f}")
    return out


def percent_rank(x, value):
    """百分等級：value 在資料中大約排在第幾百分位。

    講義定義：若 value 在資料中，百分等級可以是 [100 − %(≥ value), %(≤ value)] 之間的任何數；
    作業常用的「嚴格小於 value 的比例」也一併列出。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        value    : 要查百分等級的值
    回傳
        dict：range（講義定義的範圍）、strictly_below（嚴格小於的百分比）
    例
        sk.percent_rank(debt, 10000)
    """
    s = _series(x)
    below_eq = (s <= value).mean() * 100
    above_eq = (s >= value).mean() * 100
    strictly_below = (s < value).mean() * 100
    rng = [100 - above_eq, below_eq]
    print(f"講義定義的範圍：[{rng[0]:.2f}, {rng[1]:.2f}]")
    print(f"嚴格小於 {fmt(value)} 的比例：{strictly_below:.2f}%")
    return {"range": rng, "strictly_below": strictly_below}


def outliers_iqr(x, k=1.5, method="exclusive"):
    """用 k × IQR 規則找離群值：小於 Q1 − k·IQR 或大於 Q3 + k·IQR。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        k        : 倍數，講義用 1.5
        method   : 四分位數算法，'exclusive'（講義）或 'inclusive'（pandas）
    回傳
        離群值（Series，保留原本的 index）
    例
        sk.outliers_iqr(df['Income'])
    """
    s = _series(x)
    q1, _, q3 = statistics.quantiles(list(s), n=4, method=method)
    iqr = q3 - q1
    lo, hi = q1 - k * iqr, q3 + k * iqr
    out = s[(s < lo) | (s > hi)]
    print(f"Q1 = {q1:.4f}, Q3 = {q3:.4f}, IQR = {iqr:.4f}（{method}）")
    print(f"範圍 [{lo:.4f}, {hi:.4f}]，離群值 {len(out)} 個：{[fmt(t) for t in out]}")
    return out


def _within_table(x, ks, ddof, theory, theory_name):
    s = _series(x)
    mu = s.mean()
    sd = s.std(ddof=ddof)
    rows = []
    for k in ks:
        lo, hi = mu - k * sd, mu + k * sd
        rows.append({"k": k, "下限": lo, "上限": hi,
                     "實際比例": ((s >= lo) & (s <= hi)).mean(),
                     theory_name: theory(k)})
    print(f"平均數 = {mu:.4f}，使用{_std_note(ddof)} = {sd:.4f}")
    return pd.DataFrame(rows).set_index("k").round(4)


def chebyshev(x, ks=(1.5, 2), ddof=0):
    """驗證柴比雪夫定理：至少 1 − 1/k² 的資料落在 μ ± kσ 內。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        ks       : 要檢查的 k 值，例如 (1.5, 2)
        ddof     : 0 → 母體標準差（講義）；1 → 樣本標準差（題目說「視為樣本」時）
    回傳
        DataFrame：k、區間上下限、實際比例、Chebyshev 下界
    例
        sk.chebyshev(income, ks=(1.5, 2), ddof=1)
    """
    return _within_table(x, ks, ddof, lambda k: 1 - 1 / k ** 2, "Chebyshev 下界")


def empirical_rule(x, ks=(1, 2, 3), ddof=0):
    """經驗法則：鐘形資料約 68% / 95% / 99.7% 落在 1 / 2 / 3 個標準差內。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        ks       : 要檢查的 k 值，預設 (1, 2, 3)
        ddof     : 0 → 母體標準差（講義）；1 → 樣本標準差
    回傳
        DataFrame：k、區間上下限、實際比例、經驗法則估計
    例
        sk.empirical_rule(income)
    """
    est = {1: 0.68, 2: 0.95, 3: 0.997}
    return _within_table(x, ks, ddof, lambda k: est.get(k, float("nan")), "經驗法則估計")


def zscore(x, ddof=1):
    """z 分數 = (x − 平均數) / 標準差。

    參數
        x        : 資料（list、pandas Series、numpy array 都可以；缺值會自動略過）
        ddof     : 1 → 樣本標準差（預設）；0 → 母體標準差
    回傳
        每筆資料的 z 分數（Series）
    例
        z = sk.zscore(df['Food'])
    """
    s = _series(x)
    return (s - s.mean()) / s.std(ddof=ddof)


def cov_corr(x, y):
    """共變異數（母體與樣本）與相關係數 r。

    參數
        x, y     : 兩組成對的資料（長度要一樣）
    回傳
        DataFrame：列為共變異數、相關係數；欄為母體、樣本
    例
        sk.cov_corr(sizes, prices)
    """
    a, b = _series(x), _series(y)
    pcov = ((a - a.mean()) * (b - b.mean())).sum() / len(a)
    scov = pcov * len(a) / (len(a) - 1)
    r = a.corr(b)
    df = pd.DataFrame({"母體": [pcov, r], "樣本": [scov, r]},
                      index=["共變異數", "相關係數 r"]).round(4)
    return df


# ------------------------------------------------------------------ 多個變數（HW02 / HW03）

def _summary(s):
    """一組資料的常用統計量（四分位數用講義的 exclusive 算法）。"""
    v = list(s)
    n = len(v)
    q1, _, q3 = statistics.quantiles(v, n=4) if n >= 2 else (float("nan"),) * 3
    return {
        "個數 n": n,
        "平均數": statistics.mean(v) if n else float("nan"),
        "中位數": statistics.median(v) if n else float("nan"),
        "Q1": q1,
        "Q3": q3,
        "母體標準差 σ": statistics.pstdev(v) if n else float("nan"),
        "樣本標準差 s": statistics.stdev(v) if n >= 2 else float("nan"),
        "最小值": min(v) if n else float("nan"),
        "最大值": max(v) if n else float("nan"),
    }


def _numeric_cols(df, cols):
    if cols is None:
        cols = list(df.select_dtypes("number").columns)
    elif isinstance(cols, str):
        cols = [cols]
    if not cols:
        raise ValueError("找不到數值欄位，請用 cols=[...] 指定（欄位可能被讀成文字，先看 df.dtypes）")
    return list(cols)


def describe_cols(df, cols=None, digits=4):
    """多個數值欄位並排比較：平均、中位、四分位、標準差、最小、最大。

    參數
        df       : DataFrame
        cols     : 要比較的欄位，例如 ['Food', 'Income', 'Debt']；不給就用所有數值欄位
        digits   : 顯示到小數第幾位
    回傳
        DataFrame：列為統計量、欄為變數
    例
        sk.describe_cols(df, ['Food', 'Income', 'Debt'])
    """
    cols = _numeric_cols(df, cols)
    table = pd.DataFrame({c: _summary(_series(df[c])) for c in cols}).round(digits).astype(object)
    table.loc["個數 n"] = table.loc["個數 n"].astype(int)
    print(f"寫法：df[{cols!r}].agg(['count', 'mean', 'median', 'std', 'min', 'max'])")
    print("　　　pandas 的 std 是樣本標準差（ddof=1）；四分位數照講義要用 statistics.quantiles(df[欄位], n=4)")
    return table


def describe_by(df, value, by, digits=4):
    """依類別分組，比較每一組的統計量（例如各地區的食物支出）。

    參數
        df       : DataFrame
        value    : 要統計的數值欄位，例如 'Food'
        by       : 分組依據的類別欄位，例如 'Region'（也可以給 list，用兩個欄位交叉分組）
        digits   : 顯示到小數第幾位
    回傳
        DataFrame：列為各組、欄為統計量
    例
        sk.describe_by(df, 'Food', by='Region')
    """
    rows = {k: _summary(_series(g)) for k, g in df.groupby(by)[value]}
    table = pd.DataFrame(rows).T.round(digits)
    table["個數 n"] = table["個數 n"].astype(int)
    if isinstance(by, str):
        table.index.name = by
    else:
        table.index.names = list(by)
    print(f"寫法：df.groupby({by!r})[{value!r}].agg(['count', 'mean', 'median', 'std', 'min', 'max'])")
    print("　　　只要一個統計量：df.groupby(...)[...].mean()；pandas 的 std 是樣本標準差（ddof=1）")
    return table


def corr_matrix(df, cols=None, kind="r", ddof=1, digits=4):
    """多個變數兩兩之間的相關係數（或共變異數）矩陣，並指出相關最強的一組。

    參數
        df       : DataFrame
        cols     : 要比較的欄位，例如 ['Food', 'Income', 'Debt']；不給就用所有數值欄位
        kind     : 'r' → 相關係數；'cov' → 共變異數
        ddof     : 共變異數用：1 → 樣本（除以 n − 1，pandas 預設）；0 → 母體（除以 n）
        digits   : 顯示到小數第幾位
    回傳
        DataFrame（對稱矩陣，對角線是 1 或各變數的變異數）
    例
        sk.corr_matrix(df, ['Food', 'Income', 'Debt'])
        sk.corr_matrix(df, ['Food', 'Income'], kind='cov', ddof=0)
    """
    cols = _numeric_cols(df, cols)
    data = df[cols].astype(float)
    if kind == "r":
        table = data.corr()
        print(f"寫法：df[{cols!r}].corr()　　兩個變數：df['x'].corr(df['y'])")
    elif kind == "cov":
        table = data.cov(ddof=ddof)
        print(f"寫法：df[{cols!r}].cov(ddof={ddof})　　（{'樣本，除以 n − 1' if ddof == 1 else '母體，除以 n'}）")
    else:
        raise ValueError("kind 要是 'r'（相關係數）或 'cov'（共變異數）")
    if len(cols) >= 2:
        r = data.corr()
        pairs = [(abs(r.iloc[i, j]), cols[i], cols[j], r.iloc[i, j])
                 for i in range(len(cols)) for j in range(i + 1, len(cols))]
        _, a, b, best = max(pairs)
        print(f"相關最強的一組：{a} 與 {b}，r = {best:.4f}")
    return table.round(digits)
