"""題材ごとに描き直さない、使い回しの図。

ジョイ教授の雑学部屋は116本すべてが同じ型で、変えているのは
「対象」と「煽り」だけだった。こちらは1本ごとに図を4つ新規に描いて
いて、それが1日1本を不可能にしていた。

ここでは「形は固定、中身は引数」にする。数字と語を渡すだけで
連番が出る。同じ引数なら作り直さない（名前にハッシュを入れる）。

  from fig import bar, span, huge, versus, steps
  name = bar([('昔', 40, None), ('今', 7, GOLD)], unit='分')
  # → clips/f_xxxxxxxx/ に72枚。render の fig= にそのまま渡せる
"""
import os, hashlib, json
from PIL import Image, ImageDraw
import mkanim as M
from mkanim import W, H, SS, N, CHALK, DIM, GOLD, HEAT, NOFADE, line, dot, label, arrow

OUT = M.OUT
TOP_Y, BOT_Y = 54, 576


# ---------------------------------------------------------------- 動かす
# 化け学のふしぎ（参考2）は 0.29秒/カット・動き11.55 だった。
# こちらの第10話は 2.87秒/カット・動き3.53 で、10倍の開きがある。
# ショットを増やすだけでは届かない。図そのものが動き続ける必要がある。
#
# 出そろったら止まる、をやめる。出たあとも小刻みに動かす。
import math as _m


def _bob(i, amp=6.0, hz=1.6, phase=0.0):
    """ゆっくり上下する。要素ごとに位相をずらすと、画面全体が呼吸する。"""
    return amp * _m.sin(2 * _m.pi * (hz * i / N) + phase)


def _pop_in(i, at, span=0.18):
    """0→1。at(0..1) から span かけて出る。行き過ぎてから戻る。"""
    p = i / N
    t = (p - at) / span
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return 1 - (1 - t) ** 3


def _overshoot(t):
    """1.0 を少し超えてから戻る倍率。出た瞬間だけ大きく見せる。"""
    if t >= 1:
        return 1.0
    return 1 + 0.28 * _m.sin(_m.pi * t)


def _dir(kind, spec):
    key = hashlib.sha1((kind + json.dumps(spec, ensure_ascii=False,
                                          sort_keys=True, default=str)).encode()).hexdigest()[:10]
    return 'f_%s_%s' % (kind, key)


def _dump(name, fn):
    d = os.path.join(OUT, name)
    if os.path.isdir(d) and len(os.listdir(d)) == N:
        return name + '/'
    os.makedirs(d, exist_ok=True)
    for old in os.listdir(d):
        os.remove(os.path.join(d, old))
    for i in range(N):
        fn(i).save('%s/%04d.png' % (d, i))
    return name + '/'


def _rrect(d, box, radius, fill=None, outline=None, width=0):
    """mkanim の line/dot/label は中で SS 倍しているが、PIL を直接呼ぶ所は
    自分で倍にしないと 900x640 の座標で 1800x1280 に描いてしまう。
    最初これを忘れて、棒が半分の大きさ・枠が左上へずれていた。"""
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS),
                        radius=int(radius * SS), fill=fill,
                        outline=outline, width=int(width * SS))


def _canvas():
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


