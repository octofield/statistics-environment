"""statkit 自我測試：跟作業/講義的答案比對，並確認產生的程式碼執行結果一致。

    python -m statkit.selftest
"""
import io
import math
import statistics
import sys
from contextlib import redirect_stdout

import matplotlib

matplotlib.use("Agg")

from scipy import stats  # noqa: E402

import statkit as sk  # noqa: E402
from statkit.dist import _evaluate  # noqa: E402

HEIGHTS = [178, 172, 175, 184, 172, 175, 165, 178, 177, 175,
           180, 182, 177, 183, 180, 178, 179, 162, 170, 171]   # 講義 03a


def _cases():
    # (分布, 條件, 用 scipy 直接算的正確答案)
    return [
        (sk.Binom(20, 0.1), "X <= 3", stats.binom.cdf(3, 20, 0.1)),                 # HW05
        (sk.Poisson(6.6), "X >= 10", stats.poisson.sf(9, 6.6)),                     # HW05
        (sk.Poisson(2), "P(X ≤ 3)", stats.poisson.cdf(3, 2)),
        (sk.Poisson(2), "X > 4", stats.poisson.sf(4, 2)),
        (sk.Uniform(10, 16), "X > 15", stats.uniform.sf(15, 10, 6)),                # HW05
        (sk.Expon(6.6), "X > 25/60", stats.expon.sf(25 / 60, scale=1 / 6.6)),       # HW05
        (sk.Expon(6.6), "X <= 5/60", stats.expon.cdf(5 / 60, scale=1 / 6.6)),
        (sk.Hypergeom(20, 12, 10), "X == 7", stats.hypergeom.pmf(7, 20, 12, 10)),   # 04c
        (sk.Hypergeom(5, 2, 3), "X <= 1", stats.hypergeom.cdf(1, 5, 2, 3)),
        (sk.Geom(0.4), "X = 5", stats.geom.pmf(5, 0.4)),
        (sk.Binom(50, 0.5), "25 <= X <= 30", stats.binom.cdf(30, 50, .5) - stats.binom.cdf(24, 50, .5)),  # 06a
        (sk.Binom(10, 0.4), "2 < X < 5", stats.binom.pmf(3, 10, .4) + stats.binom.pmf(4, 10, .4)),
        (sk.Binom(10, 0.4), "X > 2.5", stats.binom.sf(2, 10, .4)),
        (sk.Binom(10, 0.4), "3 >= X", stats.binom.cdf(3, 10, .4)),
        (sk.Binom(10, 0.4), ">= 4", stats.binom.sf(3, 10, .4)),
        (sk.Binom(10, 0.4), "7 > X >= 2", stats.binom.cdf(6, 10, .4) - stats.binom.cdf(1, 10, .4)),
        (sk.Normal(6.5, 2), "X >= 10", 1 - stats.norm.cdf(10, 6.5, 2)),            # 06a
        (sk.Normal(80, 10), "70 < X < 90", stats.norm.cdf(90, 80, 10) - stats.norm.cdf(70, 80, 10)),
        (stats.binom(20, 0.06), "X == 0", stats.binom.pmf(0, 20, 0.06)),            # scipy frozen
        (stats.norm(80, 10), "X <= 70", stats.norm.cdf(70, 80, 10)),
        (sk.Discrete(range(9), APPLE), "X <= 4", 0.82),                             # 04b
    ]


APPLE = [0.06, 0.15, 0.22, 0.22, 0.17, 0.10, 0.05, 0.02, 0.01]   # 講義 04b 蘋果需求


