"""機率分布（講義 04c / 05 / 06a、HW04 / HW05）。

用法：
    X = sk.Poisson(6.6)
    X.P("X >= 10")            # 自動處理離散分布的 ≥ / >：Pr(X ≥ 10) = 1 - F(9)
    sk.prob(X, "2 < X <= 5")
    sk.quantile(sk.Normal(80, 10), 0.8)
    sk.plot_dist(X, "X >= 10")

每次計算都會印出「課程寫法」的 scipy 程式碼，請把程式碼貼進答案，
這樣匯出的 HTML 不需要 statkit 也看得懂。
也可以直接傳入 scipy 的 frozen 分布，例如 sk.prob(stats.binom(20, 0.1), "X <= 3")。
"""
import math
import re

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
from scipy import stats

from ._style import ACCENT, EDGE, FACE, HIGHLIGHT, fmt, new_ax


# ---------------------------------------------------------------- 分布物件

class Dist:
    """包住 scipy frozen 分布，並記住課程寫法的參數字串（例如 'scale=1/6.6'）。"""

    def __init__(self, frozen, kw, label, prefix=None, setup=None):
        self.frozen = frozen
        self._family = getattr(frozen, "dist", frozen)   # 自訂分布 rv_discrete(values=...) 沒有 .dist
        self.name = self._family.name
        self.kw = kw
        self.label = label
        self.prefix = prefix      # 自訂分布：程式碼寫成 X.cdf(3)
        self.setup = setup        # 自訂分布：先定義 X = stats.rv_discrete(...)

    @property
    def discrete(self):
        return isinstance(self._family, stats.rv_discrete)

    def P(self, query, digits=4, show=True):
        return prob(self, query, digits=digits, show=show)

    def quantile(self, q, tail="left", digits=4, show=True):
        return quantile(self, q, tail=tail, digits=digits, show=show)

    def moments(self, show=True):
        return moments(self, show=show)

    def plot(self, query=None, kind="pdf", ax=None):
        return plot_dist(self, query, kind=kind, ax=ax)

    def code(self, method, xname, x=None):
        if self.prefix:
            return f"{self.prefix}.{method}({'' if x is None else x})"
        args = self.kw if x is None else f"{xname}={x}, {self.kw}"
        return f"stats.{self.name}.{method}({args})"

    def __getattr__(self, attr):
        # pmf / pdf / cdf / sf / ppf / rvs / mean / var ... 直接轉給 scipy
        if attr.startswith("_") or attr == "frozen":
            raise AttributeError(attr)
        return getattr(self.frozen, attr)

    def __repr__(self):
        return f"{self.label}　→　stats.{self.name}({self.kw})"


def Binom(n, p):
    """二項分布 Bi(n, p)：n 次獨立試驗中成功的次數，X = 0, 1, …, n。

    參數
        n        : 試驗次數（正整數）
        p        : 每次試驗成功的機率（0～1）
    例
        X = sk.Binom(20, 0.1);  X.P('X <= 3')
    """
    return Dist(stats.binom(n=n, p=p), f"n={fmt(n)}, p={fmt(p)}", f"Bi(n={fmt(n)}, p={fmt(p)})")


def Poisson(mu):
    """卜瓦松分布 Poi(λ)：單位時間內發生的次數，X = 0, 1, 2, …。

    參數
        mu       : λ，單位時間平均發生次數（> 0）。時間單位要跟題目一致（每小時 3 次 → 20 分鐘 λ = 1）
    例
        sk.Poisson(6.6).P('X >= 10')
    """
    return Dist(stats.poisson(mu=mu), f"mu={fmt(mu)}", f"Poi(λ={fmt(mu)})")


def Hypergeom(N, K, n):
    """超幾何分布 Hyper(N, K, n)：母體 N 個、其中 K 個成功，不放回抽 n 個，X = 抽到的成功數。

    參數
        N        : 母體總數
        K        : 母體中「成功」的個數（≤ N）
        n        : 抽出的個數（≤ N）
    注意
        scipy 的參數名稱不同：M = N（母體）、n = K（成功數）、N = n（抽出數）；印出的程式碼已經換好
    例
        sk.Hypergeom(N=20, K=12, n=10).P('X == 7')
    """
    return Dist(stats.hypergeom(M=N, n=K, N=n), f"M={fmt(N)}, n={fmt(K)}, N={fmt(n)}",
                f"Hyper(N={fmt(N)}, K={fmt(K)}, n={fmt(n)})")


def Geom(p):
    """幾何分布 Geo(p)：第一次成功發生在第幾次試驗，X = 1, 2, 3, …。

    參數
        p        : 每次試驗成功的機率（0～1）
    例
        sk.Geom(0.4).P('X <= 4')
    """
    return Dist(stats.geom(p=p), f"p={fmt(p)}", f"Geo(p={fmt(p)})")