# ---------------------------------------------------------------- 棒くらべ
def bar(items, unit='', head=''):
    """2〜3本の棒で大小をくらべる。items=[(ラベル, 値, 色orNone), ...]

    「40分が7時間になった」「16kgかかっている」のような
    大小がオチになる回は、これ1つで足りる。
    """
    spec = dict(items=[(a, b, c) for a, b, c in items], unit=unit, head=head)
    name = _dir('bar', spec)

    def draw(i):
        im, d = _canvas()
        p, e = i / N, NOFADE
        n = len(items)
        mx = max(v for _, v, _ in items) or 1
        x0, x1 = 120, 780
        gap = (x1 - x0) / n
        base = 520
        if head:
            label(d, 450, TOP_Y + 30, head, 62, CHALK, int(236 * e))
        for k, (lab, val, col) in enumerate(items):
            cx = int(x0 + gap * (k + 0.5))
            grow = min(1.0, max(0.0, (p * 2.6) - k * 0.22))
            # 40 対 420 のように差が10倍あると、小さい方が線になって消える。
            # 平方根にして、一番小さい棒も必ず見えるようにする
            # 高さの上限。base(520) から値ラベル(46)を引いた位置が、
            # 見出し(TOP_Y+30, 高さ62)の下端より上に来ると重なる。
            # 90+300 だと 84 になって「もつ時間420分」と重なっていた。
            h = (70 + 260 * (val / mx) ** 0.5) * grow
            # 伸びきったら止まる、をやめる。わずかに脈打たせる
            if grow >= 1:
                h *= 1 + 0.022 * _m.sin(2 * _m.pi * (2.0 * i / N) + k * 1.7)
            h = int(h)
            c = col or DIM
            bw = int(gap * 0.34)
            _rrect(d, (cx - bw, base - h, cx + bw, base), 12,
                   fill=c + (int(228 * e),))
            label(d, cx, base + 52, lab, 54, CHALK, int(232 * e))
            if grow > 0.55:
                al = int(252 * e * min(1.0, (grow - 0.55) / 0.25))
                txt = ('%g' % val) + unit
                label(d, cx, base - h - 46, txt, 64, c, al)
        return im.resize((W, H), Image.LANCZOS)
    return _dump(name, draw)


# ---------------------------------------------------------------- 期間
def span(a_lab, b_lab, mid, head=''):
    """2点のあいだ。「1810年→1858年、あいだ48年」の形。"""
    spec = dict(a=a_lab, b=b_lab, mid=mid, head=head)
    name = _dir('span', spec)

    def draw(i):
        im, d = _canvas()
        p, e = i / N, NOFADE
        Y, X0, X1 = 360, 140, 760
        if head:
            label(d, 450, TOP_Y + 30, head, 60, CHALK, int(234 * e))
        line(d, [(X0, Y), (X1, Y)], CHALK, 14, int(150 * e))
        for x, t in ((X0, a_lab), (X1, b_lab)):
            dot(d, x, Y, 24, CHALK, int(246 * e))
            label(d, x, Y + 88, t, 66, CHALK, int(240 * e))
        prog = min(1.0, p * 2.4)
        px = X0 + (X1 - X0) * prog
        line(d, [(X0, Y), (px, Y)], GOLD, 18, int(248 * e))
        rr = 30 + 6 * _m.sin(2 * _m.pi * (2.6 * i / N))
        dot(d, px, Y, rr, GOLD, int(252 * e))
        if prog > 0.45:
            al = int(252 * e * min(1.0, (prog - 0.45) / 0.25))
            label(d, 450, Y - 104, mid, 124, GOLD, al)
        return im.resize((W, H), Image.LANCZOS)
    return _dump(name, draw)


# ---------------------------------------------------------------- 大きい数字
def huge(value, sub='', head='', sub_at=0.30):
    """数字を1つだけ、画面いっぱいに。オチの1枚に使う。

    sub_at は添え書きが出てくる位置（0〜1）。既定では少し遅らせて、
    数字を先に読ませる。ただし動画の1コマ目に使うときは 0 にすること。
    一覧に出るのは1コマ目なので、そこで添え書きが消えていると
    「7.5倍」だけが浮いて、何と比べているのか分からない。
    """
    spec = dict(v=value, sub=sub, head=head, at=sub_at)
    name = _dir('huge', spec)

    def draw(i):
        im, d = _canvas()
        p, e = i / N, NOFADE
        if head:
            label(d, 450, TOP_Y + 34, head, 60, CHALK, int(232 * e))
        # 出はじめに行き過ぎてから戻り、そのあとも脈打たせる。
        # 止まった数字は0.3秒で見飽きる。
        k = _overshoot(min(1.0, p / 0.16)) if p < 0.16 else 1.0
        k *= 1 + 0.035 * _m.sin(2 * _m.pi * (2.4 * i / N))
        y = 330 + _bob(i, 7, 1.5)
        label(d, 450, y, str(value), int(190 * k), GOLD, int(254 * e))
        if sub and p >= sub_at:
            al = int(246 * e * min(1.0, (p - sub_at) / 0.22)) if sub_at > 0 \
                 else int(246 * e)
            label(d, 450, BOT_Y - 40, sub, 72, CHALK, al)
        return im.resize((W, H), Image.LANCZOS)
    return _dump(name, draw)


