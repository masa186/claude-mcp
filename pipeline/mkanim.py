"""黒板用のアニメーションを、フレーム連番で書き出す。

矢印を1本置くだけでは「下に矢印がある」としか伝わらない。
空気の粒が実際に翼に当たって、軌道を変えて下へ抜けていくところを見せる。

つくるもの:
  clips/wingrace/  学校の説明の反証。上下の空気が同時に出発して、同時に着かない
  clips/airflow/   空気が翼に沿って下へ曲がって出ていく
  clips/airlift/   同じ流れ＋「下へ押す／上へ押し返される」の対

素人っぽく見える原因を3つ潰してある:
  1. PIL の線にはアンチエイリアスが無い → 2倍で描いて縮小する
  2. 粒が等速で等間隔 → 翼の上では実際に加速させ、尾の長さで速さを見せる
  3. 図に文字が無く、何を見ればいいか分からない → 図の中に注記を焼き込む
"""
import os, math
from PIL import Image, ImageDraw
from style import font, GOTHIC

W, H = 900, 640
SS = 2                      # 描画時の拡大率（縮小してアンチエイリアスにする）
N = 72                      # フレーム数（30fpsで2.4秒＝ショット1つぶん）

CHALK = (242, 237, 224)
DIM   = (188, 200, 190)
HEAT  = (224, 92, 66)
GOLD  = (231, 178, 62)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clips')

# ---------------------------------------------------------------- 翼の形
LE, TE = 150, 700           # 前縁・後縁のx
CY     = 330                # 前縁の高さ
AOA    = 0.085              # 迎え角（後縁が下がる）


def tilt(x):
    return (x - LE) * AOA


def upper(x):
    t = min(1.0, max(0.0, (x - LE) / (TE - LE)))
    return CY + tilt(x) - 5 - 58 * math.sin(math.pi * t ** 0.60)


def lower(x):
    t = min(1.0, max(0.0, (x - LE) / (TE - LE)))
    return CY + tilt(x) + 5 + 13 * math.sin(math.pi * t ** 0.95)


def wing_poly():
    pts = [(x, upper(x)) for x in range(LE, TE + 1, 6)]
    pts += [(x, lower(x)) for x in range(TE, LE - 1, -6)]
    return pts


# ---------------------------------------------------------------- 流線
DECAY = 175.0               # 翼から離れるほど影響が薄れる距離
WAKE  = 0.52                # 後流が下へ曲がる傾き


def stream_y(y0, x):
    """上流での高さ y0 の流線が、位置 x で通る高さ。"""
    up = y0 < CY
    surf = upper(x) if up else lower(x)
    dist = abs(y0 - CY)
    k = math.exp(-dist / DECAY)
    if x < LE:
        # 前縁の手前で少し持ち上がる（上昇流）
        d = max(0.0, 1.0 - (LE - x) / 210.0)
        return y0 - 26 * k * d * d
    if x <= TE:
        base = (upper(LE) if up else lower(LE))
        # 前縁の持ち上がりをここで滑らかに戻す。段差があると尾が折れて見える
        t = (x - LE) / (TE - LE)
        return y0 + (surf - base) * k - 26 * k * (1 - t) ** 2
    base = (upper(LE) if up else lower(LE))
    y = y0 + ((upper(TE) if up else lower(TE)) - base) * k
    return y + (x - TE) * WAKE * k


def speed(y0, x):
    """翼の上は速く、下は少し遅い。ここを一定にすると流れに見えない。"""
    if not (LE <= x <= TE):
        return 1.0
    t = (x - LE) / (TE - LE)
    b = math.sin(math.pi * t) ** 0.8
    k = math.exp(-abs(y0 - CY) / DECAY)
    return 1.0 + (0.85 if y0 < CY else -0.30) * b * k


X0, X1 = -110, W + 110
_tables = {}


def table(y0):
    """速さを積分して、進み具合 s(0〜1) から x を引ける表を作る。"""
    if y0 not in _tables:
        n = 900
        xs = [X0 + (X1 - X0) * i / n for i in range(n + 1)]
        acc, cum = 0.0, [0.0]
        for a, b in zip(xs, xs[1:]):
            acc += (b - a) / speed(y0, (a + b) / 2)
            cum.append(acc)
        _tables[y0] = (xs, [c / acc for c in cum])
    return _tables[y0]


def at(y0, s):
    """s = 0→1 で上流から下流まで。戻り値は (x, y)。"""
    s = s % 1.0
    xs, cum = table(y0)
    lo, hi = 0, len(cum) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if cum[mid] <= s: lo = mid
        else: hi = mid
    span = cum[hi] - cum[lo] or 1e-9
    x = xs[lo] + (xs[hi] - xs[lo]) * (s - cum[lo]) / span
    return x, stream_y(y0, x)


# ---------------------------------------------------------------- 描画の小道具

def line(d, pts, color, width, alpha=255):
    d.line([(x * SS, y * SS) for x, y in pts],
           fill=tuple(color) + (alpha,), width=int(width * SS), joint='curve')


def dot(d, x, y, r, color, alpha=255):
    d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS],
              fill=tuple(color) + (alpha,))


def dashed(d, x1, y1, x2, y2, color, width=3, dash=14, alpha=190):
    L = math.hypot(x2 - x1, y2 - y1)
    n = max(1, int(L / dash))
    for i in range(0, n, 2):
        a, b = i / n, min(1.0, (i + 1) / n)
        line(d, [(x1 + (x2-x1)*a, y1 + (y2-y1)*a),
                 (x1 + (x2-x1)*b, y1 + (y2-y1)*b)], color, width, alpha)


