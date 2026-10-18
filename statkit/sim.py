"""模擬（講義 06a 抽樣平均數、06b 蒙地卡羅）。"""
import math

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from ._style import ACCENT, EDGE, FACE, new_ax
from .dist import _as_dist


def sample_means(d, n, reps=1000, seed=None, bins=30, ax=None):
    """抽樣平均數的分布（中央極限定理）：從分布 d 抽 reps 組大小為 n 的樣本，
    比較樣本平均數的平均與變異數跟理論值 μ、σ²/n。

    參數
        d        : 分布，例如 sk.Binom(10, 0.4)、sk.Normal(80, 10)，或 scipy 的 stats.norm(80, 10)
        n        : 每組樣本的大小
        reps     : 重複抽幾組
        seed     : 亂數種子（給了結果就固定，方便重現）
        bins     : 直方圖組數
        ax       : 畫在哪個子圖（例如 plt.subplots 的 axes[0]）；不給就開一張新圖
    回傳
        所有樣本平均數（numpy array）
    例
        sk.sample_means(sk.Normal(80, 4), n=9, reps=500, seed=1)
    """
    d = _as_dist(d)
    rng = np.random.default_rng(seed)
    means = d.frozen.rvs(size=(reps, n), random_state=rng).mean(axis=1)
    mu, var = float(d.frozen.mean()), float(d.frozen.var())
    print(f"{d.label}，樣本大小 n = {n}，重複 {reps} 次")
    print(f"樣本平均數的平均數 = {means.mean():.4f}　（理論 μ = {mu:.4f}）")
    print(f"樣本平均數的變異數 = {means.var():.4f}　（理論 σ²/n = {var / n:.4f}）")

    ax = new_ax(ax, figsize=(8, 5))
    counts, edges, _ = ax.hist(means, bins=bins, color=FACE, edgecolor=EDGE)
    grid = np.linspace(edges[0], edges[-1], 300)
    pdf = stats.norm.pdf(grid, mu, math.sqrt(var / n))
    ax.plot(grid, pdf * reps * np.diff(edges).mean(), color=ACCENT, lw=2, label="ND(μ, σ/√n)")
    ax.set_xlabel("Sample means")
    ax.set_ylabel("Frequency")
    ax.set_title(f"{reps} size-{n} sample means from {d.label}")
    ax.legend()
    return means


def estimate_pi(points=1000, seed=None, plot=True):
    """蒙地卡羅估 π（講義 06b）：在 [0, 2]×[0, 2] 撒點，落在圓內的比例 × 4 ≈ π。

    參數
        points   : 撒幾個點，越多越準
        seed     : 亂數種子
        plot     : True 畫出點的分布
    回傳
        π 的估計值
    例
        sk.estimate_pi(2000, seed=115)
    """
    rng = np.random.default_rng(seed)
    x, y = rng.uniform(0, 2, points), rng.uniform(0, 2, points)
    inside = (x - 1) ** 2 + (y - 1) ** 2 <= 1
    est = 4 * inside.mean()
    print(f"{points} 個點，圓內 {inside.sum()} 個，π ≈ {est:.4f}")
    if plot:
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.add_patch(plt.Circle((1, 1), 1, color="blue", fill=False, linewidth=2))
        ax.add_patch(plt.Polygon([[0, 0], [2, 0], [2, 2], [0, 2]], closed=True, fill=False,
                                 edgecolor="red", linewidth=2))
        ax.scatter(x[inside], y[inside], marker=".", color="tab:blue")
        ax.scatter(x[~inside], y[~inside], marker=".", color="tab:gray")
        ax.set_xlim(-0.5, 2.5)
        ax.set_ylim(-0.5, 2.5)
        ax.set_aspect("equal", "box")
        ax.grid(True)
        plt.show()
    return est


def monty_hall(trials=10000, seed=None):
    """三門問題（講義 06b）：比較「不換」與「換門」的勝率（理論值 1/3 與 2/3）。

    參數
        trials   : 模擬次數
        seed     : 亂數種子
    回傳
        dict：stick（不換的勝率）、switch（換門的勝率）
    例
        sk.monty_hall(10000, seed=115)
    """
    rng = np.random.default_rng(seed)
    car = rng.integers(1, 4, trials)
    choice = rng.integers(1, 4, trials)
    stick = (car == choice).mean()
    switch = 1 - stick          # 主持人開空門後換門，只要一開始沒選中就會贏
    print(f"{trials} 次實驗：不換的勝率 = {stick:.4f}，換門的勝率 = {switch:.4f}")
    return {"stick": stick, "switch": switch}
