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
    d.text((x * SS, y * SS), text, font=font(size * SS, face or GOTHIC),
           fill=tuple(color) + (alpha,), anchor=anchor)


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
    label(d, 62, 140, '空気', 40, DIM, 210, anchor='lm')
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
    label(d, LE + 40, 120, '同時に出発', 44, CHALK, 235)
    label(d, TE - 26, 120, 'ゴール', 44, CHALK, 235)

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

    label(d, 62, 66, '手', 56, DIM, 225, anchor='lm')
    label(d, 62, 368, '翼', 56, DIM, 225, anchor='lm')
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
    label(d, 62, 116, '逆さま', 52, DIM, 225, anchor='lm')
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


def f_aoa(i):
    """翼が「少し上を向いている」ことだけを見せる図。
    ここを言葉で済ませると、次の『なぜ下に曲がるのか』が宙に浮く。"""
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    e = 1 - (1 - min(1.0, i / (N * 0.5))) ** 3      # 水平から起こしていく

    global AOA
    keep = AOA
    AOA = -AOA_SHOW * e                              # 前縁を上げる（符号が逆）
    cy = CY + 40

    # 進む向きの基準線。これが無いと「傾いている」が比べられない
    dashed(d, 110, cy, 830, cy, DIM, 4, 18, 150)
    label(d, 118, cy + 44, '進む向き', 38, DIM, 210, anchor='lm')
    arrow(d, 740, cy, 830, cy, DIM, 6, 24, 150)

    # 傾きの目印（翼弦線）
    x0, y0 = LE, cy
    x1, y1 = TE, cy + (TE - LE) * AOA
    line(d, [(x0, y0), (x1, y1)], GOLD, 5, int(220 * e))

    dy = 40
    draw_wing(d)
    AOA = keep

    if e > 0.4:
        al = int(255 * (e - 0.4) / 0.6)
        label(d, 470, cy - 190, '少しだけ上を向いている', 46, GOLD, al)
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
    label(d, 797, 116, '車の窓', 38, DIM, 210)

    # 腕と手のひら
    capsule(d, 786, sy + 18, hx, hy, 58, CHALK)
    capsule(d, hx + 14, hy + 4, px, py, 50, CHALK)

    # 下へ抜ける空気と、持っていかれる腕
    if e > 0.25:
        al = int(255 * min(1.0, (e - 0.25) / 0.35))
        arrow(d, 612, 452, 748, 528, GOLD, 13, 38, al)
        arrow(d, pmid, py - 58, pmid, py - 208, HEAT, 22, 52, al)
        label(d, pmid, py - 250, '腕が上へ', 46, HEAT, al)
    return im.resize((W, H), Image.LANCZOS)


ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def stills():
    """静止画としても使う2枚を、同じ図形定義から書き出す。
    別々に描くと、動く図と止まった図で翼の形が違う、ということが起きる。"""
    os.makedirs(ASSETS, exist_ok=True)
    f_wingrace(N - 1).save(os.path.join(ASSETS, '10_wing_wrong.png'))
    f_airflow(int(N * 0.62), lift=True).save(os.path.join(ASSETS, '11_wing_lift.png'))
    print('  10_wing_wrong.png / 11_wing_lift.png')


if __name__ == '__main__':
    print('黒板アニメを書き出し中...')
    dump('wingrace', f_wingrace)
    dump('airflow', lambda i: f_airflow(i, lift=False))
    dump('airlift', lambda i: f_airflow(i, lift=True))
    dump('aoa', f_aoa)
    dump('hand', f_hand)
    dump('same', f_same)
    dump('invert', f_invert)
    stills()
    print('完了 → ' + OUT)