def arrow(d, x1, y1, x2, y2, color, width=11, head=34, alpha=255):
    a = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - head * math.cos(a), y2 - head * math.sin(a)
    line(d, [(x1, y1), (bx, by)], color, width, alpha)
    n = a + math.pi / 2
    d.polygon([(x2 * SS, y2 * SS),
               ((bx + head*.52*math.cos(n)) * SS, (by + head*.52*math.sin(n)) * SS),
               ((bx - head*.52*math.cos(n)) * SS, (by - head*.52*math.sin(n)) * SS)],
              fill=tuple(color) + (alpha,))


def label(d, x, y, text, size=36, color=CHALK, alpha=255, anchor='mm', face=None):
    """図の中の注釈。フチを付けて、線や流れの上に来ても読めるようにする。

    スマホの実寸で読めないと指摘された。黒板の緑にグレーだと、
    背景と明度が近すぎて溶ける。色を白か黄に上げ、さらにフチで浮かせる。
    """
    d.text((x * SS, y * SS), text, font=font(size * SS, face or GOTHIC),
           fill=tuple(color) + (alpha,), anchor=anchor,
           stroke_width=max(2, int(size * SS * 0.055)),
           stroke_fill=(18, 34, 28, min(alpha, 210)))


def fade(p, a=0.12, b=0.88):
    """出入りをなめらかにする。0→1→0。"""
    if p < a:  return max(0.0, p / a)
    if p > b:  return max(0.0, (1 - p) / (1 - b))
    return 1.0


# ---------------------------------------------------------------- 粒の流れ

ROWS_UP = (185, 225, 262, 296)
ROWS_DN = (424, 468, 512)
PER_ROW = 5
TRAIL   = 0.075             # 尾の長さ（sの単位）。短いと点線、長いと流線に見える
SEG     = 14                # 尾を何本に分けて描くか（多いほど曲線がなめらか）


def draw_flow(d, p, alpha=255):
    for k, y0 in enumerate(ROWS_UP + ROWS_DN):
        for j in range(PER_ROW):
            s = (p + j / PER_ROW + k * 0.041) % 1.0
            # 尾が s<0 に回り込むと、画面の反対側まで一直線が走ってしまう
            pts = [at(y0, s - TRAIL * i / SEG)
                   for i in range(SEG + 1) if s - TRAIL * i / SEG >= 0]
            if len(pts) < 2:
                continue
            x, y = pts[0]
            if x < X0 + 20 or x > X1 - 20:
                continue
            # 尾の長さ＝その場の速さ。速いところほど長く伸びて見える
            fast = min(1.0, math.hypot(pts[0][0]-pts[2][0], pts[0][1]-pts[2][1]) / 11.0)
            wdt = 6 + 5 * fast
            for i in range(len(pts) - 1):
                a = int(alpha * (0.10 + 0.90 * (1 - i / SEG) ** 1.5) * (0.45 + 0.55 * fast))
                line(d, [pts[i], pts[i+1]], CHALK, wdt * (1 - 0.72 * i / SEG), a)
            dot(d, x, y, wdt * 0.52, CHALK, alpha)


def draw_wing(d, alpha=255):
    d.polygon([(x * SS, y * SS) for x, y in wing_poly()], fill=CHALK + (alpha,))
    line(d, [(TE, (upper(TE)+lower(TE))/2), (TE + 96, (upper(TE)+lower(TE))/2 + 42)],
         CHALK, 13, alpha)


# ---------------------------------------------------------------- 各アニメ

def f_airflow(i, lift=False):
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N

    # 曲がっていないときの高さ。これが無いと「曲がった」が目で確認できない
    ry = ROWS_UP[-1]
    dashed(d, TE - 40, ry, W - 55, ry, DIM, 3, 15, 120)

    draw_flow(d, p)
    draw_wing(d)

    # 図の中の文字は最小限にする。黒板の文字と同じことを言うと二重になり、
    # 位置もぶつかる。ここは「どれだけ曲がったか」を測って見せるだけ。
    # 濃さは時間で変えない。ショットが連番より長いと2周目に入って、
    # フェードインを入れていると継ぎ目でパッと消えるため。
    label(d, 62, 140, '空気', 60, CHALK, 255, anchor='lm')
    arrow(d, 806, ry + 8, 806, stream_y(ry, 806) - 8, GOLD, 9, 28)
    arrow(d, 590, 486, 750, 546, GOLD, 13, 38)

    if lift:
        # 「下へ押した分だけ上へ押し返される」の対を、同じ画面に出す。
        # 脈は1周でちょうど1往復させる（継ぎ目が出ない）
        k = 0.5 - 0.5 * math.cos(2 * math.pi * p)
        y0 = upper(430) - 10
        arrow(d, 430, y0, 430, y0 - 148 - int(28 * k), HEAT, 24, 56)
    return im.resize((W, H), Image.LANCZOS)


