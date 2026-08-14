"""
カワウソ黒板解説チャンネル ／ フレームレンダラー
================================================
台本を dict で書くと、1080x1920 のフレーム連番を書き出す。
ffmpeg で連結すれば MP4 になる（Colab 側で実行）。

自動でつく動き:
  - 呼吸（2.6秒周期のごく小さい伸縮）
  - まばたき（不等間隔・0.1秒）
  - カット頭の立ち上がり（0.15秒）
  - 黒板の文字がチョークで書かれるワイプ
  - 図の回転（水分子）
  - 指し棒のタップ（手を軸に回転）

使い方:
  python3 render.py --probe 0.5 7.0 12.0 19.0   # 指定秒のフレームだけ確認
  python3 render.py --all                        # 全フレーム書き出し
"""
import os, sys, math, argparse
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')
OUT = os.path.join(HERE, 'frames')

W, H = 1080, 1920
FPS = 30

CHALK   = (239, 233, 218, 255)
MUSTARD = (223, 164, 43, 255)
BOARD   = (61, 106, 90, 255)
WOOD    = (185, 138, 94, 255)
WALL    = (242, 234, 217, 255)
FLOOR   = (198, 170, 136, 255)

# 黒板の位置（構図テンプレートの数値）
BOARD_BOX = (int(W * .055), int(H * .105), int(W * .96), int(H * .625))
# 文字を置ける範囲（キャラの頭が来る左下を避ける）
TEXT_BOX  = (BOARD_BOX[0] + 46, BOARD_BOX[1] + 54, BOARD_BOX[2] - 46, BOARD_BOX[3] - 40)


def find_font():
    cands = [
        '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
        '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf',
        '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc',
        '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc',
    ]
    for p in cands:
        if os.path.exists(p):
            return p
    raise SystemExit('日本語フォントが見つかりません。Colabなら:\n'
                     '  !apt-get -qq install fonts-ipafont-gothic')

FONT_PATH = find_font()
_font_cache = {}

def font(size):
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(FONT_PATH, size)
    return _font_cache[size]

_img_cache = {}

def load(name):
    if name not in _img_cache:
        p = os.path.join(ASSETS, name)
        _img_cache[name] = Image.open(p).convert('RGBA') if os.path.exists(p) else None
    return _img_cache[name]


# ---------------------------------------------------------------- 台本

SCRIPT = [
    dict(end=3.5,  face='surprise', items=[
        dict(t=0.4, text='電子レンジは\n何を温めてる？', size=84)]),

    dict(end=9.5,  face='explain', items=[
        dict(t=3.9, text='食べ物じゃない', size=68),
        dict(t=6.6, text='水', size=190, color=MUSTARD)]),

    dict(end=20.0, face='serious', pointer=17.8, items=[
        dict(t=9.9,  fig='01_water_molecule.png', scale=.52, spin=1.1),
        dict(t=17.8, text='1秒に24億回', size=104, color=MUSTARD)]),

    dict(end=28.0, face='explain', pointer=23.6, items=[
        dict(t=20.4, fig='02_collision.png', scale=.86),
        dict(t=23.6, text='ぶつかる　→　熱', size=72, color=MUSTARD)]),

    dict(end=35.5, face='explain', items=[
        dict(t=28.4, text='お皿は温まらない', size=80)]),

    dict(end=46.0, face='proud', pointer=38.4, items=[
        dict(t=36.0, text='温めてない', size=68),
        dict(t=38.4, text='水を暴れさせてる', size=84, color=MUSTARD)]),
]

FACE_FILES = {
    'surprise': 'char_surprise.png',
    'explain':  'char_explain.png',
    'serious':  'char_serious.png',
    'proud':    'char_proud.png',
    'blink':    'char_blink.png',
}

BLINKS = [2.1, 5.4, 8.0, 11.6, 15.1, 18.3, 22.0, 25.4, 29.9, 33.2, 37.4, 41.0, 44.3]
BLINK_LEN = 0.10
DURATION = SCRIPT[-1]['end']


def cut_at(t):
    s = 0.0
    for i, c in enumerate(SCRIPT):
        if t < c['end']:
            return i, c, s
        s = c['end']
    return len(SCRIPT) - 1, SCRIPT[-1], s


