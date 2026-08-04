#!/usr/bin/env python3
"""
「今も正体が分かっていない 地球の音 3選」用の科学ビジュアル素材レンダラ。

AI画像生成を使わず、実際の信号処理でスペクトログラム・波形・スペクトルを描く。
この動画は「音」がテーマなので、本物の信号から描いたほうが説得力が出る。

出力：1080x1920 PNG（9:16）
共通処理：中央のテロップ帯を暗く落とす／ビネット／フィルムグレイン／文字は一切入れない

  python3 render_assets.py
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1920
DPI = 100
RNG = np.random.default_rng(7)

# テロップが乗る帯（画面の縦 52%〜72%）。ここは必ず暗く落として可読性を確保する
TELOP_TOP, TELOP_BOTTOM = 0.52, 0.72


def new_fig():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor("#000000")
    return fig


def finish(fig, name, grain=0.030, vignette=0.55, telop_dim=0.55):
    """グレイン・ビネット・テロップ帯の減光をかけて保存する。"""
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=DPI, facecolor="#000000", bbox_inches=None, pad_inches=0)
    plt.close(fig)

    img = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    h, w, _ = img.shape

    # ビネット
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h / 2, w / 2
    r = np.sqrt(((yy - cy) / cy) ** 2 + ((xx - cx) / cx) ** 2)
    img *= (1.0 - vignette * np.clip(r - 0.45, 0, None) ** 1.6)[..., None]

    # テロップ帯の減光（上下は滑らかにフェード）
    band = np.zeros(h, dtype=np.float32)
    t0, t1 = int(h * TELOP_TOP), int(h * TELOP_BOTTOM)
    feather = int(h * 0.05)
    band[t0:t1] = 1.0
    for i in range(feather):
        f = i / feather
        if t0 - feather + i >= 0:
            band[t0 - feather + i] = f
        if t1 + i < h:
            band[t1 + i] = 1.0 - f
    img *= (1.0 - telop_dim * band)[:, None, None]

    # フィルムグレイン
    img += RNG.normal(0.0, grain, img.shape).astype(np.float32)

    img = np.clip(img, 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)
    print(f"  {name}")


def starfield(ax, n=420, seed=3):
    rng = np.random.default_rng(seed)
    ax.scatter(rng.uniform(0, 1, n), rng.uniform(0, 1, n),
               s=rng.exponential(1.6, n) * 2.2,
               c="#cfe6ff", alpha=0.55, linewidths=0, marker=".")


# ─────────────────────────────────────────────────────────────
# A02 / カット2 — オシロスコープ。走査の途中で止まった奇妙な波形
# ─────────────────────────────────────────────────────────────
def a02_oscilloscope():
    fig = new_fig()
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#01120a")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # 蛍光管のグリッド
    for gx in np.linspace(0.08, 0.92, 11):
        ax.axvline(gx, color="#1f7a4d", lw=0.8, alpha=0.20)
    for gy in np.linspace(0.20, 0.80, 9):
        ax.axhline(gy, color="#1f7a4d", lw=0.8, alpha=0.20)

    t = np.linspace(0, 1, 3000)
    # 途中で性質が変わる波形。走査が途切れて右側は無信号
    cut = 0.62
    sig = (np.sin(2 * np.pi * 4.5 * t) * 0.13 * (1 + 0.5 * np.sin(2 * np.pi * 1.3 * t))
           + np.sin(2 * np.pi * 23 * t) * 0.055 * np.exp(-((t - 0.34) ** 2) / 0.010)
           + np.sin(2 * np.pi * 41 * t) * 0.030 * np.exp(-((t - 0.52) ** 2) / 0.006)
           + RNG.normal(0, 0.010, t.size))
    sig[t > cut] = np.nan
    y = 0.50 + sig

    for lw, alpha in ((9, 0.06), (5, 0.12), (2.6, 0.35), (1.2, 1.0)):
        ax.plot(t, y, color="#4dffa0", lw=lw, alpha=alpha, solid_capstyle="round")

    # 走査線の先端
    ax.scatter([cut], [0.50 + sig[np.searchsorted(t, cut) - 1]],
               s=180, c="#d9ffe9", alpha=0.9, zorder=5)
    finish(fig, "A02_cut02_オシロスコープ.png", telop_dim=0.45)


# ─────────────────────────────────────────────────────────────
# A06 / カット6・7 — アップスウィープのスペクトログラム
#   周波数が上昇するチャープ列を実際に合成して STFT にかける
# ─────────────────────────────────────────────────────────────
def a06_upsweep_spectrogram():
    fs = 1000.0
    dur = 20.0
    t = np.arange(0, dur, 1 / fs)
    x = RNG.normal(0, 0.030, t.size)

    # 3.4秒ごとに、20Hz→95Hz へ上昇する狭帯域チャープを置く
    period, sweep_len = 4.6, 2.9
    f0, f1 = 20.0, 95.0
    for start in np.arange(1.0, dur - sweep_len, period):
        m = (t >= start) & (t < start + sweep_len)
        tt = t[m] - start
        k = (f1 - f0) / sweep_len
        phase = 2 * np.pi * (f0 * tt + 0.5 * k * tt ** 2)
        env = np.sin(np.pi * tt / sweep_len) ** 2
        x[m] += 1.0 * env * np.sin(phase)

    fig = new_fig()
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#000000")
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list(
        "sonar", ["#000000", "#02160c", "#0b6b3a", "#3fd07a", "#c8f06a", "#ffd98a"])
    ax.specgram(x, NFFT=1024, Fs=fs, noverlap=960, cmap=cmap,
                vmin=-42, vmax=14)
    ax.set_ylim(0, 140)
    ax.axis("off")
    finish(fig, "A06_cut06-07_アップスウィープ_スペクトログラム.png",
           telop_dim=0.62, vignette=0.65)


# ─────────────────────────────────────────────────────────────
# A08 / カット9・14・43 — 宇宙から見た暗い地球と、光る点
#   3変種：点1つ(明) / 点1つ(減衰) / 点3つ
# ─────────────────────────────────────────────────────────────
def a08_globe(points, name, glow=1.0):
    fig = new_fig()
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#000000")
    # y軸を H/W まで伸ばして 1単位=1単位 の正方座標にする（円が真円になる）
    ASPECT = H / W
    ax.set_xlim(0, 1); ax.set_ylim(0, ASPECT); ax.axis("off")
    rng = np.random.default_rng(3)
    ax.scatter(rng.uniform(0, 1, 420), rng.uniform(0, ASPECT, 420),
               s=rng.exponential(1.6, 420) * 2.2,
               c="#cfe6ff", alpha=0.55, linewidths=0, marker=".")

    cx, cy, R = 0.5, 0.52, 0.40   # 下寄せ。中央のテロップ帯は空ける

    # 球体（内側から外へ、暗い青のグラデーション）
    for i in range(260):
        f = i / 260
        rad = R * (1 - f)
        shade = 0.045 + 0.150 * (1 - f) ** 2
        tint = (shade * 0.35, shade * 0.72, shade * 1.0)
        ax.add_patch(plt.Circle((cx, cy), rad, transform=ax.transData,
                                color=tint, lw=0, zorder=2))
        del rad, tint

    # 大気のリムライト
    for i in range(70):
        f = i / 70
        ax.add_patch(plt.Circle((cx, cy), R * (1 + 0.075 * f),
                                fill=False, lw=2.2,
                                color=(0.25, 0.62, 0.95),
                                alpha=0.085 * (1 - f) ** 1.4, zorder=3))

    # 経緯線をごく薄く
    for k in range(-3, 4):
        yy = cy + k * R / 4.2
        half = np.sqrt(max(R ** 2 - (yy - cy) ** 2, 0))
        ax.plot([cx - half, cx + half], [yy, yy], color="#3f7fb5",
                lw=0.8, alpha=0.16, zorder=4)

    # 光る点
    for (px, py, strength) in points:
        for i in range(46):
            f = i / 46
            ax.add_patch(plt.Circle((px, py), 0.006 + 0.085 * f,
                                    color="#ff2a2a",
                                    alpha=0.16 * (1 - f) ** 2 * strength * glow,
                                    lw=0, zorder=6))
        ax.scatter([px], [py], s=52 * strength, c="#ffd9d9",
                   alpha=min(1.0, strength), zorder=7, linewidths=0)

    finish(fig, name, telop_dim=0.30, vignette=0.35)


# ─────────────────────────────────────────────────────────────
# A10 / カット12 — 季節変動。春と秋に二つのピーク
# ─────────────────────────────────────────────────────────────
def a10_seasonal():
    fig = new_fig()
    ax = fig.add_axes([0.10, 0.10, 0.80, 0.32])   # 下寄せ。上と中央は空ける
    fig.patch.set_facecolor("#000000")
    ax.set_facecolor("#000000")

    m = np.linspace(0, 12, 900)
    y = (1.00 * np.exp(-((m - 3.6) ** 2) / 1.1)
         + 0.88 * np.exp(-((m - 9.4) ** 2) / 1.3)
         + 0.18 + 0.035 * np.sin(m * 7))
    y += RNG.normal(0, 0.012, m.size)

    for lw, alpha in ((10, 0.05), (5, 0.11), (2.4, 0.32), (1.3, 1.0)):
        ax.plot(m, y, color="#38d6ff", lw=lw, alpha=alpha)
    ax.fill_between(m, y, 0, color="#38d6ff", alpha=0.07)

    for peak in (3.6, 9.4):
        ax.axvline(peak, color="#ff2a2a", lw=1.1, alpha=0.55, ls=(0, (5, 4)))

    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(0, 12); ax.set_ylim(0, 1.35)
    ax.grid(True, color="#17384d", lw=0.7, alpha=0.35)
    finish(fig, "A10_cut12_季節変動グラフ.png", telop_dim=0.30)


# ─────────────────────────────────────────────────────────────
# A17 / カット20 — ハム。ほぼ平坦な低周波がゆっくり震える
# ─────────────────────────────────────────────────────────────
def a17_hum():
    fig = new_fig()
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#000000")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    t = np.linspace(0, 1, 4000)
    y = (0.26 + 0.055 * np.sin(2 * np.pi * 3 * t)
         + 0.018 * np.sin(2 * np.pi * 11 * t)
         + 0.006 * np.sin(2 * np.pi * 29 * t))
    for lw, alpha, col in ((26, 0.07, "#ff5a00"), (14, 0.14, "#ff7a1a"),
                           (6, 0.28, "#ff9a3a"), (2.6, 0.55, "#ffc078"),
                           (1.4, 1.0, "#fff0dd")):
        ax.plot(t, y, color=col, lw=lw, alpha=alpha)
    finish(fig, "A17_cut20_低周波ハム波形.png", telop_dim=0.30, vignette=0.7)


# ─────────────────────────────────────────────────────────────
# A26 / カット32 — 52ヘルツ。孤立した一本のピーク
#   変種b：10〜39Hz（シロナガス）の帯を薄く添えた比較版（カット34-35用）
# ─────────────────────────────────────────────────────────────
def a26_peak(with_blue_band, name):
    fig = new_fig()
    ax = fig.add_axes([0.08, 0.08, 0.84, 0.36])
    ax.set_facecolor("#000000")

    f = np.linspace(0, 100, 2400)
    spec = 0.02 + RNG.normal(0, 0.006, f.size)
    spec = np.abs(spec)

    if with_blue_band:
        for c, a in ((14, 0.28), (19, 0.34), (26, 0.30), (33, 0.22), (38, 0.16)):
            spec += a * np.exp(-((f - c) ** 2) / 1.6)

    spec += 1.0 * np.exp(-((f - 52) ** 2) / 0.30)

    if with_blue_band:
        band = (f >= 10) & (f <= 39)
        ax.fill_between(f[band], spec[band], 0, color="#2f9bd6", alpha=0.22)
        ax.plot(f, np.where((f >= 10) & (f <= 39), spec, np.nan),
                color="#7fd4ff", lw=1.2, alpha=0.75)

    peak = (f > 48) & (f < 56)
    for lw, alpha in ((14, 0.06), (7, 0.13), (3.0, 0.35), (1.5, 1.0)):
        ax.plot(f[peak], spec[peak], color="#ff2a2a", lw=lw, alpha=alpha)
    ax.plot(f, spec, color="#8899aa", lw=0.8, alpha=0.30, zorder=0)

    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(0, 100); ax.set_ylim(0, 1.25)
    finish(fig, name, telop_dim=0.28, vignette=0.6)


# ─────────────────────────────────────────────────────────────
# A30 / カット38 — 海図。一本だけ不規則な赤い経路
# ─────────────────────────────────────────────────────────────
def a30_chart():
    fig = new_fig()
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#040a12")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    for gx in np.linspace(0.05, 0.95, 13):
        ax.axvline(gx, color="#1b4666", lw=0.7, alpha=0.30)
    for gy in np.linspace(0.05, 0.95, 22):
        ax.axhline(gy, color="#1b4666", lw=0.7, alpha=0.30)

    # 他の種の回遊経路（灰色・規則的）
    for seed in range(5):
        rng = np.random.default_rng(40 + seed)
        px = np.linspace(0.12, 0.88, 9)
        py = 0.20 + 0.13 * seed / 5 + rng.normal(0, 0.012, 9)
        ax.plot(px, py, color="#7e93a6", lw=1.4, alpha=0.30)

    # 52ヘルツ個体の経路（赤・不規則）
    rng = np.random.default_rng(11)
    qx = np.linspace(0.10, 0.90, 16)
    qy = 0.26 + 0.16 * np.sin(np.linspace(0, 5.2, 16)) + rng.normal(0, 0.045, 16)
    for lw, alpha in ((11, 0.05), (6, 0.10), (2.6, 0.35), (1.5, 1.0)):
        ax.plot(qx, qy, color="#ff2a2a", lw=lw, alpha=alpha)
    ax.scatter(qx, qy, s=18, c="#ffd0d0", alpha=0.85, zorder=5, linewidths=0)
    finish(fig, "A30_cut38_回遊経路の海図.png", telop_dim=0.42)


# ─────────────────────────────────────────────────────────────
# A32 / カット41 — 三つの波形が重なる
# ─────────────────────────────────────────────────────────────
def a32_three_waves():
    fig = new_fig()
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#000000")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    t = np.linspace(0, 1, 4000)
    specs = [
        (0.30, "#38d6ff", 0.045, 11, 0.9),    # アップスウィープ
        (0.26, "#ff7a1a", 0.012, 5, 0.8),     # ハム
        (0.22, "#ff2a2a", 0.030, 26, 1.0),    # 52ヘルツ
    ]
    for base, col, amp, freq, a in specs:
        y = base + amp * np.sin(2 * np.pi * freq * t) * np.exp(-((t - 0.5) ** 2) / 0.35)
        for lw, al in ((12, 0.04), (6, 0.09), (2.4, 0.22), (1.2, 0.85)):
            ax.plot(t, y, color=col, lw=lw, alpha=al * a)
    finish(fig, "A32_cut41_三つの波形.png", telop_dim=0.30, vignette=0.7)


if __name__ == "__main__":
    print("レンダリング開始 →", OUT)
    a02_oscilloscope()
    a06_upsweep_spectrogram()
    a08_globe([(0.40, 0.44, 1.0)], "A08a_cut09_地球と光る一点.png")
    a08_globe([(0.40, 0.44, 1.0)], "A08b_cut14_地球と減衰する点.png", glow=0.30)
    a08_globe([(0.40, 0.44, 0.85), (0.62, 0.60, 0.85), (0.33, 0.68, 0.85)],
              "A08c_cut43_地球と三つの点.png")
    a10_seasonal()
    a17_hum()
    a26_peak(False, "A26a_cut32_52ヘルツの孤立ピーク.png")
    a26_peak(True, "A26b_cut34-35_52ヘルツとシロナガスの帯.png")
    a30_chart()
    a32_three_waves()
    print("完了")
