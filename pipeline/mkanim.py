"""黒板用のアニメーションを、フレーム連番で書き出す。

矢印を1本置くだけでは「下に矢印がある」としか伝わらない。
空気の粒が実際に翼に当たって、軌道を変えて下へ抜けていくところを見せる。
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw

W, H = 900, 520
N = 48                      # ループするフレーム数
CHALK = (239, 233, 218, 255)
HEAT = (206, 78, 55, 255)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clips')

# 翼（横から見た形）
WING = [(150, 300), (640, 258), (640, 300), (150, 316)]
LE, TE = 150, 640           # 前縁・後縁のx


def wing_y(x):
    """翼の下面のおおよその高さ。"""
    if x <= LE: return 308
    if x >= TE: return 279
    return 308 + (279 - 308) * (x - LE) / (TE - LE)


def path(y0, s):
    """粒の軌道。翼に当たるまでは水平、翼を過ぎると下へ曲がる。
    s は 0→1 の進み具合。"""
    x = -60 + s * (W + 160)
    if x < LE:
        return x, y0
    # 翼に沿って下がり、後縁を過ぎるとさらに下へ抜ける
    t = min(1.0, (x - LE) / (TE - LE))
    y = y0 + (wing_y(x) - wing_y(LE)) * t * 1.0
    if x > TE:
        y += (x - TE) * 0.42                   # 後流が下向きに曲がる
    return x, y


def frame(i, show_lift=False, show_flow=True):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = i / N

    if show_flow:
        rows = (188, 214, 240, 266)            # 翼の上を通る流れ
        below = (330, 356)                     # 翼の下を通る流れ
        for k, y0 in enumerate(rows + below):
            for j in range(5):
                s = (p + j / 5 + k * 0.04) % 1.0
                x, y = path(y0, s)
                if x < -20 or x > W + 20:
                    continue
                # 進行方向に少し伸ばした粒（速度が見える）
                x2, y2 = path(y0, max(0.0, s - 0.022))
                d.line([x2, y2, x, y], fill=CHALK, width=7)

    d.polygon(WING, fill=CHALK)                # 翼
    d.line([(640, 258), (720, 292)], fill=CHALK, width=13)

    if show_lift:
        # 揚力。粒が下へ抜けているのと同時に出す
        k = 0.5 - 0.5 * math.cos(2 * math.pi * p)
        top = 250 - 120 - int(26 * k)
        d.line([(400, 250), (400, top)], fill=HEAT, width=18)
        d.polygon([(400, top - 34), (368, top + 6), (432, top + 6)], fill=HEAT)
    return im


def dump(name, **kw):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    for i in range(N):
        frame(i, **kw).save('%s/%04d.png' % (d, i))
    print('  %-12s %d枚' % (name, N))


if __name__ == '__main__':
    print('黒板アニメを書き出し中...')
    dump('airflow')                       # 空気が翼を通って下へ曲がる
    dump('airlift', show_lift=True)       # 同じ流れ＋上向きの揚力
    print('完了 → ' + OUT)