def Uniform(a, b):
    """均勻分布 Uni(a, b)：[a, b] 之間每個值的機率密度都一樣。

    參數
        a        : 下限
        b        : 上限（> a）
    注意
        scipy 寫法是 loc=a, scale=b − a；印出的程式碼已經換好
    例
        sk.Uniform(10, 16).P('X > 15')
    """
    return Dist(stats.uniform(loc=a, scale=b - a), f"loc={fmt(a)}, scale={fmt(b - a)}",
                f"Uni(a={fmt(a)}, b={fmt(b)})")


def Expon(lam):
    """指數分布 Exp(λ)：兩次發生之間的等待時間（X ≥ 0）。

    參數
        lam      : λ，發生率（每單位時間平均發生幾次，> 0）；平均等待時間 = 1/λ
    注意
        scipy 寫法是 scale=1/λ；印出的程式碼已經換好。x 的時間單位要跟 λ 一致
    例
        sk.Expon(6.6).P('X > 25/60')     # 每小時 6.6 次，等超過 25 分鐘
    """
    inv = 1 / lam
    if lam < 1 and abs(inv - round(inv)) < 1e-9:      # Expon(1/12) → scale=12
        scale, label = fmt(round(inv)), f"Exp(λ=1/{fmt(round(inv))})"
    elif lam == 1:
        scale, label = "1", "Exp(λ=1)"
    else:
        scale, label = f"1/{fmt(lam)}", f"Exp(λ={fmt(lam)})"
    return Dist(stats.expon(scale=inv), f"scale={scale}", label)


def Normal(mu=0, sigma=1):
    """常態分布 ND(μ, σ)。

    參數
        mu       : 平均數 μ
        sigma    : 標準差 σ（> 0）；注意不是變異數
    例
        sk.Normal(80, 10).P('70 <= X <= 90')
    """
    return Dist(stats.norm(loc=mu, scale=sigma), f"loc={fmt(mu)}, scale={fmt(sigma)}",
                f"ND(μ={fmt(mu)}, σ={fmt(sigma)})")


def Discrete(xs, ps):
    """自訂離散分布（機率表），例如需求分布。

    參數
        xs       : 所有可能的值，例如 range(9)
        ps       : 對應的機率（加總要等於 1）
    例
        D = sk.Discrete(range(9), [0.06, 0.15, 0.22, 0.22, 0.17, 0.10, 0.05, 0.02, 0.01])
        D.P('X <= 4');  D.moments()
    """
    xs, ps = list(xs), list(ps)
    if not math.isclose(sum(ps), 1, abs_tol=1e-9):
        raise ValueError(f"機率加總是 {sum(ps)}，不是 1")
    setup = f"X = stats.rv_discrete(values=({[fmt(x) for x in xs]}, {[fmt(p) for p in ps]}))".replace("'", "")
    return Dist(stats.rv_discrete(values=(xs, ps)), "", "自訂離散分布", prefix="X", setup=setup)


def _code_lines(d, line):
    """要印出的程式碼：自訂分布會先加上 X = ... 的定義。"""
    return f"{d.setup}\n{line}" if d.setup else line


def _print_code(d, line):
    code = _code_lines(d, line)
    print("程式碼：" + ("\n" + code if "\n" in code else code))


def _as_dist(d):
    if isinstance(d, Dist):
        return d
    if hasattr(d, "dist") and hasattr(d, "args"):     # scipy frozen
        shapes = [s.strip() for s in (d.dist.shapes or "").split(",") if s.strip()]
        names = shapes + ["loc", "scale"]
        vals = dict(zip(names, d.args))
        vals.update(d.kwds)
        if vals.get("loc", 0) == 0:
            vals.pop("loc", None)
        if vals.get("scale", 1) == 1:
            vals.pop("scale", None)
        order = [k for k in names if k in vals]
        kw = ", ".join(f"{k}={fmt(vals[k])}" for k in order)
        return Dist(d, kw, f"{d.dist.name}({kw})")
    raise TypeError("請傳入 sk.Binom(...) 之類的分布，或 scipy 的 frozen 分布，例如 stats.norm(80, 10)")


# ---------------------------------------------------------------- 解析 "2 < X <= 5"

_OP_RE = re.compile(r"(<=|>=|=<|=>|==|<|>|=)")
_NUM_RE = re.compile(r"^[0-9.eE+\-*/() ]+$")
_FLIP = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "=="}


class _Num(float):
    """解析出來的數字，記住原本的寫法（例如 25/60），印程式碼時照原樣寫。"""
    src = None


def _num(text):
    text = text.strip()
    if not text or not _NUM_RE.match(text):
        raise ValueError(f"看不懂的數字：{text!r}")
    v = _Num(eval(text, {"__builtins__": {}}, {}))
    if not re.fullmatch(r"[+-]?[0-9.]+", text):
        v.src = text.replace(" ", "")
    return v


def _normalize(query):
    s = str(query).strip()
    s = (s.replace("≤", "<=").replace("≥", ">=").replace("＜", "<").replace("＞", ">")
          .replace("＝", "=").replace("（", "(").replace("）", ")").replace("−", "-"))
    m = re.fullmatch(r"\s*(?:Pr|P)\s*\((.*)\)\s*", s)
    if m:
        s = m.group(1)
    s = s.replace("=<", "<=").replace("=>", ">=")
    return s.strip()