def f_wingrace(i):
    """学校の説明の反証。

    前の版は流線・注記を全部載せていたので、この図を読むこと自体が
    新しい勉強になっていた。見るべきものを2つの点だけに絞る。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N

    draw_wing(d)
    dashed(d, LE, 150, LE, 560, DIM, 4, 18, 150)
    dashed(d, TE, 150, TE, 560, DIM, 4, 18, 150)
    label(d, LE + 40, 120, '同時に出発', 62, CHALK, 255)
    label(d, TE - 26, 120, 'ゴール', 62, CHALK, 255)

    def s_of(y0, frac):
        xs, cum = table(y0)
        def c_at(xt):
            for a, b, ca, cb in zip(xs, xs[1:], cum, cum[1:]):
                if a <= xt <= b:
                    return ca + (cb - ca) * (xt - a) / (b - a)
            return cum[-1]
        c0, c1 = c_at(LE), c_at(TE)
        return c0 + (c1 - c0) * frac

    run = min(1.0, p / 0.70)
    ux, uy = at(258, s_of(258, run))
    dx_, dy_ = at(432, s_of(432, run * 0.66))
    dot(d, ux, uy, 21, HEAT)
    dot(d, dx_, dy_, 21, GOLD)

    if run >= 1.0:
        a = int(255 * min(1.0, (p - 0.70) / 0.10))
        # 大きな×。ここが結論なので、細かい注記より記号を大きく出す
        # 言葉は黒板の行が持つ。図は記号だけにして、同じことを二度言わない
        cx, cy, r = 470, 566, 52
        line(d, [(cx - r, cy - r), (cx + r, cy + r)], HEAT, 18, a)
        line(d, [(cx + r, cy - r), (cx - r, cy + r)], HEAT, 18, a)
    return im.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- 手と翼を並べる

def f_same(i):
    """手と翼を1枚に並べて、同じことが起きているのを見せる。

    「あれと同じ」は言葉で言っても伝わらない。並べて、同じ向きに空気が抜けて
    同じ向きに力が出るところを同時に見せると、比べるまでもなく分かる。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N
    e = 1 - (1 - min(1.0, i / (N * 0.35))) ** 3

    def body(cy, kind):
        if kind == 'hand':
            ang = math.radians(-18)
            hx, hy = 560, cy
            px = hx - 150 * math.cos(ang)
            py = hy - 150 * math.sin(ang)
            capsule(d, 700, cy + 16, hx, hy, 40, CHALK)
            capsule(d, hx + 10, hy + 2, px, py, 34, CHALK)
            return px, hx
        pts = [(x, upper(x)) for x in range(LE, TE + 1, 8)]
        pts += [(x, lower(x)) for x in range(TE, LE - 1, -8)]
        k = 0.62
        poly = [(300 + (x - LE) * k, cy + (y - CY) * k) for x, y in pts]
        d.polygon([(x * SS, y * SS) for x, y in poly], fill=CHALK + (255,))
        return 300, 300 + (TE - LE) * k

    def half(cy, kind):
        nose = 410 if kind == 'hand' else 300
        # 空気を先に描いて、そのあと本体を上に重ねる。順番を逆にすると
        # 線が手や翼を突き抜けて見える
        for r, dy0 in enumerate((-76, -44, -14, 18, 48)):
            for j in range(3):
                s0 = (p * 1.15 + j / 3 + r * 0.07) % 1.0
                x = -120 + s0 * (W + 240)
                y0 = cy + dy0
                k = math.exp(-abs(dy0) / 90.0)
                def yy(xq):
                    if xq < nose:
                        return y0
                    return y0 + (xq - nose) * 0.55 * k * e
                pts = [(x - 24 * m, yy(x - 24 * m)) for m in range(6)]
                if pts[0][0] < -70 or pts[0][0] > W + 70:
                    continue
                for m in range(5):
                    line(d, [pts[m], pts[m+1]], CHALK, 8.5 - m * 1.0,
                         int(235 * (1 - m / 5) ** 1.2))
                dot(d, pts[0][0], pts[0][1], 4.6, CHALK, 240)

        n2, tail_x = body(cy, kind)
        arrow(d, (n2 + tail_x) / 2, cy - 46, (n2 + tail_x) / 2, cy - 132,
              HEAT, 17, 42, int(255 * e))

    label(d, 62, 66, '手', 78, GOLD, 255, anchor='lm')
    label(d, 62, 368, '翼', 78, GOLD, 255, anchor='lm')
    half(190, 'hand')
    dashed(d, 60, 320, 840, 320, DIM, 3, 20, 90)
    half(492, 'wing')
    return im.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- 背面飛行