# ---------------------------------------------------------------- 背景

def background():
    bg = Image.new('RGBA', (W, H), WALL)
    d = ImageDraw.Draw(bg)
    d.rectangle([0, int(H * .80), W, H], fill=FLOOR)
    d.rounded_rectangle([BOARD_BOX[0] - 16, BOARD_BOX[1] - 16,
                         BOARD_BOX[2] + 16, BOARD_BOX[3] + 16], 8, fill=WOOD)
    d.rectangle(list(BOARD_BOX), fill=BOARD)
    # 黒板のわずかなムラ
    v = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dv = ImageDraw.Draw(v)
    for i in range(9):
        a = 7 - i
        dv.rectangle([BOARD_BOX[0] + i * 5, BOARD_BOX[1] + i * 5,
                      BOARD_BOX[2] - i * 5, BOARD_BOX[3] - i * 5],
                     outline=(0, 0, 0, max(a, 0)))
    return Image.alpha_composite(bg, v)

BG = None


# ---------------------------------------------------------------- 黒板の中身

def wipe(t0, t, dur=0.34):
    """0→1。チョークで左から書かれる進捗。"""
    if t < t0:
        return 0.0
    return min(1.0, (t - t0) / dur)


def draw_board(canvas, cut, t):
    # 中身のかたまりを黒板の上寄り中央に置く（下はキャラの頭が来るので少し上へ）
    total = sum(slot_height(it) for it in cut['items'])
    avail = TEXT_BOX[3] - TEXT_BOX[1]
    y = TEXT_BOX[1] + max(0, int((avail - total) * 0.34))
    for it in cut['items']:
        p = wipe(it['t'], t)
        if p <= 0:
            # まだ出ていない要素も、次の要素の位置を狂わせないため高さだけ確保
            y += slot_height(it)
            continue

        if 'fig' in it:
            img = load(it['fig'])
            if img is None:
                y += slot_height(it)
                continue
            tw = int((TEXT_BOX[2] - TEXT_BOX[0]) * it['scale'])
            th = int(img.height * tw / img.width)
            f = img.resize((tw, th), Image.LANCZOS)
            if it.get('spin'):
                ang = -(t - it['t']) / it['spin'] * 360.0
                f = f.rotate(ang, resample=Image.BICUBIC, expand=False)
            if p < 1:
                f = fade(f, p)
            cx = (TEXT_BOX[0] + TEXT_BOX[2]) // 2 - tw // 2
            canvas.alpha_composite(f, (cx, y))
            y += th + 26
        else:
            col = it.get('color', CHALK)
            fnt = font(it['size'])
            lines = it['text'].split('\n')
            layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            dl = ImageDraw.Draw(layer)
            yy = y
            widest = 0
            for ln in lines:
                dl.text((TEXT_BOX[0], yy), ln, font=fnt, fill=col)
                widest = max(widest, int(dl.textlength(ln, font=fnt)))
                yy += int(it['size'] * 1.34)
            if p < 1:
                # 左から右へ現れる
                cut_x = TEXT_BOX[0] + int(widest * p) + 6
                m = Image.new('L', (W, H), 0)
                ImageDraw.Draw(m).rectangle([0, 0, cut_x, H], fill=255)
                layer.putalpha(Image.composite(layer.getchannel('A'),
                                               Image.new('L', (W, H), 0), m))
            canvas.alpha_composite(layer)
            y = yy + 14


def slot_height(it):
    if 'fig' in it:
        img = load(it['fig'])
        if img is None:
            return 0
        tw = int((TEXT_BOX[2] - TEXT_BOX[0]) * it['scale'])
        return int(img.height * tw / img.width) + 26
    return int(it['size'] * 1.34) * len(it['text'].split('\n')) + 14


def fade(img, a):
    al = img.getchannel('A').point(lambda v: int(v * a))
    o = img.copy()
    o.putalpha(al)
    return o


# ---------------------------------------------------------------- キャラ

CHAR_W_RATIO = 0.60      # 画面幅に対するキャラの幅
CHAR_CX      = 0.30      # キャラ中心の横位置
CHAR_FOOT    = 0.985     # 足元の位置（画面高に対する比）
HAND         = (0.470, 0.560)   # 手の位置（画面比）


