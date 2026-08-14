"""
カワウソ黒板解説チャンネル ／ フレームレンダラー v2
=====================================================
参考動画の実測（カット長 1.3〜1.7秒／画面が常に動いている）に合わせて、
「ショット」を細かく並べる方式に変更した。

キャラ画像は5枚のままで、ショット種を4つ使って絵の点数を増やす:
  wide  … 黒板＋キャラの通常構図
  face  … キャラの顔アップ（同じ画像をクロップするだけ。素材追加ゼロ）
  board … 黒板だけに寄る（図を大きく見せる）
  title … 黒背景＋白文字のインタータイトル（章の区切り）

自動でつくもの:
  - 全ショットにズーム／パン（方向は自動で交互に振る。静止するショットは作らない）
  - 呼吸、まばたき（不等間隔・0.1秒）
  - 黒板の文字がチョークで書かれるワイプ
  - 図の回転
  - 指し棒のタップ（手を軸に回転）
  - 画面下のテロップ（黒フチ付き・常時）。{ } で囲んだ語だけ色が変わる
  - 左上の固定ロゴ

使い方:
  python3 render.py --probe 0.5 3.0 12.0    指定秒だけ書き出して確認
  python3 render.py --sheet                 全ショットの頭を並べた確認シート
  python3 render.py --all                   全フレーム書き出し
"""
import os, math, argparse, colorsys
from PIL import Image, ImageDraw, ImageFont

HERE   = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')
OUT    = os.path.join(HERE, 'frames')

W, H, FPS = 1080, 1920, 30

CHALK   = (239, 233, 218, 255)
MUSTARD = (223, 164, 43, 255)
CRIMSON = (206, 78, 55, 255)
BOARD   = (61, 106, 90, 255)
WOOD    = (185, 138, 94, 255)
WALL    = (242, 234, 217, 255)
FLOOR   = (198, 170, 136, 255)
WHITE   = (255, 255, 255, 255)
BLACK   = (16, 18, 16, 255)

BOARD_BOX = (int(W*.055), int(H*.105), int(W*.96), int(H*.625))
TEXT_BOX  = (BOARD_BOX[0]+46, BOARD_BOX[1]+54, BOARD_BOX[2]-46, BOARD_BOX[3]-40)

CHAR_W_RATIO, CHAR_CX, CHAR_FOOT = 0.60, 0.30, 0.985
HAND = (0.470, 0.560)

TELOP_Y     = 0.700      # テロップの上端（下から20%のUI帯を避ける）
TELOP_SIZE  = 84
LOGO        = True


# ------------------------------------------------------------- フォント

def find_font():
    for p in ('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
              '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf',
              '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc'):
        if os.path.exists(p):
            return p
    raise SystemExit('日本語フォントがありません。Colabなら:\n'
                     '  !apt-get -qq install fonts-ipafont-gothic')

FONT_PATH = find_font()
_fc = {}
def font(s):
    if s not in _fc: _fc[s] = ImageFont.truetype(FONT_PATH, s)
    return _fc[s]

_ic = {}
def load(n):
    if n not in _ic:
        p = os.path.join(ASSETS, n)
        _ic[n] = Image.open(p).convert('RGBA') if os.path.exists(p) else None
    return _ic[n]


# ------------------------------------------------------------- 台本
#
# 1ショット = 画面が変わる1単位。1.0〜2.2秒に収める。
#   kind  : wide / face / board / title
#   face  : surprise / explain / serious / proud
#   board : 黒板に出す行のリスト。dictで {text,size,color} も可
#   tele  : 画面下のテロップ。{ } で囲むと色が変わる
#   fig   : 黒板に置く図
#   tap   : True にすると指し棒で叩く
#   mark  : ('arrow', x, y) など補助記号
#   zoom  : 'in' / 'out' / 'left' / 'right' （省略時は自動で交互）