def f_invert(i):
    """逆さまでも飛ぶ、を見せる図。

    「翼の形（上が長い）から浮く」が本当なら、ひっくり返した瞬間に
    落ちなければならない。実際は落ちない。ここが学校の説明への一番強い反証で、
    かつ「じゃあ何で浮いてんの？」への引きになる。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N
    e = 1 - (1 - min(1.0, i / (N * 0.30))) ** 3

    cy = 330
    aoa = 0.30                      # 逆さまのぶん、機首を大きく上げている
    nose, tail = 190, 700

    def surf(x, up):
        """上下をひっくり返した翼。ふくらみが下に来る。"""
        t = min(1.0, max(0.0, (x - nose) / (tail - nose)))
        base = cy - (x - nose) * aoa
        if up:
            return base - 5 - 13 * math.sin(math.pi * t ** 0.95)
        return base + 5 + 58 * math.sin(math.pi * t ** 0.60)

    # 空気。翼を過ぎたら下へ抜ける（向きは他の図と同じ）
    for r, dy0 in enumerate((-150, -108, -66, -24, 30, 74)):
        for j in range(3):
            s0 = (p * 1.1 + j / 3 + r * 0.06) % 1.0
            x = -120 + s0 * (W + 240)
            y0 = cy + dy0
            k = math.exp(-abs(dy0) / 120.0)
            def yy(xq):
                if xq < nose:
                    return y0
                return y0 + (xq - nose) * 0.44 * k * e
            pts = [(x - 26 * m, yy(x - 26 * m)) for m in range(6)]
            if pts[0][0] < -70 or pts[0][0] > W + 70:
                continue
            for m in range(5):
                line(d, [pts[m], pts[m+1]], CHALK, 8.5 - m * 1.0,
                     int(230 * (1 - m / 5) ** 1.2))
            dot(d, pts[0][0], pts[0][1], 4.6, CHALK, 240)

    poly = [(x, surf(x, True)) for x in range(nose, tail + 1, 8)]
    poly += [(x, surf(x, False)) for x in range(tail, nose - 1, -8)]
    d.polygon([(x * SS, y * SS) for x, y in poly], fill=CHALK + (255,))
    # 逆さまの目印として、尾を上に出す
    line(d, [(tail, (surf(tail, True) + surf(tail, False)) / 2),
             (tail + 92, (surf(tail, True) + surf(tail, False)) / 2 - 46)], CHALK, 13)

    arrow(d, 420, cy - 100, 420, cy - 232, HEAT, 22, 52, int(255 * e))
    label(d, 62, 116, '逆さま', 72, CHALK, 255, anchor='lm')
    return im.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- 書き出し

def dump(name, fn):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    for old in os.listdir(d):
        os.remove(os.path.join(d, old))
    for i in range(N):
        fn(i).save('%s/%04d.png' % (d, i))
    print('  %-12s %d枚  %dx%d' % (name, N, W, H))



# ---------------------------------------------------------------- 迎え角

AOA_SHOW = 0.26             # 図では迎え角を誇張する。実物の5度は画面上で見えない


def _wing_at(d, cy, aoa, le, te):
    """指定の高さ・傾き・長さで翼を1枚描く。globals を一時的に差し替えるだけ。"""
    global CY, AOA, LE, TE
    keep = (CY, AOA, LE, TE)
    CY, AOA, LE, TE = cy, aoa, le, te
    draw_wing(d)
    CY, AOA, LE, TE = keep


def _air(d, cy, aoa, le, te, bend, alpha=255):
    """翼に当たる空気を横線で描く。bend なら翼の後ろで下へ曲げる。"""
    for dy in (-66, 66):
        y = cy + dy
        y2 = y + (te - le) * aoa * 0.55
        dashed(d, 34, y, le - 12, y, CHALK, 5, 22, alpha)
        line(d, [(le - 12, y), (te, y2)], CHALK, 5, alpha)
        if bend:
            line(d, [(te, y2), (te + 150, y2 + 74)], GOLD, 7, alpha)
        else:
            line(d, [(te, y2), (te + 150, y2)], CHALK, 5, alpha)


def f_aoa(i):
    """傾けない翼と、傾けた翼を上下に並べて比べる図。

    伸びているショート40本の図の作り方を数えたら、前後の比較が23本、
    矢印が24本、色分けが22本だった。こちらは「傾いている」ことを1枚で
    見せるだけで、比べる相手が無かった。何が違うから浮くのかは、
    並べないと分からない。上＝まっすぐで何も起きない、下＝傾けると
    空気が下へ・翼が上へ。色は空気を黄、翼を赤で対にする。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    e = 1 - (1 - min(1.0, i / (N * 0.45))) ** 3      # 下段を水平から起こす

    L, T = 190, 560              # この図だけ翼を短くして、右に説明の場所を作る
    TOP, BOT = 122, 452

    # ── 上段：傾けていない翼。空気はまっすぐ通り抜ける
    _air(d, TOP, 0.0, L, T, False, 200)
    _wing_at(d, TOP, 0.0, L, T)
    label(d, 34, 26, 'まっすぐ', 48, CHALK, 235, anchor='lm')
    label(d, 786, TOP, '浮かない', 46, DIM, 225)

    # 上下を分ける線。比べていることを目で分からせる
    dashed(d, 24, 292, 876, 292, DIM, 3, 16, 110)

    # ── 下段：少し上を向けた翼。空気が下へ、翼が上へ
    aoa = -AOA_SHOW * e
    _air(d, BOT, aoa, L, T, e > 0.5, 235)
    dashed(d, L, BOT, T + 96, BOT, DIM, 4, 18, 120)      # 水平の基準
    _wing_at(d, BOT, aoa, L, T)
    label(d, 34, 606, '少し上を向ける', 50, GOLD, 255, anchor='lm')

    # 言葉は下の行（翼は上向き／空気を下に押す／翼は上へ）が言うので、
    # 図では色と向きだけにする。同じ言葉を2か所で読ませない。
    if e > 0.55:
        al = int(255 * (e - 0.55) / 0.45)
        arrow(d, 132, BOT + 4, 132, BOT - 104, HEAT, 12, 36, al)   # 翼は上（赤）
        arrow(d, 796, BOT + 74, 796, BOT + 168, GOLD, 11, 34, al)  # 空気は下（黄）
    return im.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- 車の窓の手

def capsule(d, x1, y1, x2, y2, w, color, alpha=255):
    """丸い端の棒。腕や手のひらはこれで描くと、板に見えない。"""
    line(d, [(x1, y1), (x2, y2)], color, w, alpha)
    dot(d, x1, y1, w / 2, color, alpha)
    dot(d, x2, y2, w / 2, color, alpha)


