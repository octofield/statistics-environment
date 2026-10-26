"""statkit — 統計學考試用小工具。

    import statkit as sk
    sk.setup()          # 字體大小、中文字型
    sk.help()           # 中文功能列表
    sk.explore()        # 互動式分布計算機（會產生可以貼進答案的程式碼；VS Code 顯示不出來就用 text=True）
"""
from ._style import setup
from .data import peek
from .desc import (chebyshev, corr_matrix, cov_corr, describe, describe_by, describe_cols, empirical_rule,
                   freq_table, grouped_median, grouped_stats, outliers_iqr, outliers_z, percent_rank, quantiles,
                   zscore)
from .dist import (Binom, Discrete, Dist, Expon, Geom, Hypergeom, Normal, NormalDist, Poisson, Uniform, explore,
                   inventory_profit, middle_interval, moments, newsvendor, normal_approx, plot_dist, prob,
                   quantile, sample_size)
from .plots import (bar, bar_grouped, box, box_by, freq_polygon, hist, hist_classes, ogive, pareto, pie, qq_plot,
                    scatter_by, scatter_matrix, scatter_r, stem_leaf, tidy)
from .rv import expect, joint, posterior
from .sim import estimate_pi, monty_hall, sample_means

__version__ = "1.2.1"

_HELP = """
statkit 功能列表　（每個函式都可以用 help(sk.函式名) 或 Shift+Tab 看說明）

【設定】
  sk.setup(size=16, dpi=100)                 字體大小、圖的解析度、中文字型

【讀資料】
  df = sk.peek('檔名.xlsx')                  看工作表、欄位、缺值、前幾列，並印出讀檔程式碼

【敘述統計】
  sk.describe(x)                             平均/中位/眾數/四分位/變異數/標準差/偏態/峰態 + 寫法
  sk.freq_table(x, start=0, width=5000)      次數分配表、眾數組（組中點）
  sk.quantiles(x, n=4)                       四分位數（n=100 為百分位數）
  sk.percent_rank(x, 10000)                  百分等級
  sk.outliers_iqr(x, k=1.5)                  1.5 IQR 規則找離群值
  sk.outliers_z(x, k=3)                      |z| > 3 找離群值
  sk.chebyshev(x, ks=(1.5, 2))               驗證柴比雪夫定理（預設母體標準差 ddof=0）
  sk.empirical_rule(x)                       經驗法則 68 / 95 / 99.7
  sk.zscore(x, ddof=1)                       z 分數（平均數 0、標準差 1）
  sk.cov_corr(x, y)                          共變異數（母體/樣本）、相關係數
  sk.grouped_stats(mid, freq)                分組資料的平均數與變異數
  sk.grouped_median(table)                   分組資料的中位數（內插法）

【畫圖】（都回傳 ax，可再調整）
  sk.hist_classes(x, start=0, width=5000)    依組界的直方圖；fit='norm' 疊常態曲線、density=True 畫密度
  sk.hist(x, bins=10, normal=True)           直方圖 + 常態曲線
  sk.freq_polygon(x, start=0, width=5000)    次數多邊形（with_hist=True 疊在直方圖上）
  sk.ogive(x, start=0, width=5000)           肩形圖（累積次數）
  sk.box([a, b, c], labels=[...])            盒鬚圖（多組）
  sk.scatter_r(x, y, fit=True)               散佈圖 + r + 迴歸線
  sk.bar(cats) / sk.pie(cats) / sk.pareto(cats)
  sk.stem_leaf(x, stem_unit=10)              莖葉圖（文字）
  sk.qq_plot(x)                              常態 Q-Q 圖
  sk.tidy(ax, bar_labels=True)               讓圖更好看：去框線、淡格線、千分位、長條標數值

【多個變數】（df 是讀進來的 DataFrame）
  sk.describe_cols(df, ['Food', 'Income'])   多個欄位的統計量並排比較
  sk.describe_by(df, 'Food', by='Region')    依類別分組的統計量（groupby）
  sk.corr_matrix(df, ['Food', 'Income', 'Debt'])        相關係數矩陣（kind='cov' 共變異數、plot=True 熱圖）
  sk.scatter_matrix(df, ['Food', 'Income', 'Debt'])     兩兩散佈圖 + r
  sk.scatter_by(df, 'Debt', 'Food', by='Region')        依類別上色的散佈圖 + 各組 r
  sk.box_by(df, 'Food', by='Region')         依類別分組的盒鬚圖
  sk.bar_grouped(pd.crosstab(df['A'], df['B']))         分組長條圖（stacked=True 堆疊）

【機率分布】（參數用課本的記號）
  sk.Binom(n, p)   sk.Poisson(λ)   sk.Hypergeom(N, K, n)   sk.Geom(p)
  sk.Uniform(a, b) sk.Expon(λ)     sk.Normal(μ, σ)
  sk.Discrete([0, 1, 2], [0.25, 0.5, 0.25])  自訂機率表
  X.P("X >= 10")                             機率（自動處理離散的 ≥ / >），印出課程寫法的程式碼
  X.P("X <= 114 or X >= 126")                兩邊的尾巴（偏離超過某個值）
  sk.prob(X, "2 < X <= 5")                   同上；X 也可以是 scipy 的 stats.norm(80, 10)
  sk.quantile(X, 0.95, tail="left")          反查 x（tail="right" 為 Pr(X ≥ x) = q）
  sk.middle_interval(X, 0.95)                包含中間 95% 的區間
  sk.moments(X)                              平均數、變異數、標準差
  sk.plot_dist(X, "X >= 10", kind="pdf")     PMF/PDF/CDF 圖 + 塗色區間
  sk.normal_approx(n, p, "25 <= X <= 30")    二項的常態近似（有/無連續校正）
  sk.explore()                               互動式分布計算機
  sk.explore(text=True)                      一問一答版（不用互動元件，VS Code 斷網也能用）

【常態的運算與抽樣】
  W = 6 + 2 * X + 3 * Y                      獨立常態的線性組合 → 還是常態；W.explain() 看算式
  X.sample_mean(n)                           樣本平均數 X̄ ~ ND(μ, σ/√n)
  sk.sample_size(sigma=40, margin=6, prob=0.99)          最小樣本數

【兩個隨機變數、貝氏、期望值】
  sk.joint(p, xs=[2, 3], ys=[1, 4, 5])       聯合機率表：邊際、E[XY]、Cov、ρ、是否獨立（conditional='x' 條件機率）
  sk.posterior({0.4: 1/3, 0.6: 2/3}, lambda p: stats.binom.pmf(3, 10, p))   貝氏後驗
  sk.expect(X, lambda x: 2 * x + 20 * (x >= 15))        E[g(X)]（例如含獎金、罰款的期望收益）

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