def char_image(cut, t):
    """まばたき中なら閉じ目に差し替える。"""
    for b in BLINKS:
        if b <= t < b + BLINK_LEN:
            im = load(FACE_FILES['blink'])
            if im is not None:
                return im
    return load(FACE_FILES[cut['face']])


def draw_char(canvas, cut, cut_start, t):
    img = char_image(cut, t)
    if img is None:
        img = placeholder()

    # 呼吸
    br = 1.0 + 0.008 * (0.5 - 0.5 * math.cos(2 * math.pi * (t % 2.6) / 2.6))
    # カット頭の立ち上がり
    e = min(1.0, max(0.0, (t - cut_start) / 0.15))
    pop = 1.0 + 0.010 * (1 - e)
    lift = int(7 * (1 - e))

    s = br * pop
    tw = int(W * CHAR_W_RATIO * s)
    th = int(img.height * tw / img.width)
    im = img.resize((tw, th), Image.LANCZOS)

    x = int(W * CHAR_CX) - tw // 2
    y = int(H * CHAR_FOOT) - th + lift
    canvas.alpha_composite(im, (x, y))


def placeholder():
    """キャラ画像が無いときの代役。"""
    w, h = 700, 1000
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    g = (195, 188, 168, 255)
    d.ellipse([130, 0, 570, 430], fill=g)
    d.rounded_rectangle([170, 380, 530, 1000], 150, fill=g)
    f = font(46)
    d.text((350, 200), 'カワウソ', font=f, fill=(120, 114, 96, 255), anchor='mm')
    d.text((350, 260), '（差し替え）', font=font(30), fill=(120, 114, 96, 255), anchor='mm')
    return im


# ---------------------------------------------------------------- 指し棒

STICK_LEN = int(H * 0.20)
STICK_TH  = 11


def draw_pointer(canvas, cut, t):
    hx, hy = int(W * HAND[0]), int(H * HAND[1])
    ang = -52.0                        # 通常の角度（右上を指す）
    tap = cut.get('pointer')
    if tap is not None:
        d = t - tap
        if -0.10 <= d < 0.0:
            ang += 6.0 * (d + 0.10) / 0.10
        elif 0.0 <= d < 0.07:
            ang += 6.0
        elif 0.07 <= d < 0.20:
            ang += 6.0 * (1 - (d - 0.07) / 0.13)

    r = math.radians(ang)
    tipx, tipy = hx + STICK_LEN * math.cos(r), hy + STICK_LEN * math.sin(r)
    # 手を軸に、反対側にも同じ長さ（キャラの体で隠れる部分）
    bx, by = hx - STICK_LEN * .55 * math.cos(r), hy - STICK_LEN * .55 * math.sin(r)
    d = ImageDraw.Draw(canvas)
    d.line([bx, by, tipx, tipy], fill=CHALK, width=STICK_TH)
    d.ellipse([tipx - 7, tipy - 7, tipx + 7, tipy + 7], fill=CHALK)


# ---------------------------------------------------------------- 1フレーム

def render_frame(t):
    global BG
    if BG is None:
        BG = background()
    canvas = BG.copy()
    ci, cut, cs = cut_at(t)
    draw_board(canvas, cut, t)
    draw_pointer(canvas, cut, t)      # 棒はキャラの下
    draw_char(canvas, cut, cs, t)
    return canvas.convert('RGB')


# ---------------------------------------------------------------- 実行

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', nargs='*', type=float)
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    if a.probe:
        for t in a.probe:
            p = os.path.join(OUT, 'probe_%05.1f.png' % t)
            render_frame(t).save(p)
            print(p)
        return

    if a.all:
        n = int(DURATION * FPS)
        for i in range(n):
            render_frame(i / FPS).save(os.path.join(OUT, '%05d.png' % i))
            if i % 60 == 0:
                print('  %d / %d' % (i, n), flush=True)
        print('完了: %d フレーム' % n)
        print('次: ffmpeg -r %d -i frames/%%05d.png -i narration.wav '
              '-c:v libx264 -pix_fmt yuv420p -shortest ep01.mp4' % FPS)
        return

    ap.print_help()


if __name__ == '__main__':
    main()