# ---------------------------------------------------------------- 対決
def versus(left, right, win=None, head='', col=None):
    """左右にくらべる。win='r' なら右を目立たせる。

    色を選べるようにした理由。金色は他の図では「これが答え」の色で
    使っている。危ないほうを指す図で金色を使うと、
    「42度で10分」が推奨の側に見えてしまう。
    危険を指すときは col=HEAT のように赤を渡すこと。
    """
    col = col or GOLD
    spec = dict(l=left, r=right, w=win, head=head, c=col)
    name = _dir('vs', spec)

    def draw(i):
        im, d = _canvas()
        p, e = i / N, NOFADE
        if head:
            label(d, 450, TOP_Y + 30, head, 60, CHALK, int(234 * e))
        line(d, [(450, 190), (450, 500)], DIM, 8, int(140 * e))
        for side, txt in ((-1, left), (1, right)):
            cx = 450 + side * 200
            side_win = (win == 'r' and side > 0) or (win == 'l' and side < 0)
            ink = col if (side_win and p > 0.42) else CHALK
            al = int(248 * e * min(1.0, max(0.0, p * 3 - (0 if side < 0 else 0.3))))
            for j, ln in enumerate(txt.split('\n')[:2]):
                label(d, cx, 300 + j * 84, ln, 78, ink, al)
        if p > 0.42 and win:
            al = int(250 * e * min(1.0, (p - 0.42) / 0.24))
            cx = 450 + (200 if win == 'r' else -200)
            g = 6 * _m.sin(2 * _m.pi * (2.2 * i / N))
            _rrect(d, (cx - 190 - g, 232 - g, cx + 190 + g, 452 + g), 26,
                   outline=col + (al,), width=11)
        return im.resize((W, H), Image.LANCZOS)
    return _dump(name, draw)


# ---------------------------------------------------------------- 手順
def steps(labels, head=''):
    """3つの段を順に出す。出たあとも止めない。

    「今どれの話か」を光で示すと、画面が常に変わり続ける。
    化け学（参考2）は0.29秒/カットで、止まっている時間が無かった。
    """
    spec = dict(s=list(labels), head=head)
    name = _dir('step', spec)

    def draw(i):
        im, d = _canvas()
        p, e = i / N, NOFADE
        if head:
            label(d, 450, TOP_Y + 26, head, 68, CHALK, int(234 * e))
        n = len(labels)
        # 板に載せて縮むと、70では小さかった。実測の埋まりも
        # 参考6本の中央値25.8%に対して17.9%しか無い。文字を大きくして詰める。
        y0, dy = 236, 142
        # 今どの段に光を当てるか。尺を n 等分して順に移る
        cur = min(n - 1, int(p * n * 1.15))
        for k, t in enumerate(labels):
            a = _pop_in(i, k * 0.16, 0.16)
            if a <= 0:
                continue
            on = (k == cur)
            y = y0 + k * dy + _bob(i, 5 if on else 2.5, 1.4, k * 1.1)
            col = GOLD if on else DIM
            r = 18 + (5 * _m.sin(2 * _m.pi * (2.2 * i / N)) if on else 0)
            dot(d, 152, y, r, col, int(244 * e * a))
            sz = int(88 * (_overshoot((i / N - k * 0.16) / 0.16) if a < 1 else 1))
            label(d, 200, y, t, sz, CHALK if on else DIM, int(248 * e * a), anchor='lm')
        return im.resize((W, H), Image.LANCZOS)
    return _dump(name, draw)


if __name__ == '__main__':
    print(bar([('昔', 40, None), ('今', 420, GOLD)], unit='分', head='もつ時間'))
    print(span('1810年', '1858年', '48年', head='缶詰ができてから'))
    print(huge('300kg', sub='窓1枚にかかる力'))
    print(versus('刺す', '転がす', win='r', head='どっちが速い'))
    print(steps(['粉のまま燃やす', '棒にする', 'うずまきにする'], head='改良'))