def f_hand(i):
    """車の窓から手を出したときの図。

    翼の図とわざと同じ見た目にしてある（空気は左から右、当たって下へ、
    赤い矢印は上へ）。同じ絵に見えることが、そのまま『同じことが起きている』
    という説明になる。言葉で「あれと同じ」と言うより早い。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    e = 1 - (1 - min(1.0, i / (N * 0.5))) ** 3
    up = 58 * e
    ang = math.radians(-18 * e)

    sy = 356 - up                       # 手首の高さ
    hx, hy = 470, sy - 8
    px = hx - 176 * math.cos(ang)
    py = hy - 176 * math.sin(ang)
    pmid = (px + hx) / 2

    def path(y0, x):
        """手のひらを過ぎたら下へ抜ける。翼の図と同じ考え方。"""
        k = math.exp(-abs(y0 - py) / 130.0)
        if x < px:
            return y0
        return y0 + (x - px) * 0.52 * k * e

    # 曲がっていないときの高さ（比べる基準）
    ref = 268
    dashed(d, hx + 30, ref, 866, ref, DIM, 3, 15, 110)

    # 空気
    for k, y0 in enumerate((176, 216, 256, 300)):
        for j in range(4):
            s0 = ((i / N) * 1.15 + j / 4 + k * 0.06) % 1.0
            x = -120 + s0 * (W + 240)
            pts = [(x - 22 * m, path(y0, x - 22 * m)) for m in range(7)]
            if pts[0][0] < -60 or pts[0][0] > W + 60:
                continue
            def inside_window(q):
                return 706 < q[0] < 888 and 140 < q[1] < 472
            for m in range(6):
                if inside_window(pts[m]) or inside_window(pts[m+1]):
                    continue                      # 窓の中を空気が突き抜けて見えるのを防ぐ
                al = int(230 * (1 - m / 6) ** 1.4)
                line(d, [pts[m], pts[m+1]], CHALK, 9 - m * 0.9, al)
            if not inside_window(pts[0]):
                dot(d, pts[0][0], pts[0][1], 4.6, CHALK, 235)

    # 車の窓（右）。腕より先に描いて、腕が手前に来るようにする
    d.rounded_rectangle([716 * SS, 150 * SS, 878 * SS, 462 * SS], 30 * SS,
                        outline=DIM + (200,), width=9 * SS)
    label(d, 797, 116, '車の窓', 56, CHALK, 255)

    # 腕と手のひら
    capsule(d, 786, sy + 18, hx, hy, 58, CHALK)
    capsule(d, hx + 14, hy + 4, px, py, 50, CHALK)

    # 下へ抜ける空気と、持っていかれる腕
    if e > 0.25:
        al = int(255 * min(1.0, (e - 0.25) / 0.35))
        arrow(d, 612, 452, 748, 528, GOLD, 13, 38, al)
        arrow(d, pmid, py - 58, pmid, py - 208, HEAT, 22, 52, al)
        label(d, pmid, py - 250, '腕が上へ', 68, HEAT, al)
    return im.resize((W, H), Image.LANCZOS)


ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def stills():
    """静止画としても使う2枚を、同じ図形定義から書き出す。
    別々に描くと、動く図と止まった図で翼の形が違う、ということが起きる。"""
    os.makedirs(ASSETS, exist_ok=True)
    f_wingrace(N - 1).save(os.path.join(ASSETS, '10_wing_wrong.png'))
    f_airflow(int(N * 0.62), lift=True).save(os.path.join(ASSETS, '11_wing_lift.png'))
    print('  10_wing_wrong.png / 11_wing_lift.png')




# ---------------------------------------------------------------- 電子レンジ
#
# 第2話（飛行機）の実データで分かったこと: 43.2%が冒頭で消え、残った人は
# 75%見てループしていた。つまり中身は効いている。効いた理由のひとつが
# 「図が動いていた」ことなので、電子レンジの図も静止画から連番に作り直す。
#
# 40本の実測で図の作り方は 矢印24・前後の比較23・色分け22・拡大18 だった。
# 比較（f_plate）と色分け（水は青、熱は赤）をここでも使う。

WATER = (108, 168, 214)      # 水の分子。青
HOT   = (224, 92, 66)        # 熱。赤（HEAT と同じ系統）
WAVE  = (231, 178, 62)       # マイクロ波。金


def molecule(d, cx, cy, ang, r=34, alpha=255, col=None):
    """水の分子。酸素1つに水素2つ。向きが分かるように非対称に描く。"""
    col = col or WATER
    d.ellipse([(cx-r)*SS, (cy-r)*SS, (cx+r)*SS, (cy+r)*SS],
              fill=tuple(col) + (alpha,))
    for s in (-1, 1):
        a = ang + s * 0.92                      # 実際の水分子の角度に寄せる
        hx, hy = cx + math.cos(a) * r * 1.5, cy + math.sin(a) * r * 1.5
        d.ellipse([(hx-r*.58)*SS, (hy-r*.58)*SS, (hx+r*.58)*SS, (hy+r*.58)*SS],
                  fill=tuple(CHALK) + (alpha,))
        line(d, [(cx, cy), (hx, hy)], col, 7, alpha)


GRID = [(x, y) for y in (250, 400) for x in (250, 420, 590, 760)]


def f_spin(i):
    """マイクロ波が来ると、水の分子がいっせいに向きを変える図。

    「電波が水を回す」が言葉だけだと入らない。波が左から通り過ぎるのに
    合わせて分子が反転するところを見せると、因果が目で追える。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N
    label(d, 62, 96, '水の分子', 60, WATER, 255, anchor='lm')

    # マイクロ波。左から右へ流れる波。分子はこれに合わせて向きを変える
    wx = -200 + (W + 400) * p
    for k in range(3):
        xs = []
        for t in range(0, W + 1, 8):
            ph = (t - wx) / 150.0
            xs.append((t, 150 + k * 6 + math.sin(ph) * 42 * math.exp(-abs(t-wx)/420)))
        line(d, xs, GOLD, 5, 150 - k * 40)

    for gx, gy in GRID:
        # 波が通り過ぎた分子ほど、大きく振れる
        near = math.exp(-abs(gx - wx) / 260.0)
        ang = math.sin(p * 2*math.pi * 3 + gx * 0.01) * 2.2 * near - math.pi/2
        molecule(d, gx, gy, ang, 34, 255)
    if p > 0.45:
        al = int(255 * min(1.0, (p - 0.45) / 0.25))
        label(d, 470, 560, 'ぐるんぐるん 向きを変える', 62, GOLD, al)
    return im.resize((W, H), Image.LANCZOS)