def _parse(query):
    """回傳 (lower, upper, eq)。lower / upper 為 (值, 是否包含) 或 None。"""
    s = _normalize(query)
    parts = [p.strip() for p in _OP_RE.split(s)]
    ops = [o if o != "=" else "==" for o in parts[1::2]]
    terms = parts[0::2]
    is_var = [bool(re.fullmatch(r"[A-Za-z_]\w*", t)) for t in terms]

    if len(terms) == 2 and terms[0] == "":          # ">= 10" 省略 X
        terms[0], is_var[0] = "X", True

    if len(terms) == 2:
        if is_var[0]:
            op, v = ops[0], _num(terms[1])
        elif is_var[1]:
            op, v = _FLIP[ops[0]], _num(terms[0])
        else:
            raise ValueError(f"找不到變數：{query!r}")
        if op == "==":
            return None, None, v
        if op in ("<", "<="):
            return None, (v, op == "<="), None
        return (v, op == ">="), None, None

    if len(terms) == 3 and is_var[1] and not is_var[0] and not is_var[2]:
        a, b = _num(terms[0]), _num(terms[2])
        o1, o2 = ops
        if o1 in ("<", "<=") and o2 in ("<", "<="):
            return (a, o1 == "<="), (b, o2 == "<="), None
        if o1 in (">", ">=") and o2 in (">", ">="):
            return (b, o2 == ">="), (a, o1 == ">="), None
    raise ValueError(f"看不懂的條件：{query!r}。請寫成 'X >= 10'、'2 < X <= 5'、'X == 3' 這種形式")


def _pretty(lower, upper, eq, var="X"):
    lt = lambda inc: "≤" if inc else "<"
    if eq is not None:
        return f"Pr({var} = {fmt(eq)})"
    if lower and upper:
        return f"Pr({fmt(lower[0])} {lt(lower[1])} {var} {lt(upper[1])} {fmt(upper[0])})"
    if upper:
        return f"Pr({var} {lt(upper[1])} {fmt(upper[0])})"
    return f"Pr({var} {'≥' if lower[1] else '>'} {fmt(lower[0])})"


def _evaluate(d, query):
    """回傳 dict：value、math（例如 '1 - F(9)'）、expr（scipy 程式碼）、region（畫圖用）。"""
    lower, upper, eq = _parse(query)
    title = _pretty(lower, upper, eq)
    if d.discrete:
        cdf = lambda k: d.code("cdf", "k", fmt(k))
        if eq is not None:
            if not float(eq).is_integer():
                return dict(title=title, value=0.0, math="0（離散分布只取整數）", expr="0", region=None)
            k = int(eq)
            return dict(title=title, value=float(d.frozen.pmf(k)), math=f"f({k})",
                        expr=d.code("pmf", "k", k), region=(k, k))
        L = None if lower is None else (math.ceil(lower[0]) if lower[1] else math.floor(lower[0]) + 1)
        U = None if upper is None else (math.floor(upper[0]) if upper[1] else math.ceil(upper[0]) - 1)
        if L is not None and U is not None:
            if U < L:
                return dict(title=title, value=0.0, math="0（區間內沒有整數）", expr="0", region=None)
            value = d.frozen.cdf(U) - d.frozen.cdf(L - 1)
            return dict(title=title, value=float(value), math=f"F({U}) - F({L - 1})",
                        expr=f"{cdf(U)} - {cdf(L - 1)}", region=(L, U))
        if U is not None:
            return dict(title=title, value=float(d.frozen.cdf(U)), math=f"F({U})",
                        expr=cdf(U), region=(None, U))
        return dict(title=title, value=float(1 - d.frozen.cdf(L - 1)), math=f"1 - F({L - 1})",
                    expr=f"1 - {cdf(L - 1)}", region=(L, None))

    cdf = lambda x: d.code("cdf", "x", fmt(x))
    if eq is not None:
        return dict(title=title, value=0.0, math="0（連續分布單點機率為 0）", expr="0", region=None)
    if lower and upper:
        a, b = lower[0], upper[0]
        if b < a:
            return dict(title=title, value=0.0, math="0", expr="0", region=None)
        return dict(title=title, value=float(d.frozen.cdf(b) - d.frozen.cdf(a)),
                    math=f"F({fmt(b)}) - F({fmt(a)})", expr=f"{cdf(b)} - {cdf(a)}", region=(a, b))
    if upper:
        b = upper[0]
        return dict(title=title, value=float(d.frozen.cdf(b)), math=f"F({fmt(b)})",
                    expr=cdf(b), region=(None, b))
    a = lower[0]
    return dict(title=title, value=float(1 - d.frozen.cdf(a)), math=f"1 - F({fmt(a)})",
                expr=f"1 - {cdf(a)}", region=(a, None))


# ---------------------------------------------------------------- 計算