SHOTS = [
 # ---- フック 0.0〜3.4
 dict(dur=1.5, kind='wide',  face='surprise', board=['電子レンジは','{何を温めてる？}'],
      tele='電子レンジって、'),
 dict(dur=1.1, kind='face',  face='surprise', tele='{何を温めてる}と思う？'),
 dict(dur=0.8, kind='title', title='ほぼ全員\n間違えます'),

 # ---- 匂わせ 3.4〜9.4
 dict(dur=1.6, kind='wide',  face='explain', board=['正解は'], tele='正解は、'),
 dict(dur=1.5, kind='board', board=['{食べ物じゃない}'], tele='{食べ物じゃありません。}'),
 dict(dur=1.4, kind='face',  face='explain', tele='中に入っている、'),
 dict(dur=1.5, kind='board', board=[dict(text='水', size=300, color=MUSTARD)],
      tele='{水}です。', tap=True),

 # ---- 仕組み① 9.4〜20.0
 dict(dur=1.6, kind='wide',  face='serious', board=['電子レンジが','出しているのは'],
      tele='電子レンジが出しているのは、'),
 dict(dur=1.8, kind='board', board=[dict(text='マイクロ波', size=140, color=MUSTARD)],
      tele='{マイクロ波}という、'),
 dict(dur=1.5, kind='wide',  face='serious', board=['目に見えない','電波'],
      tele='目に見えない電波。'),
 dict(dur=2.0, kind='board', fig=('01_water_molecule.png', .58, 1.1),
      tele='これを浴びると、水の分子が'),
 dict(dur=1.9, kind='board', fig=('01_water_molecule.png', .40, 0.45),
      board=[dict(text='ぐるぐる回る', size=110)], tele='{猛烈に}回りはじめます。'),
 dict(dur=1.8, kind='wide',  face='serious',
      board=[dict(text='1秒に\n24億回', size=150, color=MUSTARD)],
      tele='一秒間に、{24億回}。', tap=True),

 # ---- 仕組み② 20.0〜28.2
 dict(dur=1.4, kind='face',  face='explain', tele='向きを変えるたびに、'),
 dict(dur=2.0, kind='board', fig=('02_collision.png', .92, None),
      tele='隣の分子と{ぶつかり合う。}'),
 dict(dur=1.6, kind='wide',  face='explain',
      board=[dict(text='ぶつかる → 熱', size=96, color=CRIMSON)],
      tele='そこで{熱}が生まれて、', tap=True),
 dict(dur=1.6, kind='board', board=['食べ物を','{内側から}温める'],
      tele='食べ物を内側から温めている。'),
 dict(dur=1.6, kind='face',  face='explain', tele='つまり、外から温めてない。'),

 # ---- 具体例 28.2〜35.8
 dict(dur=0.9, kind='title', title='ここで\n1つ気づく'),
 dict(dur=1.7, kind='wide',  face='explain', board=['じゃあ','{お皿}は？'],
      tele='じゃあ、{お皿}はどうなる？'),
 dict(dur=1.6, kind='board', board=[dict(text='温まらない', size=150, color=MUSTARD)],
      tele='水分がないので、{温まりません。}', tap=True),
 dict(dur=1.7, kind='face',  face='explain', tele='お皿が熱いのは、'),
 dict(dur=1.7, kind='wide',  face='explain', board=['食べ物から','熱が移っただけ'],
      tele='食べ物から{熱が移っただけ}なんです。'),

 # ---- オチ 35.8〜42.5
 dict(dur=1.3, kind='title', title='つまり'),
 dict(dur=1.7, kind='wide',  face='proud', board=['{温めてない}'],
      tele='電子レンジは、温めているんじゃない。'),
 dict(dur=2.2, kind='board', board=[dict(text='水を\n暴れさせてる', size=160, color=MUSTARD)],
      tele='{水を暴れさせている}だけなんです。', tap=True),
 dict(dur=1.5, kind='face',  face='proud', tele=''),

 # ---- 予告 42.5〜47.5
 dict(dur=2.4, kind='wide',  face='proud', board=['次は','{飛行機}'],
      tele='次は、飛行機がなんで飛ぶのか。'),
 dict(dur=2.6, kind='board', board=[dict(text='学校の説明は\n間違い', size=120, color=CRIMSON)],
      tele='学校で習ったあの説明、{実は間違いです。}'),
]

FACE_FILES = dict(surprise='char_surprise.png', explain='char_explain.png',
                  serious='char_serious.png', proud='char_proud.png',
                  blink='char_blink.png')

BLINKS = [1.9, 4.6, 7.2, 10.1, 13.4, 16.0, 19.2, 22.1, 25.0, 28.4,
          31.2, 34.1, 37.0, 40.2, 43.5, 46.1]
BLINK_LEN = 0.10

ZOOM_CYCLE = ('in', 'out', 'left', 'in', 'right', 'out')


def build():
    t = 0.0
    for i, s in enumerate(SHOTS):
        s['t'] = t
        s.setdefault('zoom', ZOOM_CYCLE[i % len(ZOOM_CYCLE)])
        t += s['dur']
    return t

DURATION = build()


def shot_at(t):
    for s in SHOTS:
        if s['t'] <= t < s['t'] + s['dur']:
            return s
    return SHOTS[-1]


# ------------------------------------------------------------- 文字

