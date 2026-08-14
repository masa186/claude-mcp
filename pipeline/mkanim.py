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
    label(d, 62, 140, '空気', 40, DIM, 210, anchor='lm')
    a1 = int(255 * min(1.0, max(0.0, (p - 0.16) / 0.22)))
    if a1 > 8:
        arrow(d, 806, ry + 8, 806, stream_y(ry, 806) - 8, GOLD, 9, 28, a1)
        arrow(d, 590, 486, 750, 546, GOLD, 13, 38, a1)

    if lift:
        # 「下へ押した分だけ上へ押し返される」の対を、同じ画面に出す
        k = 0.5 - 0.5 * math.cos(2 * math.pi * min(1.0, p / 0.5))
        a2 = int(255 * min(1.0, p / 0.30))
        y0 = upper(430) - 10
        arrow(d, 430, y0, 430, y0 - 148 - int(28 * k), HEAT, 24, 56, a2)
    return im.resize((W, H), Image.LANCZOS)


def f_wingrace(i):
    """学校の説明の反証。同時に出発 → 同時には着かない。"""
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N

    # 通る道を薄く敷いておく（どこを見ればいいかを先に示す）
    for y0, col in ((258, DIM), (432, DIM)):
        pts = [at(y0, t / 60.0) for t in range(61)]
        line(d, pts, col, 3, 90)

    draw_wing(d)

    # 出発線とゴール線
    dashed(d, LE, 96, LE, 578, DIM, 3, 16, 150)
    dashed(d, TE, 96, TE, 578, DIM, 3, 16, 150)
    label(d, LE + 42, 68, '同時に出発', 42, CHALK, 235)
    label(d, TE - 28, 68, 'ゴール', 42, CHALK, 235)

    # 上の粒と下の粒。s=0 で前縁、s=1 で後縁に着くように正規化する
    def s_of(y0, frac):
        xs, cum = table(y0)
        def cum_at(xt):
            for a, b, ca, cb in zip(xs, xs[1:], cum, cum[1:]):
                if a <= xt <= b:
                    return ca + (cb - ca) * (xt - a) / (b - a)
            return cum[-1]
        c0, c1 = cum_at(LE), cum_at(TE)
        return c0 + (c1 - c0) * frac

    run = min(1.0, p / 0.72)                 # 0.72 で上の粒がゴール
    up_x, up_y = at(258, s_of(258, run))
    # 上の空気のほうが速い。上がゴールしたとき、下はまだ3割ほど手前にいる
    dn_x, dn_y = at(432, s_of(432, run * 0.70))

    # オチの赤文字が出たら、説明用の注記は引っ込める（重ならないように）
    la = int(210 * (1.0 if run < 1.0 else max(0.0, 1 - (p - 0.72) / 0.08)))
    if la > 6:
        label(d, 348, 158, '上を通る空気', 42, DIM, la)
        label(d, 348, 552, '下を通る空気', 42, DIM, la)

    dot(d, up_x, up_y, 17, HEAT)
    dot(d, dn_x, dn_y, 17, GOLD)

    if run >= 1.0:
        # 上は着いた。下はまだ手前 → そこにズレが見えている
        a = int(255 * min(1.0, (p - 0.72) / 0.10))
        arrow(d, dn_x + 24, dn_y, TE - 6, dn_y, HEAT, 9, 28, a)
        label(d, (dn_x + TE) / 2, dn_y - 44, 'まだ着いてない', 42, HEAT, a)
        label(d, 450, 612, '「同時に着く」は起きない', 52, HEAT, a)
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
    stills()
    print('完了 → ' + OUT)