def prob(d, query, digits=4, show=True):
    """計算機率並印出課程寫法的程式碼（離散分布的 ≥ / > 會自動處理要不要減 1）。

    參數
        d        : 分布，例如 sk.Binom(10, 0.4)、sk.Normal(80, 10)，或 scipy 的 stats.norm(80, 10)
        query    : 條件字串，例如 'X >= 10'、'2 < X <= 5'、'X == 3'、'P(X ≤ 4)'；
                   數字可以寫算式，例如 'X > 25/60'
        digits   : 顯示到小數第幾位
        show     : True 會印出算式與程式碼；False 只回傳數值
    回傳
        機率（float）
    例
        sk.prob(sk.Binom(20, 0.1), 'X <= 3')
    """
    d = _as_dist(d)
    r = _evaluate(d, query)
    if show:
        print(f"{d.label}")
        print(f"{r['title']} = {r['math']} = {r['value']:.{digits}f}")
        _print_code(d, f"print(round({r['expr']}, {digits}))")
    return r["value"]


def quantile(d, q, tail="left", digits=4, show=True):
    """反查：給機率求 x。

    參數
        d        : 分布，例如 sk.Binom(10, 0.4)、sk.Normal(80, 10)，或 scipy 的 stats.norm(80, 10)
        q        : 機率（0～1）
        tail     : 'left' → 求 x 使 Pr(X ≤ x) = q；'right' → 求 x 使 Pr(X ≥ x) = q
        digits   : 顯示到小數第幾位
        show     : True 會印出算式與程式碼；False 只回傳數值
    回傳
        x（float）。離散分布回傳「F(x) ≥ q 的最小 x」（講義的定義）
    例
        sk.quantile(sk.Normal(80, 10), 0.8)
        sk.quantile(sk.Normal(80, 10), 0.05, tail='right')
    """
    d = _as_dist(d)
    cum = q if tail == "left" else 1 - q
    x = float(d.frozen.ppf(cum))
    expr = d.code("ppf", "q", fmt(q) if tail == "left" else f"1 - {fmt(q)}")
    if show:
        print(d.label)
        if d.discrete:
            print(f"滿足 F(x) ≥ {fmt(cum)} 的最小 x = {fmt(x)}")
        else:
            cond = f"Pr(X ≤ x) = {fmt(q)}" if tail == "left" else f"Pr(X ≥ x) = {fmt(q)}"
            print(f"{cond}　→　x = {x:.{digits}f}")
        _print_code(d, f"print(round({expr}, {digits}))")
    return x


def moments(d, show=True):
    """平均數、變異數、標準差。

    參數
        d        : 分布，例如 sk.Binom(10, 0.4)、sk.Normal(80, 10)，或 scipy 的 stats.norm(80, 10)
        show     : True 會印出算式與程式碼；False 只回傳數值
    回傳
        dict：mean、var、std
    例
        sk.moments(sk.Hypergeom(20, 12, 10))
    """
    d = _as_dist(d)
    mean, var = float(d.frozen.mean()), float(d.frozen.var())
    if show:
        print(d.label)
        print(f"E[X] = {mean:.4f}，Var(X) = {var:.4f}，SD(X) = {math.sqrt(var):.4f}")
        _print_code(d, f"print({d.code('mean', None)}, {d.code('var', None)})")
    return {"mean": mean, "var": var, "std": math.sqrt(var)}


def newsvendor(D, co, cu, digits=4):
    """報童模型（講義 05）：最適訂購量 q* 滿足 F(q*) = cu / (co + cu)。

    參數
        D        : 需求分布，例如 sk.Uniform(20, 50)、sk.Normal(100, 15)、sk.Discrete(...)
        co       : 多訂一單位的成本（overage）= 進貨成本 c + 處理費 d − 殘值 v
        cu       : 少訂一單位的成本（underage）= 售價 r − 進貨成本 c + 缺貨成本 s
        digits   : 顯示到小數第幾位
    回傳
        q*（float）
    例
        sk.newsvendor(sk.Uniform(20, 50), co=5, cu=10)     # 講義答案 40
    """
    D = _as_dist(D)
    ratio = cu / (co + cu)
    q = float(D.frozen.ppf(ratio))
    print(f"{D.label}，co = {fmt(co)}，cu = {fmt(cu)}")
    print(f"臨界比例 F(q*) = cu / (co + cu) = {fmt(cu)} / {fmt(co + cu)} = {ratio:.{digits}f}")
    print(f"最適訂購量 q* = {q:.{digits}f}，缺貨機率 1 - F(q*) = {1 - ratio:.{digits}f}")
    _print_code(D, f"print(round({D.code('ppf', 'q', f'{fmt(cu)} / ({fmt(co)} + {fmt(cu)})')}, {digits}))")
    return q


