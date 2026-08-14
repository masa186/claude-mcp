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

CHAR_W_RATIO, CHAR_CX, CHAR_FOOT = 0.50, 0.235, 0.985
HAND = (0.472, 0.774)   # char_explain の上げた手の実測値

TELOP_Y     = 0.725      # テロップの上端（下から20%のUI帯を避ける）
TELOP_SIZE  = 84
TELOP_STROKE = 5         # 黒フチ。太すぎるとテンプレ感が出る
STAGGER     = 0.55       # 黒板の要素を出す間隔（小さい変化のリズム）
POP_AT      = 0.38       # テロップの強調語が跳ねる時刻（ショット頭から）
POP_LEN     = 0.16
LOGO        = True


# ------------------------------------------------------------- フォント

def pick(*cands):
    for p in cands:
        if os.path.exists(p):
            return p
    return None

# テロップは極太（参考動画はテロップが主役）、黒板は太字
FONT_TELOP = pick('/usr/share/fonts/opentype/mplus/Mplus1-Black.otf',
                  '/usr/share/fonts/opentype/mplus/Mplus1-ExtraBold.otf',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
                  '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf')
FONT_BOARD = pick('/usr/share/fonts/opentype/mplus/Mplus1-Bold.otf',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
                  '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf')
if not FONT_TELOP:
    raise SystemExit('日本語フォントがありません。Colabなら:\n'
                     '  !apt-get -qq install fonts-mplus')

_fc = {}
def font(size, path=None):
    key = (size, path or FONT_BOARD)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(key[1], size)
    return _fc[key]

def tfont(size):
    return font(size, FONT_TELOP)

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
 # ---- フック
 dict(sec='hook', dur=1.5, kind='wide', face='surprise',
      board=['電子レンジは','{何を温めてる？}'], tele='電子レンジって、'),
 dict(dur=1.1, kind='face',  face='surprise', tele='{何を温めてる}と思う？'),
 dict(dur=0.8, kind='title', title='ほぼ全員\n間違えます'),

 # ---- 匂わせ
 dict(sec='setup', dur=1.5, kind='wide', face='explain', board=['正解は'], tele='正解は、'),
 dict(dur=1.5, kind='board', board=['{食べ物じゃない}'], tele='{食べ物じゃありません。}'),
 dict(dur=1.3, kind='face',  face='explain', tele='中に入っている、'),
 dict(dur=1.5, kind='board', board=[dict(text='水', size=300, color=MUSTARD)],
      tele='{水}です。', tap=True),

 # ---- 仕組み①
 dict(sec='how', dur=1.5, kind='wide', face='point',
      board=['電子レンジが','出しているのは'], tele='ここ見て。電子レンジが出してるのは、'),
 dict(dur=1.6, kind='board', fig=('04_microwave.png', 1.00, 'pulse:1.0'),
      tele='奥から{電波}を出して、'),
 dict(dur=1.6, kind='board', board=[dict(text='マイクロ波', size=140, color=MUSTARD)],
      tele='{マイクロ波}といいます。'),
 dict(dur=1.5, kind='board', fig=('05_wave.png', .92, 'scroll:2.4'),
      board=[dict(text='目に見えない', size=88)], tele='目に見えない波です。'),
 dict(dur=1.8, kind='board', fig=('01_water_molecule.png', .52, 1.1),
      tele='これを浴びると、水の分子が'),
 dict(dur=1.7, kind='board', fig=('06_flip.png', 1.00, 'alt:0.42'),
      tele='{ぐるん、ぐるん}と向きを変える。'),
 dict(dur=2.0, kind='board',
      board=[dict(count=2400000000, done='24億回', label='24億回',
                  count_in=1.1, size=132, color=MUSTARD)],
      tele='その回数、一秒間に{24億回}。'),
 dict(dur=1.2, kind='face',  face='surprise', tele='{……多すぎる。}'),

 # ---- 仕組み②
 dict(dur=1.3, kind='face',  face='explain', tele='向きを変えるたびに、'),
 dict(dur=1.9, kind='board', fig=('02_collision.png', .92, 'pulse:0.55'),
      tele='隣の分子と{ぶつかり合う。}'),
 dict(dur=1.5, kind='wide',  face='explain',
      board=[dict(text='ぶつかる → 熱', size=96, color=CRIMSON)],
      tele='そこで{熱}が生まれて、', tap=True),
 dict(dur=1.5, kind='board', board=['食べ物を','{内側から}温める'],
      tele='食べ物を内側から温めている。'),
 dict(dur=1.4, kind='face',  face='explain', tele='つまり、外から温めてない。'),

 # ---- 具体例
 dict(sec='example', dur=0.9, kind='title', title='ここで\n1つ気づく'),
 dict(dur=1.6, kind='wide',  face='point', board=['じゃあ','{お皿}は？'],
      tele='じゃあ、{お皿}はどうなる？'),
 dict(dur=1.7, kind='board', fig=('07_plate_food.png', 1.00, 'pulse:1.3'),
      tele='お皿には{水がない。}'),
 dict(dur=1.5, kind='board', board=[dict(text='温まらない', size=150, color=MUSTARD)],
      tele='だから{温まりません。}', tap=True),
 dict(dur=1.4, kind='face',  face='explain', tele='お皿が熱いのは、'),
 dict(dur=1.6, kind='board', fig=('08_heat_move.png', 1.00, 'pulse:0.85'),
      tele='食べ物から{熱が移っただけ}なんです。'),

 # ---- オチ
 dict(sec='punch', dur=1.2, kind='title', title='つまり'),
 dict(dur=1.6, kind='wide',  face='arms', board=['{温めてない}'],
      tele='電子レンジは、温めているんじゃない。'),
 dict(dur=2.1, kind='board', board=[dict(text='水を\n暴れさせてる', size=160, color=MUSTARD)],
      tele='{水を暴れさせている}だけなんです。', tap=True),
 dict(dur=1.4, kind='face',  face='proud', tele=''),

 # ---- 予告
 dict(sec='next', dur=2.1, kind='wide', face='proud', board=['次は','{飛行機}'],
      tele='次は、飛行機がなんで飛ぶのか。'),
 dict(dur=2.3, kind='board', board=[dict(text='学校の説明は\n間違い', size=120, color=CRIMSON)],
      tele='学校で習ったあの説明、{実は間違いです。}'),
]