def f_bump(i):
    """向きを変えた分子が隣とぶつかって、そこが熱くなる図。"""
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N
    label(d, 62, 96, 'ぶつかる', 60, CHALK, 255, anchor='lm')

    for k, (gx, gy) in enumerate(GRID):
        w = 2*math.pi * 2.2 * p + k * 1.1
        dx, dy = math.cos(w) * 26, math.sin(w * 1.3) * 20
        ang = math.sin(w) * 2.4 - math.pi/2
        # ぶつかった瞬間だけ赤く光らせる。色で「ここで熱が出た」と分かる
        hit = max(0.0, math.sin(w)) ** 6
        col = tuple(int(WATER[c] + (HOT[c] - WATER[c]) * hit) for c in range(3))
        if hit > 0.35:
            r = 46 + 26 * hit
            d.ellipse([(gx+dx-r)*SS, (gy+dy-r)*SS, (gx+dx+r)*SS, (gy+dy+r)*SS],
                      fill=tuple(HOT) + (int(70 * hit),))
        molecule(d, gx + dx, gy + dy, ang, 34, 255, col)

    if p > 0.4:
        al = int(255 * min(1.0, (p - 0.4) / 0.25))
        arrow(d, 470, 520, 470, 452, HOT, 11, 34, al)
        label(d, 470, 570, 'これが熱', 66, HOT, al)
    return im.resize((W, H), Image.LANCZOS)