def inventory_profit(D, price, cost, salvage=0, levels=None):
    """離散需求下，每個進貨量 y 的期望利潤（講義 04b 的蘋果例子）。

    利潤 = price × min(y, X) − cost × y + salvage × max(y − X, 0)

    參數
        D        : 需求分布（離散），例如 sk.Discrete(...)、sk.Poisson(3)
        price    : 售價（每賣出一單位的收入）
        cost     : 進貨成本（每進一單位）
        salvage  : 殘值（每剩一單位可以回收的錢，預設 0）
        levels   : 要比較的進貨量（不給就用需求所有可能的值）
    回傳
        DataFrame：每個進貨量的期望銷量、服務水準、期望利潤
    例
        sk.inventory_profit(D, price=10, cost=2)
    """
    import pandas as pd
    D = _as_dist(D)
    lo, hi = _support(D, 0, 1 - 1e-9)
    xs = np.arange(math.floor(lo), math.ceil(hi) + 1)
    ps = D.frozen.pmf(xs)
    levels = xs if levels is None else np.asarray(levels)
    rows = []
    for y in levels:
        sold = np.minimum(y, xs)
        left = np.maximum(y - xs, 0)
        profit = (price * sold - cost * y + salvage * left) * ps
        rows.append({"進貨量 y": int(y), "期望銷量": (sold * ps).sum(),
                     "服務水準 Pr(X ≤ y)": float(D.frozen.cdf(y)), "期望利潤": profit.sum()})
    df = pd.DataFrame(rows).set_index("進貨量 y").round(4)
    best = df["期望利潤"].idxmax()
    print(f"期望利潤最大的進貨量 y* = {best}，期望利潤 = {df.loc[best, '期望利潤']:.4f}")
    return df


# ---------------------------------------------------------------- 繪圖

def _support(d, lo_q=1e-4, hi_q=1 - 1e-4):
    lo, hi = d.frozen.support()
    a = d.frozen.ppf(lo_q) if not np.isfinite(lo) else lo
    b = d.frozen.ppf(hi_q) if not np.isfinite(hi) else hi
    return float(a), float(b)


def plot_dist(d, query=None, kind="pdf", ax=None, title=None, xlabel="x"):
    """畫 PMF / PDF 或 CDF，並把 query 的區間塗色（HTML 裡看得到）。

    參數
        d        : 分布，例如 sk.Binom(10, 0.4)、sk.Normal(80, 10)，或 scipy 的 stats.norm(80, 10)
        query    : 要塗色的條件，例如 'X >= 10'（可省略）
        kind     : 'pdf' → PMF / PDF；'cdf' → 累積分布函數
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
        title / xlabel : 標題、橫軸名稱
    回傳
        ax
    例
        sk.plot_dist(sk.Poisson(6.6), 'X >= 10')
    """
    d = _as_dist(d)
    ax = new_ax(ax, figsize=(8, 5))
    r = _evaluate(d, query) if query else None
    region = r["region"] if r else None

    if d.discrete:
        a, b = _support(d)
        xs = np.arange(math.floor(a), math.ceil(b) + 1)
        if kind == "cdf":
            ax.step(xs, d.frozen.cdf(xs), where="post", color=EDGE)
            ax.set_ylabel("Cumulative probability")
        else:
            ys = d.frozen.pmf(xs)
            colors = [FACE] * len(xs)
            if region:
                L, U = region
                colors = [HIGHLIGHT if (L is None or x >= L) and (U is None or x <= U) else FACE for x in xs]
            ax.bar(xs, ys, color=colors, edgecolor=EDGE, width=0.9 if len(xs) < 60 else 1.0)
            ax.set_ylabel("Probability")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    else:
        a, b = _support(d, 5e-4, 1 - 5e-4)
        pad = (b - a) * 0.08
        xs = np.linspace(a - pad, b + pad, 600)
        if kind == "cdf":
            ax.plot(xs, d.frozen.cdf(xs), color=EDGE)
            ax.set_ylabel("Cumulative probability")
        else:
            ys = d.frozen.pdf(xs)
            ax.plot(xs, ys, color=EDGE)
            if region:
                L, U = region
                mask = np.ones_like(xs, dtype=bool)
                if L is not None:
                    mask &= xs >= L
                if U is not None:
                    mask &= xs <= U
                ax.fill_between(xs, ys, where=mask, color=HIGHLIGHT, alpha=0.45)
            ax.set_ylabel("Density")
            ax.set_ylim(bottom=0)

    ax.set_xlabel(xlabel)
    head = title or d.label
    ax.set_title(f"{head}\n{r['title']} = {r['value']:.4f}" if r else head)
    return ax