def parts(text):
    """'水を{暴れさせてる}' -> [('水を',False), ('暴れさせてる',True)]"""
    out, buf, hi = [], '', False
    for ch in text:
        if ch == '{':
            if buf: out.append((buf, hi)); buf = ''
            hi = True
        elif ch == '}':
            if buf: out.append((buf, hi)); buf = ''
            hi = False
        else:
            buf += ch
    if buf: out.append((buf, hi))
    return out


def rich(d, x, y, text, fnt, base, hi, stroke=0, scol=BLACK, anchor_c=False):
    segs = parts(text)
    total = sum(d.textlength(s, font=fnt) for s, _ in segs)
    cx = x - total / 2 if anchor_c else x
    for s, is_hi in segs:
        d.text((cx, y), s, font=fnt, fill=(hi if is_hi else base),
               stroke_width=stroke, stroke_fill=scol)
        cx += d.textlength(s, font=fnt)
    return total


# ------------------------------------------------------------- 背景

_bg = {}

def bg_wide():
    if 'wide' in _bg: return _bg['wide']
    im = Image.new('RGBA', (W, H), WALL)
    d = ImageDraw.Draw(im)
    d.rectangle([0, int(H*.80), W, H], fill=FLOOR)
    d.rounded_rectangle([BOARD_BOX[0]-16, BOARD_BOX[1]-16,
                         BOARD_BOX[2]+16, BOARD_BOX[3]+16], 8, fill=WOOD)
    d.rectangle(list(BOARD_BOX), fill=BOARD)
    _bg['wide'] = im
    return im


def bg_board():
    """黒板だけに寄った画面。"""
    if 'board' in _bg: return _bg['board']
    im = Image.new('RGBA', (W, H), BOARD)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 26], fill=WOOD)
    d.rectangle([0, H-26, W, H], fill=WOOD)
    _bg['board'] = im
    return im


# ------------------------------------------------------------- 黒板の中身

def wipe(t0, t, dur=0.28):
    return 0.0 if t < t0 else min(1.0, (t - t0) / dur)


def board_area(kind):
    if kind == 'board':
        return (int(W*.09), int(H*.20), int(W*.91), int(H*.66))
    return TEXT_BOX