def f_plate(i):
    """お皿と食べ物を並べて比べる図。上＝水なし、下＝水あり。

    40本の実測で「前後の比較」は23本。飛行機でこれを入れたら効いたので
    ここでも使う。お皿が温まらない理由が、並べるだけで分かる。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N
    e = 1 - (1 - min(1.0, i / (N * 0.5))) ** 3

    # 電波を左から流す。動いていたのは半径22の分子4つだけで、コマ間の
    # 差が 0.5 しか出ず、実測では静止画と同じ扱いになっていた
    # （画面に5.9秒出ているのに動きゼロ）。
    # 「同じ電波が両方に当たっているのに、下だけ反応する」が図の主旨なので、
    # その電波を大きく描いて流す。端から端まで動く物が要る。
    for row in (160, 470):
        for k in range(3):
            x = ((p * 1.6 + k / 3.0) % 1.0) * (W + 180) - 90
            for j in range(3):
                d.arc([int((x - 46 + j*13) * SS), int((row - 54) * SS),
                       int((x + 46 + j*13) * SS), int((row + 54) * SS)],
                      -60, 60, fill=WAVE + (int(150 * e),), width=int(5 * SS))

    # ── 上：お皿。水の分子が無いので、波が来ても何も起きない
    label(d, 40, 60, 'お皿', 60, CHALK, 235, anchor='lm')
    capsule(d, 210, 160, 620, 160, 34, CHALK, 220)
    label(d, 748, 160, '水も油もなし', 46, DIM, 235)
    if e > 0.5:
        label(d, 465, 246, '温まらない', 60, DIM, int(255*(e-0.5)/0.5))

    dashed(d, 24, 320, 876, 320, DIM, 3, 16, 110)

    # ── 下：食べ物。中に水があるので、そこが熱くなる
    label(d, 40, 372, '食べ物', 60, CHALK, 255, anchor='lm')
    capsule(d, 210, 470, 620, 470, 34, CHALK, 220)
    # 分子は大きくして上下にも揺らす。小さく回るだけでは動いて見えない。
    for k, gx in enumerate((270, 370, 470, 570)):
        w = 2*math.pi * 2.0 * p + k
        hit = max(0.0, math.sin(w)) ** 5 * e
        col = tuple(int(WATER[c] + (HOT[c] - WATER[c]) * hit) for c in range(3))
        gy = 470 + math.sin(w * 2 + k) * 9 * e
        if hit > 0.35:                      # ぶつかった瞬間だけ光る
            dot(d, gx, gy, int(30 + 26 * hit), HOT, int(90 * hit))
        molecule(d, gx, gy, math.sin(w) * 2.0 - math.pi/2, 30, 255, col)
    if e > 0.5:
        al = int(255 * (e - 0.5) / 0.5)
        label(d, 748, 470, '水と油あり', 48, GOLD, al)
        label(d, 465, 566, 'ここが熱くなる', 62, HOT, al)
    return im.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- ペンギンの足

COLD = (96, 156, 214)        # 冷たい血。青
WARM = (222, 88, 62)         # 温かい血。赤


def _blood(d, x, y, r, warm, alpha=255):
    """血の粒。温かいほど赤、冷たいほど青。"""
    c = tuple(int(COLD[k] + (WARM[k] - COLD[k]) * warm) for k in range(3))
    dot(d, x, y, r, c, alpha)


def f_rete(i, swap=False):
    """ペンギンの足の付け根。行きの血と帰りの血が並んで熱を渡し合う図。

    伝えたいのは1つだけ。「足へ行く温かい血が、足から戻る冷たい血を
    温め直している」。だから、上から下へ降りる赤い粒と、下から上へ
    のぼる青い粒を、隣り合わせに置いて、その間で熱をやり取りさせる。

    swap=True … 仕組みが無い場合。熱が渡らず、冷たい血がそのまま
    胴体へ帰る。前後の比較は実測40本中23本が使っていた。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N
    e = 1 - (1 - min(1.0, i / (N * 0.35))) ** 3

    TOP, BOT = 120, 560              # 胴体側 / 足側
    XA, XB = 330, 560                # 行き（動脈）と帰り（静脈）のx

    # 胴体と足の帯
    capsule(d, 120, TOP - 46, 780, TOP - 46, 54, CHALK, 60)
    label(d, 120, TOP - 46, 'からだ 38度', 46, CHALK, 235, anchor='lm')
    capsule(d, 250, BOT + 52, 650, BOT + 52, 46, CHALK, 55)
    label(d, 250, BOT + 52, '足 0度', 46, COLD, 240, anchor='lm')

    # 血管
    capsule(d, XA, TOP, XA, BOT, 40, (236, 232, 220), 45)
    capsule(d, XB, TOP, XB, BOT, 40, (236, 232, 220), 45)
    label(d, XA, TOP - 104, '行き', 44, WARM, int(235*e))
    label(d, XB, TOP - 104, '帰り', 44, COLD, int(235*e))

    # 熱を渡す矢印。仕組みが有るときだけ、行き→帰りへ横に渡る
    if not swap:
        for k in range(4):
            yy = TOP + 70 + k * 118
            a = int(210 * e * (0.45 + 0.55 * max(0.0, math.sin(2*math.pi*(p*1.4 - k*0.12)))))
            arrow(d, XA + 34, yy, XB - 34, yy, GOLD, 8, 26, a)

    # 粒。行きは上から下へ、下るほど冷える。帰りは下から上へ、のぼるほど温まる
    for j in range(6):
        s0 = (p * 1.1 + j / 6.0) % 1.0
        y = TOP + (BOT - TOP) * s0
        _blood(d, XA, y, 17, 1.0 - s0, int(255 * e))
        y2 = BOT - (BOT - TOP) * s0
        # 仕組みが無ければ、帰りは冷たいまま上まで行く
        warm = 0.0 if swap else s0
        _blood(d, XB, y2, 17, warm, int(255 * e))

    if swap and e > 0.6:
        # TOP-150 は画面外（y=-30）だった。血管の間の空きに置く
        label(d, 450, (TOP + BOT) // 2, '体温が逃げる', 52, WARM,
              int(255 * (e - 0.6) / 0.4))
    return im.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- 冷蔵庫