def normal_approx(n, p, query=None, ax=None):
    """二項分布的常態近似（講義 06a）：比較精確值、無校正、連續校正三種結果。

    參數
        n        : 試驗次數
        p        : 每次成功機率
        query    : 條件，例如 '25 <= X <= 30'（可省略，省略只畫圖）
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
    回傳
        ax
    例
        sk.normal_approx(50, 0.5, '25 <= X <= 30')
    """
    b = Binom(n, p)
    mu, sd = n * p, math.sqrt(n * p * (1 - p))
    nd = Normal(mu, sd)
    ax = new_ax(ax, figsize=(8, 5))
    xs = np.arange(0, n + 1)
    lo, hi = max(0, mu - 4.5 * sd), min(n, mu + 4.5 * sd)
    keep = (xs >= lo) & (xs <= hi)
    ax.bar(xs[keep], b.frozen.pmf(xs[keep]), color=FACE, edgecolor=EDGE, width=0.9)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    grid = np.linspace(lo - 0.5, hi + 0.5, 400)
    ax.plot(grid, nd.frozen.pdf(grid), color=ACCENT, lw=2, label=f"ND({fmt(round(mu, 4))}, {sd:.4f})")
    ax.set_title(f"Bi(n={fmt(n)}, p={fmt(p)}) vs normal approximation")
    ax.set_xlabel("x")
    ax.set_ylabel("Probability")
    ax.legend()

    print(f"μ = np = {mu:.4f}，σ = √(np(1-p)) = {sd:.4f}")
    ok = n >= 25 and mu > 5 and n * (1 - p) > 5
    print(f"n = {n}，np = {mu:.2f}，n(1-p) = {n * (1 - p):.2f}　"
          f"講義的經驗法則 n ≥ 25、np > 5、n(1-p) > 5：{'符合' if ok else '不符合，近似可能不準'}")
    if query is None:
        return ax
    exact = _evaluate(b, query)
    lower, upper, eq = _parse(query)
    raw_lo = lower[0] if lower else None
    raw_hi = upper[0] if upper else None
    L, U = exact["region"] if exact["region"] else (None, None)
    cc_lo = None if L is None else L - 0.5
    cc_hi = None if U is None else U + 0.5

    def ncode(a, c):
        sc = f"loc={fmt(round(mu, 6))}, scale={fmt(round(sd, 6))}"
        parts = []
        if c is not None:
            parts.append(f"stats.norm.cdf(x={fmt(c)}, {sc})")
        if a is not None:
            parts.append(f"stats.norm.cdf(x={fmt(a)}, {sc})")
        if a is None:
            return parts[0]
        if c is None:
            return f"1 - {parts[0]}"
        return f"{parts[0]} - {parts[1]}"

    def nval(a, c):
        hi_v = 1.0 if c is None else nd.frozen.cdf(c)
        lo_v = 0.0 if a is None else nd.frozen.cdf(a)
        return float(hi_v - lo_v)

    print(f"二項精確值　{exact['title']} = {exact['math']} = {exact['value']:.4f}")
    print(f"　　程式碼：{exact['expr']}")
    if eq is None:
        v = nval(raw_lo, raw_hi)
        print(f"常態近似（無校正）= {v:.4f}")
        print(f"　　程式碼：{ncode(raw_lo, raw_hi)}")
    v = nval(cc_lo, cc_hi)
    rng = f"[{fmt(cc_lo) if cc_lo is not None else '-∞'}, {fmt(cc_hi) if cc_hi is not None else '∞'}]"
    print(f"常態近似（連續校正，Y ∈ {rng}）= {v:.4f}")
    print(f"　　程式碼：{ncode(cc_lo, cc_hi)}")
    return ax


# ---------------------------------------------------------------- 互動 UI

# 分布：(顯示名稱, 建構函式, [(參數, 預設值, 是否整數, 說明)], X 的意義, scipy 引數說明)
_SPECS = {
    "binom": ("二項 Bi(n, p)", Binom,
              [("n", 10, True, "試驗次數（正整數）"), ("p", 0.4, False, "每次試驗成功的機率（0～1）")],
              "X = n 次獨立試驗中成功的次數，X = 0, 1, …, n",
              "k：成功次數、n：試驗次數、p：每次成功機率"),
    "poisson": ("卜瓦松 Poi(λ)", Poisson,
                [("λ", 4, False, "單位時間（或單位區間）內平均發生次數（> 0），時間單位要跟題目一致")],
                "X = 單位時間內發生的次數，X = 0, 1, 2, …",
                "k：發生次數、mu：λ（平均次數）"),
    "hypergeom": ("超幾何 Hyper(N, K, n)", Hypergeom,
                  [("N", 20, True, "母體總數"), ("K", 12, True, "母體中「成功」的個數（≤ N）"),
                   ("n", 10, True, "抽出的個數（不放回，≤ N）")],
                  "X = 不放回抽出的 n 個裡，成功的個數",
                  "k：成功個數、M：母體總數 N、n：成功數 K、N：抽出數 n（scipy 的名稱跟課本不一樣！）"),
    "geom": ("幾何 Geo(p)", Geom,
             [("p", 0.4, False, "每次試驗成功的機率（0～1）")],
             "X = 第一次成功發生在第幾次試驗，X = 1, 2, 3, …",
             "k：第幾次試驗、p：每次成功機率"),
    "uniform": ("均勻 Uni(a, b)", Uniform,
                [("a", 10, False, "下限"), ("b", 16, False, "上限（要大於 a）")],
                "X 在 [a, b] 之間，每個值的機率密度都一樣",
                "x：要查的值、loc：下限 a、scale：寬度 b − a"),
    "expon": ("指數 Exp(λ)（λ = 發生率）", Expon,
              [("λ", 6.6, False, "發生率：每單位時間平均發生幾次（> 0），平均等待時間 = 1/λ")],
              "X = 兩次發生之間的等待時間（X ≥ 0）",
              "x：時間長度（單位要跟 λ 一致）、scale：1/λ（平均等待時間）"),
    "norm": ("常態 ND(μ, σ)", Normal,
             [("μ", 80, False, "平均數"), ("σ", 10, False, "標準差（> 0），不是變異數")],
             "鐘形分布，以 μ 為中心左右對稱",
             "x：要查的值、loc：平均數 μ、scale：標準差 σ"),
}

