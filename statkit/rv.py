"""兩個隨機變數、貝氏後驗、E[g(X)]（講義 04a / 04b、HW07、考古題）。

    sk.joint([[0.4, 0.2, 0.1], [0.05, 0.1, 0.15]], xs=[2, 3], ys=[1, 4, 5])   # Cov、ρ、是否獨立
    sk.posterior({0.4: 1/3, 0.5: 1/3, 0.6: 1/3}, lambda p: stats.binom.pmf(3, 10, p))
    sk.expect(sk.Poisson(12), lambda x: 2 * x + 20 * (x >= 15) - 10 * (x <= 8))

每個函式都會印出課程寫法的程式碼，請貼進答案。
"""
import math

import numpy as np
import pandas as pd

from ._style import fmt
from .dist import _as_dist, _support


def _is_num(v):
    try:
        float(v)
        return not isinstance(v, bool)
    except (TypeError, ValueError):
        return False


def _fmt_list(vs):
    return "[" + ", ".join(fmt(v) if _is_num(v) else repr(v) for v in vs) + "]"


def joint(probs, xs=None, ys=None, conditional=None, digits=4, tol=1e-9):
    """聯合機率表：邊際機率、（數值時）E[X]、E[Y]、E[XY]、Cov、ρ，並逐格判斷是否獨立。

    參數
        probs    : 聯合機率，2 維 list（列 = X 的值、欄 = Y 的值），或 DataFrame（index = X、columns = Y）
        xs, ys   : X、Y 的可能值；也可以是事件名稱（例如 ['Important', 'Unimportant']），這時只算機率不算期望值
        conditional : 'x' → 另外印出 Pr(Y | X = x)；'y' → Pr(X | Y = y)；'both' → 兩個都印
        digits   : 顯示到小數第幾位
    回傳
        dict：table（含邊際的表）、px、py、independent，數值時還有 mean_x、mean_y、exy、cov、var_x、var_y、rho
    例
        sk.joint([[0.4, 0.2, 0.1], [0.05, 0.1, 0.15]], xs=[2, 3], ys=[1, 4, 5])
        sk.joint([[0.459, 0.051], [0.111, 0.379]], xs=['Important', 'Unimportant'],
                 ys=['Switch', "Don't switch"], conditional='x')       # 講義 04a 洗衣店
    """
    if isinstance(probs, pd.DataFrame):
        xs = list(probs.index) if xs is None else list(xs)
        ys = list(probs.columns) if ys is None else list(ys)
        p = probs.to_numpy(float)
    else:
        p = np.asarray(probs, float)
        xs = list(range(p.shape[0])) if xs is None else list(xs)
        ys = list(range(p.shape[1])) if ys is None else list(ys)
    if p.shape != (len(xs), len(ys)):
        raise ValueError(f"機率表是 {p.shape[0]}×{p.shape[1]}，但 xs 有 {len(xs)} 個、ys 有 {len(ys)} 個")
    total = p.sum()
    if abs(total - 1) > 1e-6:
        print(f"⚠ 機率加總是 {total:.6f}，不是 1，請檢查表格")
    px, py = p.sum(axis=1), p.sum(axis=0)

    table = pd.DataFrame(p, index=[str(x) for x in xs], columns=[str(y) for y in ys])
    table["Total"] = px
    table.loc["Total"] = list(py) + [total]
    table.index.name, table.columns.name = "x \\ y", None
    try:
        from IPython.display import display
        display(table.round(digits))
    except ImportError:
        print(table.round(digits))
    show = lambda keys, vals: "、".join(f"{k}: {round(float(v), digits)}" for k, v in zip(keys, vals))
    print(f"邊際機率 Pr(X = x)：{show(xs, px)}")
    print(f"邊際機率 Pr(Y = y)：{show(ys, py)}")

    # 獨立：每一格都要 Pr(x, y) = Pr(x)·Pr(y)
    bad = [(xs[i], ys[j], p[i, j], px[i] * py[j]) for i in range(len(xs)) for j in range(len(ys))
           if abs(p[i, j] - px[i] * py[j]) > tol]
    independent = not bad
    if independent:
        print("獨立：每一格都滿足 Pr(X = x, Y = y) = Pr(X = x) × Pr(Y = y)")
    else:
        x, y, pj, prod = bad[0]
        print(f"不獨立：例如 Pr(X = {x}, Y = {y}) = {fmt(round(pj, 10))} ≠ Pr(X = {x}) × Pr(Y = {y}) = {round(prod, digits)}")
    out = {"table": table, "px": px, "py": py, "independent": independent}

    numeric = all(_is_num(v) for v in xs + ys)
    if numeric:
        xv, yv = np.asarray(xs, float), np.asarray(ys, float)
        mx, my = (xv * px).sum(), (yv * py).sum()
        exy = (np.outer(xv, yv) * p).sum()
        cov = exy - mx * my
        vx, vy = (xv ** 2 * px).sum() - mx ** 2, (yv ** 2 * py).sum() - my ** 2
        rho = cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else float("nan")
        cov_show = 0.0 if abs(cov) < tol else cov
        print(f"E[X] = {mx:.{digits}f}，E[Y] = {my:.{digits}f}，E[XY] = {exy:.{digits}f}")
        print(f"Cov(X, Y) = E[XY] − E[X]E[Y] = {cov_show:.{digits}f}")
        print(f"Var(X) = {vx:.{digits}f}，Var(Y) = {vy:.{digits}f}，ρ = Cov / (σx σy) = {0.0 if abs(cov) < tol else rho:.{digits}f}")
        if abs(cov) < tol and not independent:
            print("→ 不相關（Cov = 0）但不獨立：獨立 ⇒ 不相關，反過來不成立")
        elif abs(cov) < tol:
            print("→ 不相關（Cov = 0）")
        out.update(mean_x=mx, mean_y=my, exy=exy, cov=cov_show, var_x=vx, var_y=vy, rho=rho)
        print("程式碼：")
        print(f"xs = {_fmt_list(xs)}\nys = {_fmt_list(ys)}\n"
              f"p = {[[fmt(v) for v in row] for row in p.tolist()]}".replace("'", "") + "\n"
              "px = [sum(row) for row in p]                                  # Pr(X = x)\n"
              "py = [sum(p[i][j] for i in range(len(xs))) for j in range(len(ys))]   # Pr(Y = y)\n"
              "mu_x = sum(x * q for x, q in zip(xs, px))\n"
              "mu_y = sum(y * q for y, q in zip(ys, py))\n"
              "exy = sum(xs[i] * ys[j] * p[i][j] for i in range(len(xs)) for j in range(len(ys)))\n"
              "cov = exy - mu_x * mu_y\n"
              "var_x = sum(x ** 2 * q for x, q in zip(xs, px)) - mu_x ** 2\n"
              "var_y = sum(y ** 2 * q for y, q in zip(ys, py)) - mu_y ** 2\n"
              "rho = cov / math.sqrt(var_x * var_y)\n"
              "print(round(cov, 4), round(rho, 4))")

    if conditional in ("x", "both"):
        cond = pd.DataFrame(p / px[:, None], index=table.index[:-1], columns=table.columns[:-1])
        print("\n條件機率 Pr(Y = y | X = x) = Pr(x, y) / Pr(x)（每一列加總為 1）：")
        print(cond.round(digits).to_string())
        out["cond_y_given_x"] = cond
    if conditional in ("y", "both"):
        cond = pd.DataFrame(p / py[None, :], index=table.index[:-1], columns=table.columns[:-1])
        print("\n條件機率 Pr(X = x | Y = y) = Pr(x, y) / Pr(y)（每一欄加總為 1）：")
        print(cond.round(digits).to_string())
        out["cond_x_given_y"] = cond
    return out