def draw_content(canvas, s, t, kind):
    a = board_area(kind)
    local = t - s['t']
    rows = []

    if s.get('fig'):
        name, scale, spin = s['fig']
        img = load(name)
        if img is not None:
            tw = int((a[2]-a[0]) * scale)
            th = int(img.height * tw / img.width)
            rows.append(('fig', img, tw, th, spin))

    for row in s.get('board', []):
        it = row if isinstance(row, dict) else dict(text=row)
        it.setdefault('size', 132 if kind == 'board' else 88)
        rows.append(('txt', it))

    total = 0
    for r in rows:
        total += (r[3] + 30) if r[0] == 'fig' else \
                 int(r[1]['size'] * 1.32) * len(r[1]['text'].split('\n')) + 18
    y = a[1] + max(0, int(((a[3]-a[1]) - total) * (0.5 if kind == 'board' else 0.30)))

    d = ImageDraw.Draw(canvas)
    for r in rows:
        p = wipe(0.10, local)
        if r[0] == 'fig':
            _, img, tw, th, spin = r
            f = img.resize((tw, th), Image.LANCZOS)
            if spin:
                f = f.rotate(-local / spin * 360.0, resample=Image.BICUBIC)
            if p < 1:
                al = f.getchannel('A').point(lambda v: int(v * p)); f.putalpha(al)
            canvas.alpha_composite(f, ((a[0]+a[2])//2 - tw//2, y))
            y += th + 30
        else:
            it = r[1]
            fnt = font(it['size'])
            col = it.get('color', CHALK)
            ctr = (kind == 'board')
            for ln in it['text'].split('\n'):
                lay = Image.new('RGBA', (W, H), (0,0,0,0))
                dl = ImageDraw.Draw(lay)
                x0 = (a[0]+a[2])//2 if ctr else a[0]
                wid = rich(dl, x0, y, ln, fnt, col, MUSTARD, anchor_c=ctr)
                if p < 1:
                    left = x0 - wid/2 if ctr else a[0]
                    m = Image.new('L', (W, H), 0)
                    ImageDraw.Draw(m).rectangle([0, 0, left + int(wid*p) + 8, H], fill=255)
                    lay.putalpha(Image.composite(lay.getchannel('A'),
                                                 Image.new('L', (W, H), 0), m))
                canvas.alpha_composite(lay)
                y += int(it['size'] * 1.32)
            y += 18


# ------------------------------------------------------------- キャラ

def placeholder():
    im = Image.new('RGBA', (700, 1000), (0,0,0,0))
    d = ImageDraw.Draw(im); g = (195, 188, 168, 255)
    d.ellipse([130, 0, 570, 430], fill=g)
    d.rounded_rectangle([170, 380, 530, 1000], 150, fill=g)
    d.text((350, 190), 'カワウソ', font=font(44), fill=(120,114,96,255), anchor='mm')
    d.text((350, 250), '（差し替え）', font=font(28), fill=(120,114,96,255), anchor='mm')
    return im


def char_img(s, t):
    for b in BLINKS:
        if b <= t < b + BLINK_LEN:
            im = load(FACE_FILES['blink'])
            if im is not None: return im
    return load(FACE_FILES.get(s.get('face', 'explain'))) or placeholder()


def draw_char(canvas, s, t):
    img = char_img(s, t)
    local = t - s['t']
    br  = 1.0 + 0.008 * (0.5 - 0.5*math.cos(2*math.pi*(t % 2.6)/2.6))
    e   = min(1.0, local / 0.15)
    sc  = br * (1.0 + 0.010*(1-e))
    tw  = int(W * CHAR_W_RATIO * sc)
    th  = int(img.height * tw / img.width)
    im  = img.resize((tw, th), Image.LANCZOS)
    canvas.alpha_composite(im, (int(W*CHAR_CX) - tw//2,
                                int(H*CHAR_FOOT) - th + int(7*(1-e))))


def draw_pointer(canvas, s, t):
    hx, hy = int(W*HAND[0]), int(H*HAND[1])
    ang = -52.0
    if s.get('tap'):
        d0 = (t - s['t']) - 0.34
        if -0.10 <= d0 < 0:   ang += 6.0 * (d0+0.10)/0.10
        elif 0 <= d0 < 0.07:  ang += 6.0
        elif 0.07 <= d0 < .2: ang += 6.0 * (1-(d0-0.07)/0.13)
    r = math.radians(ang)
    L = int(H*0.20)
    d = ImageDraw.Draw(canvas)
    d.line([hx - L*.55*math.cos(r), hy - L*.55*math.sin(r),
            hx + L*math.cos(r),     hy + L*math.sin(r)], fill=CHALK, width=11)


def face_shot(s, t):
    """キャラの顔だけを全画面に。素材を増やさずカットを増やす主力。"""
    img = char_img(s, t)
    src = img.crop((0, 0, img.width, int(img.height*0.46)))
    k = max(W/src.width, H*0.78/src.height) * 1.06
    src = src.resize((int(src.width*k), int(src.height*k)), Image.LANCZOS)
    im = Image.new('RGBA', (W, H), WALL)
    ImageDraw.Draw(im).rectangle([0, 0, W, H], fill=BOARD)
    im.alpha_composite(src, (W//2 - src.width//2, int(H*0.10)))
    return im


def title_shot(s, t):
    im = Image.new('RGBA', (W, H), BLACK)
    d = ImageDraw.Draw(im)
    local = t - s['t']
    lines = s['title'].split('\n')
    fnt = font(126)
    tot = len(lines) * int(126*1.36)
    y = H//2 - tot//2
    for i, ln in enumerate(lines):
        p = wipe(0.06 + i*0.10, local, 0.16)
        if p <= 0:
            y += int(126*1.36); continue
        lay = Image.new('RGBA', (W, H), (0,0,0,0))
        dl = ImageDraw.Draw(lay)
        rich(dl, W//2, y, ln, fnt, WHITE, MUSTARD, anchor_c=True)
        if p < 1:
            al = lay.getchannel('A').point(lambda v: int(v*p)); lay.putalpha(al)
        im.alpha_composite(lay)
        y += int(126*1.36)
    return im


# ------------------------------------------------------------- テロップ・ロゴ

def draw_telop(canvas, s):
    txt = s.get('tele', '')
    if not txt: return
    fnt = font(TELOP_SIZE)
    d = ImageDraw.Draw(canvas)
    # 長い行は2行に折る
    segs = parts(txt)
    plain = ''.join(x for x, _ in segs)
    if d.textlength(plain, font=fnt) > W*0.88:
        half = len(plain)//2
        cut = plain.rfind('、', 0, half+6)
        cut = cut+1 if cut > 3 else half
        rows = [plain[:cut], plain[cut:]]
        hi_set = set(x for x, h in segs if h)
        y = int(H*TELOP_Y)
        for rw in rows:
            lay = Image.new('RGBA', (W, H), (0,0,0,0))
            dl = ImageDraw.Draw(lay)
            marked = rw
            for h in hi_set:
                if h in marked: marked = marked.replace(h, '{'+h+'}')
            rich(dl, W//2, y, marked, fnt, WHITE, MUSTARD, 7, BLACK, True)
            canvas.alpha_composite(lay)
            y += int(TELOP_SIZE*1.34)
    else:
        lay = Image.new('RGBA', (W, H), (0,0,0,0))
        dl = ImageDraw.Draw(lay)
        rich(dl, W//2, int(H*TELOP_Y), txt, fnt, WHITE, MUSTARD, 7, BLACK, True)
        canvas.alpha_composite(lay)


def draw_logo(canvas, t):
    if not LOGO: return
    r, cx, cy = 52, 96, int(H*0.045)
    d = ImageDraw.Draw(canvas)
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255,255,255,205))
    face = load(FACE_FILES['explain'])
    if face is not None:
        crop = face.crop((int(face.width*.22), 0, int(face.width*.78), int(face.height*.30)))
        k = (2*r)/max(crop.width, 1)
        crop = crop.resize((int(crop.width*k), int(crop.height*k)), Image.LANCZOS)
        m = Image.new('L', (2*r, 2*r), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 2*r, 2*r], fill=255)
        tile = Image.new('RGBA', (2*r, 2*r), (0,0,0,0))
        tile.alpha_composite(crop, (r - crop.width//2, 4))
        tile.putalpha(Image.composite(tile.getchannel('A'), Image.new('L',(2*r,2*r),0), m))
        canvas.alpha_composite(tile, (cx-r, cy-r))
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=BOARD, width=5)


# ------------------------------------------------------------- ズーム

def apply_zoom(im, s, t):
    p = min(1.0, max(0.0, (t - s['t']) / s['dur']))
    z = s['zoom']
    Z = 1.075
    if z == 'in':    k, ox, oy = 1 + (Z-1)*p,      0.5, 0.5
    elif z == 'out': k, ox, oy = Z - (Z-1)*p,      0.5, 0.5
    elif z == 'left':  k, ox, oy = Z, 0.34 + 0.30*p, 0.5
    else:              k, ox, oy = Z, 0.66 - 0.30*p, 0.5
    bw, bh = int(W*k), int(H*k)
    big = im.resize((bw, bh), Image.LANCZOS)
    x = int((bw - W) * ox); y = int((bh - H) * oy)
    return big.crop((x, y, x+W, y+H))


# ------------------------------------------------------------- 1フレーム

def render_frame(t):
    s = shot_at(t)
    k = s['kind']

    if k == 'title':
        frame = title_shot(s, t)
        return apply_zoom(frame, s, t).convert('RGB')

    if k == 'face':
        frame = face_shot(s, t)
        frame = apply_zoom(frame, s, t)
        draw_telop(frame, s); draw_logo(frame, t)
        return frame.convert('RGB')

    if k == 'board':
        frame = bg_board().copy()
        draw_content(frame, s, t, 'board')
        frame = apply_zoom(frame, s, t)
        draw_telop(frame, s); draw_logo(frame, t)
        return frame.convert('RGB')

    frame = bg_wide().copy()
    draw_content(frame, s, t, 'wide')
    draw_pointer(frame, s, t)
    draw_char(frame, s, t)
    frame = apply_zoom(frame, s, t)
    draw_telop(frame, s); draw_logo(frame, t)
    return frame.convert('RGB')


# ------------------------------------------------------------- 実行

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', nargs='*', type=float)
    ap.add_argument('--sheet', action='store_true')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    print('尺 %.1f 秒 / %d ショット / 平均 %.2f 秒'
          % (DURATION, len(SHOTS), DURATION/len(SHOTS)))

    if a.sheet:
        cols, rows = 6, math.ceil(len(SHOTS)/6)
        tw, th = 180, 320
        sheet = Image.new('RGB', (cols*tw, rows*th), (24,26,24))
        for i, s in enumerate(SHOTS):
            im = render_frame(s['t'] + s['dur']*0.6).resize((tw-4, th-4), Image.LANCZOS)
            sheet.paste(im, ((i % cols)*tw+2, (i//cols)*th+2))
        p = os.path.join(OUT, 'shotsheet.png'); sheet.save(p); print(p)
        return

    if a.probe:
        for t in a.probe:
            p = os.path.join(OUT, 'probe_%05.1f.png' % t)
            render_frame(t).save(p); print(p)
        return

    if a.all:
        n = int(DURATION*FPS)
        for i in range(n):
            render_frame(i/FPS).save(os.path.join(OUT, '%05d.png' % i))
            if i % 150 == 0: print('  %d / %d' % (i, n), flush=True)
        print('完了 %d フレーム' % n)
        return

    ap.print_help()


if __name__ == '__main__':
    main()