_MODES = [
    ("Pr(X ≤ x)", "le"), ("Pr(X < x)", "lt"), ("Pr(X ≥ x)", "ge"), ("Pr(X > x)", "gt"),
    ("Pr(X = x)", "eq"), ("Pr(a ≤ X ≤ b)", "between"), ("自訂條件（例：2 < X <= 5）", "custom"),
    ("反查：Pr(X ≤ x) = q，求 x", "ppf"), ("反查：Pr(X ≥ x) = q，求 x", "isf"),
    ("平均數與變異數", "moments"),
]

# 問題類型的說明：(共通說明, 離散分布的提醒, 連續分布的提醒)
_MODE_HELP = {
    "le": ("Pr(X ≤ x)：X 不超過 x（至多 x）的機率 = F(x)", "", ""),
    "lt": ("Pr(X < x)：X 小於 x 的機率", "離散：= F(x − 1)", "連續：跟 Pr(X ≤ x) 一樣 = F(x)"),
    "ge": ("Pr(X ≥ x)：X 至少 x 的機率", "離散：= 1 − F(x − 1)，<b>要減 1！</b>", "連續：= 1 − F(x)"),
    "gt": ("Pr(X > x)：X 超過 x 的機率 = 1 − F(x)", "", ""),
    "eq": ("Pr(X = x)：剛好等於 x 的機率", "離散：用 pmf", "連續：單點機率一定是 0"),
    "between": ("Pr(a ≤ X ≤ b)：介於 a、b 之間（含兩端）", "離散：= F(b) − F(a − 1)", "連續：= F(b) − F(a)"),
    "custom": ("自訂條件：例如 <code>2 &lt; X &lt;= 5</code>、<code>X &gt;= 10</code>、<code>3 &gt; X</code>，"
               "數字可以寫算式，例如 <code>25/60</code>", "", ""),
    "ppf": ("反查左尾：給累積機率 q，找 x 使 Pr(X ≤ x) = q（第 100q 百分位數，scipy 的 ppf）",
            "離散：回傳 F(x) ≥ q 的最小 x", ""),
    "isf": ("反查右尾：給機率 q，找 x 使 Pr(X ≥ x) = q，等於 ppf(1 − q)",
            "離散：回傳 F(x) ≥ 1 − q 的最小 x", ""),
    "moments": ("平均數 E[X]、變異數 Var(X)、標準差 SD(X)", "", ""),
}

_INPUT_HELP = {
    "x": "要查的值", "a": "區間下限（含）", "b": "區間上限（含）",
    "q": "機率（0～1）", "條件": "自訂條件，例如 2 < X <= 5",
}


