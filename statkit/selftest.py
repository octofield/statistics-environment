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

    # 多個變數：跟 pandas / numpy 直接算的結果比對
    import numpy as np
    weights = [h * 0.4 - 2 + (i % 5) for i, h in enumerate(HEIGHTS)]
    multi = pd.DataFrame({"身高": HEIGHTS, "體重": weights, "組": ["A", "B"] * 10})
    with redirect_stdout(io.StringIO()):
        cols = sk.describe_cols(multi, ["身高", "體重"])
        by = sk.describe_by(multi, "身高", by="組")
        r = sk.corr_matrix(multi, ["身高", "體重"])
        pcov = sk.corr_matrix(multi, ["身高", "體重"], kind="cov", ddof=0)
        sk.scatter_matrix(multi, ["身高", "體重"])
        sk.scatter_by(multi, "身高", "體重", by="組")
        sk.box_by(multi, "身高", by="組")
        sk.bar_grouped(multi.pivot_table(index="組", values=["身高", "體重"]), stacked=True)
    check("describe_cols Q1", cols.loc["Q1", "身高"], round(q[0], 4))
    check("describe_by 平均數", by.loc["B", "平均數"], round(multi.groupby("組")["身高"].mean()["B"], 4))
    check("corr_matrix r", r.loc["身高", "體重"], round(np.corrcoef(HEIGHTS, weights)[0, 1], 4))
    check("corr_matrix 母體共變異數", pcov.loc["身高", "體重"], round(np.cov(HEIGHTS, weights, ddof=0)[0, 1], 4))

    # 常態的運算、樣本平均數（講義 06a）
    with redirect_stdout(io.StringIO()):
        xbar = sk.Normal(80, 10).sample_mean(4)
        check("06a 例題 1 Pr(X̄ > 82)", round(xbar.P("X > 82", show=False), 3), 0.345)
        check("06a 例題 1 Pr(X̄ < 76)", round(xbar.P("X < 76", show=False), 3), 0.212)
        check("06a Pepsi Pr(X̄ ≥ 1.316)", round(sk.Normal(1.189, 0.049).P("X >= 1.316", show=False), 4), 0.0048)
        X, Y = sk.Normal(50, 6), sk.Normal(20, 2)
        W = 3 - 2 * X + 0.5 * Y
        check("線性組合 μ", W.mu, 3 - 100 + 10)
        check("線性組合 σ", W.sigma, math.sqrt(4 * 36 + 0.25 * 4))
        # eval 只執行 statkit 自己產生的程式碼字串，確認貼進答案的寫法算出來一樣
        check("線性組合的程式碼", float(eval(f"stats.norm.cdf(x=-80, {W.kw})", {"stats": stats, "math": math})),
              stats.norm.cdf(-80, -87, math.sqrt(145)))
        check("同一個變數相加 X + X = 2X", (X + X).sigma, 12)
        check("或：雙尾", sk.Normal(6.5, 2).P("X >= 10 or X <= 0", show=False),
              stats.norm.sf(10, 6.5, 2) + stats.norm.cdf(0, 6.5, 2))
        check("或：離散", sk.Binom(10, 0.3).P("X <= 1 或 X >= 6", show=False),
              stats.binom.cdf(1, 10, 0.3) + stats.binom.sf(5, 10, 0.3))
        check("sample_size", sk.sample_size(10, 2, 0.95), 97)
        a, b = sk.middle_interval(sk.Normal(0, 1), 0.95)
        check("middle_interval", b, stats.norm.ppf(0.975))

        # 分組中位數、z 分數離群值（講義 03b）
        check("03b 分組中位數", round(sk.grouped_median([160, 164, 168, 172, 176, 180, 184, 188],
                                                      [1, 1, 2, 5, 6, 4, 1]), 2), 176.67)
        check("z 分數離群值", len(sk.outliers_z(HEIGHTS + [250])), 1)

        # 聯合機率表（講義 04a）、兩個隨機變數
        dry = sk.joint([[0.459, 0.051], [0.111, 0.379]], xs=["I", "U"], ys=["S", "N"], conditional="x")
        check("04a Pr(S|U)", round(dry["cond_y_given_x"].loc["U", "S"], 3), 0.227)
        check("04a p37 獨立", sk.joint([[0.21, 0.35, 0.14], [0.09, 0.15, 0.06]])["independent"], True)
        un = sk.joint([[0.2, 0.1, 0.3], [0.1, 0.2, 0.1]], xs=[2, 3], ys=[1, 4, 5])
        check("不相關但不獨立 Cov", un["cov"], 0)
        check("不相關但不獨立", un["independent"], False)

        # 貝氏後驗、E[g(X)]
        post = sk.posterior({0.3: 0.5, 0.7: 0.5}, lambda p: stats.binom.pmf(2, 3, p))
        lik = [stats.binom.pmf(2, 3, 0.3), stats.binom.pmf(2, 3, 0.7)]
        check("posterior", post.loc["0.7", "後驗"], round(lik[1] / sum(lik), 4))
        g = lambda x: 3 * x + 10 * (x >= 6) - 5 * (x <= 2)
        check("expect", sk.expect(sk.Poisson(4), g),
              3 * 4 + 10 * stats.poisson.sf(5, 4) - 5 * stats.poisson.cdf(2, 4), tol=1e-8)

        # 疊圖、美化（只確認跑得過）
        sk.hist_classes(HEIGHTS, start=160, width=4, density=True, fit="norm")
        sk.freq_polygon(HEIGHTS, start=160, width=4, with_hist=True)
        sk.tidy(sk.bar(["A", "B", "A"]), bar_labels=True, thousands=True)
        sk.corr_matrix(multi, ["身高", "體重"], plot=True)
        sk.plot_dist(xbar, "X <= 76 or X >= 84")

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