def run(verbose=True):
    failures = []
    count = [0]

    def check(name, got, want, tol=1e-9):
        count[0] += 1
        ok = math.isclose(got, want, rel_tol=tol, abs_tol=tol)
        if not ok:
            failures.append(f"{name}: got {got}, want {want}")
        return ok

    for d, q, want in _cases():
        d = sk.dist._as_dist(d)
        r = _evaluate(d, q)
        check(f"{d.label} {q}", r["value"], want)
        ns = {"stats": stats}
        if d.setup:
            exec(d.setup, ns)
        check(f"{d.label} {q}（產生的程式碼）", float(eval(r["expr"], ns)), want)

    # 反查
    check("geom ppf", sk.quantile(sk.Geom(0.4), 0.8, show=False), stats.geom.ppf(0.8, 0.4))
    check("norm ppf", sk.quantile(sk.Normal(6.5, 2), 0.6, show=False), stats.norm.ppf(0.6, 6.5, 2))
    check("uniform isf", sk.quantile(sk.Uniform(10, 16), 0.01, tail="right", show=False),
          stats.uniform.isf(0.01, 10, 6))

    # 應用（講義 04b / 05 的答案）
    with redirect_stdout(io.StringIO()):
        check("newsvendor q*=40", sk.newsvendor(sk.Uniform(20, 50), co=5, cu=10), 40)
        check("newsvendor q**=42", sk.newsvendor(sk.Uniform(20, 50), co=4, cu=11), 42)
        check("80% 服務水準", sk.quantile(sk.Discrete(range(9), APPLE), 0.8, show=False), 4)
        table = sk.inventory_profit(sk.Discrete(range(9), APPLE), price=10, cost=2)
    best = table["期望利潤"].idxmax()
    brute = max(range(9), key=lambda y: sum(p * (10 * min(y, x) - 2 * y) for x, p in enumerate(APPLE)))
    check("期望利潤最大的進貨量", best, brute)
    check("taxi or bus", sk.prob(sk.Expon(1 / 12), "X > 10", show=False), math.exp(-10 / 12))   # 05

    # 讀資料：Excel 多個工作表、Big5（cp950）編碼的 CSV
    import tempfile
    import pandas as pd
    with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
        xlsx = f"{tmp}/t.xlsx"
        with pd.ExcelWriter(xlsx) as w:
            pd.DataFrame({"a": [1, 2, None], "b": [4, 5, 6]}).to_excel(w, sheet_name="first", index=False)
            pd.DataFrame({"身高": HEIGHTS}).to_excel(w, sheet_name="第二", index=False)
        df1 = sk.peek(xlsx)
        df2 = sk.peek(xlsx, sheet="第二")
        csv = f"{tmp}/t.csv"
        pd.DataFrame({"地區": ["北", "南"], "值": [1, 2]}).to_csv(csv, index=False, encoding="cp950")
        df3 = sk.peek(csv)
    check("peek 第一個工作表", len(df1), 3)
    check("peek 指定工作表", df2["身高"].sum(), sum(HEIGHTS))
    check("peek cp950 CSV", int(df3.loc[df3["地區"] == "南", "值"].iloc[0]), 2)

    # 敘述統計（講義 03a 的寫法）
    desc = sk.describe(HEIGHTS)
    q = statistics.quantiles(HEIGHTS, n=4)
    check("Q1", desc.loc["Q1（exclusive）", "值"], round(q[0], 4))
    check("樣本標準差", desc.loc["樣本標準差 s", "值"], round(statistics.stdev(HEIGHTS), 4))
    with redirect_stdout(io.StringIO()):
        ft = sk.freq_table(HEIGHTS, edges=list(range(160, 196, 4)))
        cheb = sk.chebyshev(HEIGHTS, ks=(2,))
        sk.plot_dist(sk.Poisson(4), "X >= 3")
        sk.plot_dist(sk.Normal(80, 10), "70 < X < 90", kind="cdf")
        sk.hist_classes(HEIGHTS, start=160, width=4)
        sk.normal_approx(50, 0.5, "25 <= X <= 30")
        sk.box([HEIGHTS, HEIGHTS])
        sk.sample_means(sk.Normal(80, 4), n=9, reps=200, seed=1)
        sk.estimate_pi(200, seed=1, plot=False)
    check("freq_table 總數", ft["次數"].sum(), len(HEIGHTS))
    mu, sd = statistics.mean(HEIGHTS), statistics.pstdev(HEIGHTS)
    within = sum(mu - 2 * sd <= v <= mu + 2 * sd for v in HEIGHTS) / len(HEIGHTS)
    check("chebyshev k=2", cheb.loc[2, "實際比例"], round(within, 4))

    if verbose:
        if failures:
            print("statkit 自我測試失敗：")
            for f in failures:
                print("  ✗", f)
        else:
            print(f"statkit 自我測試通過（{count[0]} 項）")
    return not failures


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
