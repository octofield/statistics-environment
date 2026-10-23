"""statkit — 統計學考試用小工具。

    import statkit as sk
    sk.setup()          # 字體大小、中文字型
    sk.help()           # 中文功能列表
    sk.explore()        # 互動式分布計算機（會產生可以貼進答案的程式碼）
"""
from ._style import setup
from .data import peek
from .desc import (chebyshev, corr_matrix, cov_corr, describe, describe_by, describe_cols, empirical_rule,
                   freq_table, grouped_stats, outliers_iqr, percent_rank, quantiles, zscore)
from .dist import (Binom, Discrete, Dist, Expon, Geom, Hypergeom, Normal, Poisson, Uniform, explore,
                   inventory_profit, moments, newsvendor, normal_approx, plot_dist, prob, quantile)
from .plots import (bar, bar_grouped, box, box_by, hist, hist_classes, ogive, pareto, pie, qq_plot, scatter_by,
                    scatter_matrix, scatter_r, stem_leaf)
from .sim import estimate_pi, monty_hall, sample_means

__version__ = "1.0.0"

_HELP = """
statkit 功能列表　（每個函式都可以用 help(sk.函式名) 或 Shift+Tab 看說明）

【設定】
  sk.setup(size=16, dpi=100)                 字體大小、圖的解析度、中文字型

【讀資料】
  df = sk.peek('../data/檔名.xlsx')          看工作表、欄位、缺值、前幾列，並印出讀檔程式碼

【敘述統計】
  sk.describe(x)                             平均/中位/眾數/四分位/變異數/標準差/偏態/峰態 + 寫法
  sk.freq_table(x, start=0, width=5000)      次數分配表、眾數組（組中點）
  sk.quantiles(x, n=4)                       四分位數（n=100 為百分位數）
  sk.percent_rank(x, 10000)                  百分等級
  sk.outliers_iqr(x, k=1.5)                  1.5 IQR 規則找離群值
  sk.chebyshev(x, ks=(1.5, 2))               驗證柴比雪夫定理（預設母體標準差 ddof=0）
  sk.empirical_rule(x)                       經驗法則 68 / 95 / 99.7
  sk.zscore(x, ddof=1)                       z 分數
  sk.cov_corr(x, y)                          共變異數（母體/樣本）、相關係數
  sk.grouped_stats(mid, freq)                分組資料的平均數與變異數

【畫圖】（都回傳 ax，可再調整）
  sk.hist_classes(x, start=0, width=5000)    依組界的直方圖
  sk.hist(x, bins=10, normal=True)           直方圖 + 常態曲線
  sk.ogive(x, start=0, width=5000)           肩形圖（累積次數）
  sk.box([a, b, c], labels=[...])            盒鬚圖（多組）
  sk.scatter_r(x, y, fit=True)               散佈圖 + r + 迴歸線
  sk.bar(cats) / sk.pie(cats) / sk.pareto(cats)
  sk.stem_leaf(x, stem_unit=10)              莖葉圖（文字）
  sk.qq_plot(x)                              常態 Q-Q 圖

【多個變數】（df 是讀進來的 DataFrame）
  sk.describe_cols(df, ['Food', 'Income'])   多個欄位的統計量並排比較
  sk.describe_by(df, 'Food', by='Region')    依類別分組的統計量（groupby）
  sk.corr_matrix(df, ['Food', 'Income', 'Debt'])        相關係數矩陣（kind='cov' 為共變異數）
  sk.scatter_matrix(df, ['Food', 'Income', 'Debt'])     兩兩散佈圖 + r
  sk.scatter_by(df, 'Debt', 'Food', by='Region')        依類別上色的散佈圖 + 各組 r
  sk.box_by(df, 'Food', by='Region')         依類別分組的盒鬚圖
  sk.bar_grouped(pd.crosstab(df['A'], df['B']))         分組長條圖（stacked=True 堆疊）

【機率分布】（參數用課本的記號）
  sk.Binom(n, p)   sk.Poisson(λ)   sk.Hypergeom(N, K, n)   sk.Geom(p)
  sk.Uniform(a, b) sk.Expon(λ)     sk.Normal(μ, σ)
  sk.Discrete([0, 1, 2], [0.25, 0.5, 0.25])  自訂機率表
  X.P("X >= 10")                             機率（自動處理離散的 ≥ / >），印出課程寫法的程式碼
  sk.prob(X, "2 < X <= 5")                   同上；X 也可以是 scipy 的 stats.norm(80, 10)
  sk.quantile(X, 0.95, tail="left")          反查 x（tail="right" 為 Pr(X ≥ x) = q）
  sk.moments(X)                              平均數、變異數、標準差
  sk.plot_dist(X, "X >= 10", kind="pdf")     PMF/PDF/CDF 圖 + 塗色區間
  sk.normal_approx(n, p, "25 <= X <= 30")    二項的常態近似（有/無連續校正）
  sk.explore()                               互動式分布計算機

【應用】
  sk.newsvendor(sk.Uniform(20, 50), co=5, cu=10)        報童模型最適訂購量
  sk.inventory_profit(D, price=10, cost=2)              離散需求下各進貨量的期望利潤

【模擬】
  sk.sample_means(sk.Normal(80, 4), n=9)     抽樣平均數分布（中央極限定理）
  sk.estimate_pi(1000)                       蒙地卡羅估 π
  sk.monty_hall(10000)                       三門問題
"""


def help():  # noqa: A001 — 刻意用 sk.help() 這個名字
    print(_HELP)