def posterior(prior, likelihood, digits=4):
    """貝氏定理：由先驗機率與概似算出後驗機率（講義 04a；考古題「參數 p 的後驗分布」）。

    後驗 = 先驗 × 概似 / Σ(先驗 × 概似)

    參數
        prior      : 先驗機率，dict {參數值或事件: 機率}，例如 {0.4: 1/3, 0.5: 1/3, 0.6: 1/3}
        likelihood : 每個參數值下「觀察到這個結果」的機率：同順序的 list，或函式 f(參數值)，
                     例如 lambda p: stats.geom.pmf(2, p)（第 2 次才第一次成功）
        digits     : 顯示到小數第幾位
    回傳
        DataFrame：先驗、概似、先驗×概似、後驗
    例
        sk.posterior({0.4: 1/3, 0.5: 1/3, 0.6: 1/3}, lambda p: stats.binom.pmf(3, 10, p))
    """
    keys = list(prior.keys())
    pri = np.array([float(prior[k]) for k in keys])
    if callable(likelihood):
        lik = np.array([float(likelihood(k)) for k in keys])
    else:
        lik = np.asarray(likelihood, float)
    joint_ = pri * lik
    total = joint_.sum()
    post = joint_ / total
    df = pd.DataFrame({"先驗": pri, "概似": lik, "先驗×概似": joint_, "後驗": post},
                      index=pd.Index([str(k) for k in keys], name="參數 / 事件")).round(digits)
    print(f"觀察到這個結果的總機率（全機率）= Σ 先驗×概似 = {total:.{digits}f}")
    for k, v in zip(keys, post):
        print(f"後驗 Pr({k} | 結果) = {v:.{digits}f}")
    print("程式碼：")
    print(f"params = {_fmt_list(keys)}\n"
          f"prior = {_fmt_list([round(v, 10) for v in pri])}\n"
          "likelihood = [...]   # 每個參數下觀察到這個結果的機率，例如 [stats.binom.pmf(3, 10, p) for p in params]\n"
          "total = sum(a * b for a, b in zip(prior, likelihood))\n"
          "posterior = [a * b / total for a, b in zip(prior, likelihood)]\n"
          "print([round(v, 4) for v in posterior])")
    return df