def section_times():
    """BGMの音量を切り替える境目を SHOTS から拾う（秒を手で書かないため）。"""
    out = {}
    for s in SHOTS:
        if s.get('sec') and s['sec'] not in out:
            out[s['sec']] = s['t']
    return out


FACE_FILES = dict(surprise='char_surprise.png', explain='char_explain.png',
                  serious='char_serious.png', proud='char_proud.png',
                  point='char_point.png', arms='char_arms.png')

# 口を開けた差分がある表情は、喋っている間だけ口をパクパクさせる。
MOUTH_FILES = dict(point='char_point_open.png')
MOUTH_HZ = 6.5

# まばたき画像は「その表情と同じポーズ」でないと、0.1秒だけ姿勢が跳ねる。
# 用意できている表情にだけ差し込む。増やしたいときはここにファイル名を足す。
BLINK_FILES = dict(explain='char_blink.png')

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


def rich(d, x, y, text, fnt, base, hi, stroke=0, scol=BLACK, anchor_c=False,
         hifnt=None):
    """{ } で囲んだ語だけ色を変える。hifnt を渡すと、その語だけ別サイズで描く。"""
    segs = parts(text)
    hf = hifnt or fnt
    total = sum(d.textlength(s, font=(hf if h else fnt)) for s, h in segs)
    cx = x - total / 2 if anchor_c else x
    for s, is_hi in segs:
        f = hf if is_hi else fnt
        dy = -(hf.size - fnt.size) * 0.42 if (is_hi and hifnt is not None) else 0
        d.text((cx, y + dy), s, font=f, fill=(hi if is_hi else base),
               stroke_width=stroke, stroke_fill=scol)
        cx += d.textlength(s, font=f)
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
        if 'count' in it:
            it = dict(it)
            it['text'] = count_text(it, local)
        it.setdefault('size', 132 if kind == 'board' else 88)
        rows.append(('txt', it))

    total = 0
    for r in rows:
        total += (r[3] + 30) if r[0] == 'fig' else \
                 int(r[1]['size'] * 1.32) * len(r[1]['text'].split('\n')) + 18
    y = a[1] + max(0, int(((a[3]-a[1]) - total) * (0.5 if kind == 'board' else 0.30)))

    d = ImageDraw.Draw(canvas)
    for ri, r in enumerate(rows):
        # 1つずつ間を置いて出す。これが「小さい変化」の本体。
        p = wipe(0.10 + ri * STAGGER, local)
        if r[0] == 'fig':
            _, img, tw, th, anim = r
            f = img.resize((tw, th), Image.LANCZOS)
            f = animate_fig(f, anim, local)
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