def explore(dist="norm"):
    """互動式分布計算機：選分布、填參數、選問題，會即時畫圖並產生可以貼進答案的程式碼。

    每個參數都有說明（滑鼠停在輸入框上，或看下方的說明區）。
    匯出 HTML 後互動元件不會動，所以請把下方產生的程式碼貼到新的 cell 執行。

    參數
        dist     : 一開始顯示的分布：'binom'、'poisson'、'hypergeom'、'geom'、'uniform'、'expon'、'norm'
    例
        sk.explore()
        sk.explore('binom')
    """
    import ipywidgets as W
    from IPython.display import HTML, display

    lay = W.Layout(width="210px")
    dd = W.Dropdown(options=[(v[0], k) for k, v in _SPECS.items()], value=dist,
                    description="分布", layout=W.Layout(width="330px"))
    mode = W.Dropdown(options=_MODES, value="le", description="問題", layout=W.Layout(width="330px"))
    xw = W.FloatText(value=70, description="x", tooltip=_INPUT_HELP["x"], layout=lay)
    aw = W.FloatText(value=60, description="a", tooltip=_INPUT_HELP["a"], layout=lay)
    bw = W.FloatText(value=90, description="b", tooltip=_INPUT_HELP["b"], layout=lay)
    qw = W.BoundedFloatText(value=0.95, min=0, max=1, step=0.01, description="q",
                            tooltip=_INPUT_HELP["q"], layout=lay)
    cw = W.Text(value="70 < X <= 90", description="條件", tooltip=_INPUT_HELP["條件"],
                layout=W.Layout(width="330px"))
    kind = W.ToggleButtons(options=[("PMF / PDF", "pdf"), ("CDF", "cdf")], value="pdf")
    params = W.HBox()
    help_box = W.HTML()
    out = W.Output()
    code = W.Textarea(layout=W.Layout(width="100%", height="120px"))
    state = {"widgets": []}

    def build_params(*_):
        for w in state["widgets"]:
            w.unobserve(refresh, names="value")
        ws = []
        for name, default, is_int, tip in _SPECS[dd.value][2]:
            w = (W.IntText if is_int else W.FloatText)(value=default, description=name, tooltip=tip, layout=lay)
            w.observe(refresh, names="value")
            ws.append(w)
        state["widgets"] = ws
        params.children = ws

    def show_inputs():
        m = mode.value
        vis = {xw: m in ("le", "lt", "ge", "gt", "eq"), aw: m == "between", bw: m == "between",
               qw: m in ("ppf", "isf"), cw: m == "custom"}
        for w, on in vis.items():
            w.layout.display = None if on else "none"

    def query():
        x, a, b = fmt(xw.value), fmt(aw.value), fmt(bw.value)
        return {"le": f"X <= {x}", "lt": f"X < {x}", "ge": f"X >= {x}", "gt": f"X > {x}",
                "eq": f"X == {x}", "between": f"{a} <= X <= {b}", "custom": cw.value}.get(mode.value)

    def arg_text():
        return _SPECS[dd.value][4] + ("、q：累積機率" if mode.value in ("ppf", "isf") else "")

    def show_help():
        label, _, specs, meaning, _ = _SPECS[dd.value]
        discrete = dd.value in ("binom", "poisson", "hypergeom", "geom")
        common, d_note, c_note = _MODE_HELP[mode.value]
        note = d_note if discrete else c_note
        rows = "".join(f"<li><b>{n}</b>：{tip}</li>" for n, _, _, tip in specs)
        help_box.value = (
            "<div style='font-size:13px;line-height:1.6;border-left:3px solid #2a78d6;"
            "padding:2px 10px;margin:4px 0'>"
            f"<b>{label}</b>：{meaning}（{'離散' if discrete else '連續'}分布）"
            f"<ul style='margin:2px 0 2px 18px;padding:0'>{rows}</ul>"
            f"<b>問題</b>：{common}{'；' + note if note else ''}<br>"
            f"<b>程式碼的引數</b>：{arg_text()}</div>")

    def refresh(*_):
        show_inputs()
        show_help()
        out.clear_output(wait=True)
        with out:
            try:
                d = _SPECS[dd.value][1](*[w.value for w in state["widgets"]])
                m = mode.value
                if m == "moments":
                    mm = moments(d, show=False)
                    html = (f"<b>{d.label}</b>：E[X] = {mm['mean']:.4f}，Var(X) = {mm['var']:.4f}，"
                            f"SD(X) = {mm['std']:.4f}")
                    snippet = (f"from scipy import stats\n# {d.label}\n# 引數：{arg_text()}\n"
                               f"print(stats.{d.name}.mean({d.kw}), stats.{d.name}.var({d.kw}))")
                    plot_dist(d, kind=kind.value)
                elif m in ("ppf", "isf"):
                    tail = "left" if m == "ppf" else "right"
                    x = quantile(d, qw.value, tail=tail, show=False)
                    qtxt = fmt(qw.value) if tail == "left" else f"1 - {fmt(qw.value)}"
                    expr = d.code("ppf", "q", qtxt)
                    cond = "≤" if tail == "left" else "≥"
                    html = f"<b>{d.label}</b>：Pr(X {cond} x) = {fmt(qw.value)}　→　x = <b>{x:.4f}</b>"
                    if d.discrete:
                        html += "（離散：F(x) ≥ q 的最小 x）"
                    snippet = (f"from scipy import stats\n# {d.label}\n# Pr(X {cond} x) = {fmt(qw.value)}\n"
                               f"# 引數：{arg_text()}\nprint(round({expr}, 4))")
                    plot_dist(d, (f"X <= {fmt(x)}" if tail == "left" else f"X >= {fmt(x)}"), kind=kind.value)
                else:
                    r = _evaluate(d, query())
                    html = f"<b>{d.label}</b>：{r['title']} = {r['math']} = <b>{r['value']:.4f}</b>"
                    snippet = (f"from scipy import stats\n# {d.label}\n# {r['title']} = {r['math']}\n"
                               f"# 引數：{arg_text()}\nprint(round({r['expr']}, 4))")
                    plot_dist(d, query(), kind=kind.value)
                plt.show()
                display(HTML(f"<div style='font-size:15px;margin:4px 0'>{html}</div>"))
                code.value = snippet
            except Exception as e:  # 參數不合法時顯示訊息，不讓 UI 壞掉
                plt.close("all")
                print("⚠", e)
                code.value = ""

    def on_dist(*_):
        build_params()
        refresh()

    dd.observe(on_dist, names="value")
    for w in (mode, xw, aw, bw, qw, cw, kind):
        w.observe(refresh, names="value")
    build_params()
    refresh()
    display(W.VBox([
        W.HBox([dd, mode]), params, W.HBox([xw, aw, bw, qw, cw]), help_box, kind, out,
        W.HTML("<b>程式碼（貼到新的 cell 執行，HTML 才會保留答案）：</b>"), code,
    ]))