def f_pump(i, back=False):
    """冷蔵庫。庫内の熱を管が拾って、外へ運んで捨てる図。

    伝えたいのは1つ。「冷たさを作っているのではなく、熱を運び出している」。
    最初は管を箱の外に描いていたが、それだと「中の熱を拾う」が絵に出ない。
    管は庫内を通してから外へ出す。

    back=True … 裏側だけを強調する。実際に40〜50度になる所。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N
    e = 1 - (1 - min(1.0, i / (N * 0.35))) ** 3

    BX0, BY0, BX1, BY1 = 80, 150, 520, 540      # 庫内
    OX = 730                                     # 外（裏）
    LO, HI = BY1 - 90, BY0 + 90                  # 管の下段・上段

    d.rounded_rectangle([BX0*SS, BY0*SS, BX1*SS, BY1*SS], radius=18*SS,
                        outline=CHALK + (240,), width=int(7*SS))
    # 「庫内」の四角だけでは箱にしか見えない、というのが第5話の講評での
    # 一番はっきりした指摘だった。箱の中は管のアニメで埋まっているので、
    # 上の空き帯（管の上段より上）に小さな冷蔵庫の絵を1つ添えるだけにする。
    # 文字を読まなくても「この箱＝冷蔵庫」と分かる（サムネのアイコン化と同じ発想）。
    ix0, iy0, ix1, iy1 = BX0 + 22, BY0 + 12, BX0 + 176, BY0 + 84
    ia = int(235 * e)
    d.rounded_rectangle([ix0*SS, iy0*SS, ix1*SS, iy1*SS], radius=9*SS,
                        outline=COLD + (ia,), width=int(5*SS))
    isplit = iy0 + int((iy1 - iy0) * 0.34)
    line(d, [(ix0 + 7, isplit), (ix1 - 7, isplit)], COLD, 4, ia)
    ihx = ix1 - 18
    for hy0, hy1 in ((iy0 + 9, isplit - 7), (isplit + 7, iy1 - 9)):
        d.rounded_rectangle([(ihx-4)*SS, hy0*SS, (ihx+4)*SS, hy1*SS], radius=4*SS,
                            fill=COLD + (ia,))
    label(d, (BX0+BX1)//2, BY0 - 46, '庫内', 50, COLD, int(240*e))
    label(d, OX, BY0 - 46, '外（裏）', 50, HEAT, int(240*e))

    # 拾われる前の熱。管の下段のまわりに漂わせる
    for k in range(4):
        a2 = int(200 * e * max(0.0, math.sin(2*math.pi*(p*1.1 - k*0.19))))
        dot(d, 150 + k*95, LO - 66 - 26*math.sin(p*6.28 + k), 18, HEAT, a2)

    # 管の一周。庫内の下を右へ → 外で上へ → 庫内へ戻る
    path = [(BX0+55, LO), (OX, LO), (OX, HI), (BX0+55, HI), (BX0+55, LO)]
    for a, b in zip(path, path[1:]):
        # 75では黒板の上で消えていた。管が見えないと話が伝わらない
        line(d, [a, b], (236, 232, 220), 30, 165)

    # 裏側の放熱
    if e > 0.4:
        al = int(210 * (e - 0.4) / 0.6)
        for k in range(4):
            yy = HI + 40 + k * 84
            w = 2*math.pi * 1.6 * p + k
            arrow(d, OX + 44, yy, OX + 44 + 66 + 16*math.sin(w), yy,
                  HEAT, 9, 26, al)
        if back:
            label(d, OX + 40, BY1 + 6, '40〜50度', 54, HEAT, al)

    # 粒。庫内で熱を拾って赤くなり、外で放して青くなる
    L = [math.hypot(b[0]-a[0], b[1]-a[1]) for a, b in zip(path, path[1:])]
    tot = sum(L)
    for j in range(8):
        s0 = (p * 1.15 + j / 8.0) % 1.0
        dist = s0 * tot
        x, y = path[0]
        for (a, b), ln in zip(zip(path, path[1:]), L):
            if dist <= ln:
                x = a[0] + (b[0]-a[0]) * dist/ln
                y = a[1] + (b[1]-a[1]) * dist/ln
                break
            dist -= ln
        f = L[0] / tot                      # 庫内の下段が終わる位置
        g = (L[0] + L[1]) / tot             # 外の縦が終わる位置
        if s0 < f:      warm = s0 / f                     # 拾いながら温まる
        elif s0 < g:    warm = 1.0 - (s0 - f) / (g - f)   # 外で放して冷える
        else:           warm = 0.0                        # 冷たいまま戻る
        c = tuple(int(COLD[k] + (WARM[k]-COLD[k]) * warm) for k in range(3))
        dot(d, x, y, 21, c, int(255*e))
    return im.resize((W, H), Image.LANCZOS)


def f_evap(i):
    """打ち水。水が気体になるとき、地面の熱を持っていく図。

    第5話は「打ち水したら涼しいやろ」と口で言うだけで、絵にしていなかった。
    例えは音だけで流れて、画面はずっと同じ管の図のままだった。
    ここを絵にすると、たとえが効くのと、同じ画が続くのを断つのと、
    両方が一度に片づく。
    """
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N
    e = 1 - (1 - min(1.0, i / (N * 0.3))) ** 3

    GY = 470                                    # 地面
    capsule(d, 60, GY, 840, GY, 40, CHALK, 70)
    label(d, 450, GY + 76, '地面', 46, DIM, int(235 * e))

    # 地面に残る熱。水が持っていくぶんだけ減る
    for k in range(6):
        ph = (p * 1.3 + k / 6.0) % 1.0
        al = int(220 * e * max(0.0, 1 - ph * 1.6))
        dot(d, 150 + k * 110, GY - 30, 26, HEAT, al)

    # 水の粒が上がりながら小さくなって消える。赤い熱を連れていく
    for k in range(6):
        ph = (p * 1.3 + k / 6.0) % 1.0
        x = 150 + k * 110 + 18 * math.sin(ph * 6.0 + k)
        y = GY - 40 - ph * 300
        r = int(36 * (1 - ph * 0.65))
        al = int(245 * e * max(0.0, 1 - ph))
        if ph > 0.10:
            dot(d, x, y, r, WATER, al)
            dot(d, x + 7, y - 9, max(5, r // 3), HEAT, int(al * 0.9))

    label(d, 450, 90, '水が気体になるとき', 52, CHALK, int(240 * e))
    label(d, 450, 168, '熱を持っていく', 56, GOLD, int(240 * e))
    return im.resize((W, H), Image.LANCZOS)


if __name__ == '__main__':
    print('黒板アニメを書き出し中...')
    dump('wingrace', f_wingrace)
    dump('airflow', lambda i: f_airflow(i, lift=False))
    dump('airlift', lambda i: f_airflow(i, lift=True))
    dump('aoa', f_aoa)
    dump('hand', f_hand)
    dump('same', f_same)
    dump('invert', f_invert)
    dump('spin', f_spin)          # 電子レンジ：分子が向きを変える
    dump('bump', f_bump)          # 電子レンジ：ぶつかって熱になる
    dump('plate', f_plate)        # 電子レンジ：皿と食べ物を比べる
    dump('rete', f_rete)                            # ペンギン：熱を渡し合う
    dump('rete0', lambda i: f_rete(i, swap=True))   # ペンギン：渡さない場合
    dump('pump', f_pump)                            # 冷蔵庫：熱を運び出す
    dump('pumpb', lambda i: f_pump(i, back=True))   # 冷蔵庫：裏が40〜50度
    dump('evap', f_evap)                            # 冷蔵庫：打ち水
    stills()
    print('完了 → ' + OUT)