# ------------------------------------------------------------- スクリーン

CLIP_DIR = os.path.join(HERE, 'clips')
SCREEN_W = 0.86               # 画面幅に対するスクリーンの横幅
SCREEN_TOP = 0.155            # スクリーンの上端（画面高に対する比）
ROLL = 0.42                   # 降りてくる時間（秒）

_clip_cache = {}


def clip_frames(name):
    if name not in _clip_cache:
        d = os.path.join(CLIP_DIR, name)
        fs = sorted(os.listdir(d)) if os.path.isdir(d) else []
        _clip_cache[name] = [os.path.join(d, f) for f in fs]
    return _clip_cache[name]


_frame_cache = {}


def clip_frame(name, i):
    fs = clip_frames(name)
    if not fs:
        return None
    key = (name, i % len(fs))
    if key not in _frame_cache:
        if len(_frame_cache) > 120:
            _frame_cache.clear()
        _frame_cache[key] = Image.open(fs[key[1]]).convert('RGBA')
    return _frame_cache[key]


def draw_screen(canvas, s, t):
    """黒板の前にスクリーンが降りてきて、そこに映像が流れる。
    黒板に実写を直接貼ると浮くが、スクリーンなら教室として自然になる。"""
    local = t - s['t']
    sw = int(W * SCREEN_W)
    sh = int(sw * 9 / 16)
    x0 = W // 2 - sw // 2
    y0 = int(H * SCREEN_TOP)

    roll = min(1.0, local / ROLL) if s.get('roll', True) else 1.0
    roll = ease_out(roll)
    vis = max(2, int(sh * roll))

    d = ImageDraw.Draw(canvas)
    # 巻き取り機（上のバー）
    d.rectangle([x0 - 14, y0 - 20, x0 + sw + 14, y0 - 2], fill=(70, 62, 52, 255))

    img = clip_frame(s['clip'], int(local * FPS))
    panel = Image.new('RGBA', (sw, sh), (236, 234, 228, 255))
    if img is not None:
        f = img.resize((sw, sh), Image.LANCZOS)
        # ゆっくり寄る
        k = 1.0 + 0.06 * min(1.0, local / max(s['dur'], .01))
        bw, bh = int(sw * k), int(sh * k)
        f = f.resize((bw, bh), Image.LANCZOS).crop(
            ((bw - sw) // 2, (bh - sh) // 2, (bw - sw) // 2 + sw, (bh - sh) // 2 + sh))
        panel.alpha_composite(f)
    canvas.alpha_composite(panel.crop((0, 0, sw, vis)), (x0, y0))
    # スクリーンの下端の棒
    d.rectangle([x0 - 6, y0 + vis, x0 + sw + 6, y0 + vis + 9], fill=(96, 86, 72, 255))


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
    face = s.get('face', 'explain')
    # 喋っている間（テロップが出ている間）だけ口を動かす
    mf = MOUTH_FILES.get(face)
    if mf and s.get('tele'):
        if int((t - s['t']) * MOUTH_HZ * 2) % 2:
            im = load(mf)
            if im is not None: return im
    bf = BLINK_FILES.get(face)
    if bf:
        for b in BLINKS:
            if b <= t < b + BLINK_LEN:
                im = load(bf)
                if im is not None: return im
    return load(FACE_FILES.get(face)) or placeholder()


def ease_out(x):
    return 1 - (1 - x) ** 3


def count_text(it, local):
    """数字を0から一気に回して、決めた値で止める。
    「1秒に24億回」を文字で置くだけだと読み飛ばされるが、
    実際に桁が回ると『多すぎる』が体験になる。"""
    hold = it.get('count_in', 0.95)
    p = max(0.0, (local - 0.10) / hold)
    if p >= 1.0:
        return it.get('done', it.get('label', ''))
    v = int(it['count'] * (1 - (1 - p) ** 3))     # 減速しながら到達
    return it.get('fmt', '{:,}').format(v)


def animate_fig(f, anim, t):
    """図を止めない。参考動画は画面が常に動いている。
      spin:秒   … 回る（水の分子）
      alt:秒    … 左右が入れ替わる（電場の反転）
      pulse:秒  … 脈打つ（電波・熱）
      scroll:秒 … 横に流れる（波形）
    """
    if not anim:
        return f
    if isinstance(anim, (int, float)):
        anim = 'spin:%s' % anim
    kind, _, per = str(anim).partition(':')
    per = float(per or 1.0)
    ph = (t % per) / per

    if kind == 'spin':
        return f.rotate(-t / per * 360.0, resample=Image.BICUBIC)
    if kind == 'alt':
        return f.transpose(Image.FLIP_LEFT_RIGHT) if ph >= 0.5 else f
    if kind == 'pulse':
        k = 1.0 + 0.09 * math.sin(2 * math.pi * ph)
        w2, h2 = max(2, int(f.width * k)), max(2, int(f.height * k))
        big = f.resize((w2, h2), Image.LANCZOS)
        out = Image.new('RGBA', f.size, (0, 0, 0, 0))
        out.alpha_composite(big, ((f.width - w2) // 2, (f.height - h2) // 2))
        return out
    if kind == 'scroll':
        dx = int(f.width * ph)
        out = Image.new('RGBA', f.size, (0, 0, 0, 0))
        out.alpha_composite(f, (-dx, 0))
        out.alpha_composite(f, (f.width - dx, 0))
        return out
    return f


def draw_char(canvas, s, t):
    img = char_img(s, t)
    local = t - s['t']

    br = 1.0 + 0.009 * (0.5 - 0.5*math.cos(2*math.pi*(t % 2.6)/2.6))   # 呼吸
    sway = 1.4 * math.sin(2*math.pi*(t % 4.3)/4.3)                     # ゆっくり左右に傾く

    e = ease_out(min(1.0, local / 0.22))          # カット頭の立ち上がり
    lift = int(46 * (1 - e))                      # 下からスッと上がる
    sq   = 1.0 + 0.055 * (1 - e)                  # 入りで少し潰れて戻る

    hop = 0.0                                     # 棒で叩く瞬間に小さく跳ねる
    if s.get('tap'):
        d = local - 0.34
        if 0 <= d < 0.26:
            hop = math.sin(math.pi * d / 0.26) * 15

    sc = br * (1.0 + 0.012*(1-e))
    tw = int(W * CHAR_W_RATIO * sc / sq)
    th = int(img.height * (W * CHAR_W_RATIO * sc) * sq / img.width)
    im = img.resize((max(tw, 2), max(th, 2)), Image.LANCZOS)
    if abs(sway) > 0.05:
        im = im.rotate(sway, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(im, (int(W*CHAR_CX) - im.width//2,
                                int(H*CHAR_FOOT) - im.height + lift - int(hop)))


STICK_FACES = ('explain',)   # 指さし・腕組みのときは棒を持たない   # 手を上げているポーズだけ棒を持たせる

def draw_pointer(canvas, s, t):
    if s.get('face') not in STICK_FACES:
        return
    hx, hy = int(W*HAND[0]), int(H*HAND[1])
    ang = -58.0
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
    local = t - s['t']
    src = img.crop((0, 0, img.width, int(img.height*0.46)))
    br = 1.0 + 0.012 * (0.5 - 0.5*math.cos(2*math.pi*(t % 2.6)/2.6))
    e = ease_out(min(1.0, local / 0.22))
    k = max(W/src.width, H*0.78/src.height) * 1.06 * br * (1 + 0.03*(1-e))
    src = src.resize((int(src.width*k), int(src.height*k)), Image.LANCZOS)
    tilt = 1.1 * math.sin(2*math.pi*(t % 3.7)/3.7)
    if abs(tilt) > 0.05:
        src = src.rotate(tilt, resample=Image.BICUBIC, expand=True)
    im = Image.new('RGBA', (W, H), BOARD)
    im.alpha_composite(src, (W//2 - src.width//2,
                             int(H*0.10) + int(34*(1-e))))
    return im


def title_shot(s, t):
    im = Image.new('RGBA', (W, H), BLACK)
    d = ImageDraw.Draw(im)
    local = t - s['t']
    lines = s['title'].split('\n')
    fnt = tfont(126)
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

def draw_telop(canvas, s, t=None):
    txt = s.get('tele', '')
    if not txt: return
    fnt = tfont(TELOP_SIZE)
    # 強調語だけ一瞬大きくする（画面のどこかが常に動いている状態を作る）
    hifnt = None
    if t is not None:
        d0 = (t - s['t']) - POP_AT
        if 0 <= d0 < POP_LEN:
            k = math.sin(math.pi * d0 / POP_LEN)
            hifnt = tfont(int(TELOP_SIZE * (1 + 0.14 * k)))
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
            rich(dl, W//2, y, marked, fnt, WHITE, MUSTARD, TELOP_STROKE, BLACK, True, hifnt)
            canvas.alpha_composite(lay)
            y += int(TELOP_SIZE*1.34)
    else:
        lay = Image.new('RGBA', (W, H), (0,0,0,0))
        dl = ImageDraw.Draw(lay)
        rich(dl, W//2, int(H*TELOP_Y), txt, fnt, WHITE, MUSTARD, TELOP_STROKE, BLACK, True, hifnt)
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
    # ショットの中ほどで一段だけ寄る。カットを増やさずに変化を足す。
    q = (t - s['t']) - s['dur'] * 0.55
    if q < 0:      step = 0.0
    elif q < 0.30: step = 0.016 * (1 - (1 - q / 0.30) ** 2)
    else:          step = 0.016
    z = s['zoom']
    Z = 1.075
    if z == 'in':    k, ox, oy = 1 + (Z-1)*p + step, 0.5, 0.5
    elif z == 'out': k, ox, oy = Z - (Z-1)*p + step, 0.5, 0.5
    elif z == 'left':  k, ox, oy = Z + step, 0.34 + 0.30*p, 0.5
    else:              k, ox, oy = Z + step, 0.66 - 0.30*p, 0.5
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
        draw_telop(frame, s, t); draw_logo(frame, t)
        return frame.convert('RGB')

    if k == 'screen':
        frame = bg_wide().copy()
        draw_screen(frame, s, t)
        draw_char(frame, s, t)
        frame = apply_zoom(frame, s, t)
        draw_telop(frame, s, t); draw_logo(frame, t)
        return frame.convert('RGB')

    if k == 'board':
        frame = bg_board().copy()
        draw_content(frame, s, t, 'board')
        frame = apply_zoom(frame, s, t)
        draw_telop(frame, s, t); draw_logo(frame, t)
        return frame.convert('RGB')

    frame = bg_wide().copy()
    draw_content(frame, s, t, 'wide')
    draw_pointer(frame, s, t)
    draw_char(frame, s, t)
    frame = apply_zoom(frame, s, t)
    draw_telop(frame, s, t); draw_logo(frame, t)
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