def expect(d, g, name="g(X)", digits=4):
    """E[g(X)]：例如含獎金、罰款的期望收益（講義 04b；考古題）。

    參數
        d        : 分布，例如 sk.Poisson(12)、sk.Discrete([...], [...])、sk.Normal(80, 10)
        g        : 函式，例如 lambda x: 2 * x + 20 * (x >= 15) - 10 * (x <= 8)
        name     : 顯示用的名稱
        digits   : 顯示到小數第幾位
    回傳
        E[g(X)]（float）
    例
        sk.expect(sk.Poisson(12), lambda x: 2 * x + 20 * (x >= 15) - 10 * (x <= 8))
    """
    d = _as_dist(d)
    if d.discrete:
        lo, hi = _support(d, 0, 1 - 1e-12)
        xs = np.arange(math.floor(lo), math.ceil(hi) + 1)
        value = float(sum(float(g(x)) * float(d.frozen.pmf(x)) for x in xs))
        print(f"{d.label}：E[{name}] = Σ {name}·Pr(X = x)（x = {int(xs[0])}…{int(xs[-1])}，之後的機率可以忽略）= {value:.{digits}f}")
        print("程式碼：")
        print(f"def g(x):\n    return ...   # 例如 2 * x + 20 * (x >= 15) - 10 * (x <= 8)\n"
              f"print(round(sum(g(x) * {d.code('pmf', 'k', 'x')} for x in range({int(xs[0])}, {int(xs[-1]) + 1})), 4))")
        print("（也可以拆開：例如 2·E[X] + 20·Pr(X ≥ 15) − 10·Pr(X ≤ 8)）")
    else:
        value = float(d.frozen.expect(g))
        print(f"{d.label}：E[{name}] = ∫ {name} f(x) dx = {value:.{digits}f}")
        print(f"程式碼：print(round(stats.{d.name}.expect(g, {d.kw}), 4))")
    return value
