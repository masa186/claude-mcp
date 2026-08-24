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

CHALK   = (250, 247, 238, 255)
MUSTARD = (223, 164, 43, 255)
CRIMSON = (206, 78, 55, 255)
BOARD   = (61, 106, 90, 255)
WOOD    = (185, 138, 94, 255)
WALL    = (242, 234, 217, 255)
FLOOR   = (198, 170, 136, 255)
WHITE   = (255, 255, 255, 255)
BLACK   = (16, 18, 16, 255)

BOARD_BOX = (int(W*.055), int(H*.105), int(W*.96), int(H*.625))
# 文字を置いていい範囲。寄り（1.18倍）と振りで切り取られる外側を除いた内側。
SAFE_X0, SAFE_X1 = int(W*.115), int(W*.885)
TEXT_BOX  = (SAFE_X0, BOARD_BOX[1]+54, SAFE_X1, BOARD_BOX[3]-40)

CHAR_W_RATIO, CHAR_CX, CHAR_FOOT = 0.50, 0.235, 0.985
HAND = (0.472, 0.774)   # char_explain の上げた手の実測値

TELOP_Y     = 0.480      # テロップの上端（下から20%のUI帯を避ける）
TELOP_Y_FACE = 0.620     # 顔アップのときだけ下げる。口の上に字が乗ると読みにくい
# 視聴者役が喋るときのテロップ。先生とは色も位置も変える。
# 掛け合いのあるショート14本を1本ずつ見たら、14本とも「明らかに別人と
# 分かる声」で、13本は画面にも印を出していた（テロップの色9本・
# 話者の絵7本・テロップの位置7本）。印が無いのは1本だけ。
# こちらは声だけ変えて画に何も出していなかったので「たまに知らん声が出る」
# と言われた。多い順の上位2つ（色・位置）をそのまま当てる。
TELOP_Y_VIEWER = 0.500   # 先生（顔アップは0.620）より上。ただし目や鼻には
                         # かぶせない。0.315まで上げたら顔を隠してしまった
VIEWER_INK  = (150, 214, 240, 255)   # 水色。先生の白と混ざらない
VIEWER_HI   = (255, 236, 150, 255)
VIEWER_PLATE = (16, 44, 62, 165)     # 板も青寄りにする
VIEWER_TAG  = '視聴者'
TELOP_SIZE  = 84
TELOP_STROKE = 6         # 黒フチ
STAGGER     = 0.40       # 黒板の要素を出す間隔（小さい変化のリズム）
POP         = 0.22       # 1つの要素が出そろうまで。話ごとに上書きできる。
                         # ショットを短くした回でこれが長いと、カットの頭に
                         # 何も無い黒板が続いて、切り替わったことが画に出ない。
LEADIN      = 0.033      # カットしてから1つ目が出るまで（1コマ）。
                         # ここが0.1秒あると、カットのたびに一拍空いて重く見える
POP_AT      = 0.38       # テロップの強調語が跳ねる時刻（ショット頭から）
POP_LEN     = 0.16
LOGO        = True

# 視線を1箇所に絞るためのルール。
# 黒板そのものを見せているときにテロップを出すと、視聴者が
# 「黒板と字幕のどっちを読めばいいのか」で迷う。
# 黒板が主役のショット（board / title）ではテロップを出さない。
TELOP_KINDS = ('face', 'screen', 'wide')


# ------------------------------------------------------------- フォント

# 書体は style.py に集約した（黒板・テロップ・図の注記で必ず同じ顔になる）。
# 明朝の太字にしていた。教養寄りの落ち着きを出すためだったが、
# 伸びているショート40本の書体を1本ずつ数えたら、ゴシック29本・丸ゴシック8本に対して
# 明朝は3本しかなかった（docs/decide.md）。太さも極太18本・太い22本で、
# 細い書体は1本も無い。印象として一番多く挙がったのが「勢いがある」26本。
# 落ち着きは黒板の色と余白で出せるので、書体は多数派に寄せる。
import style

FONT_TELOP = style.GOTHIC
FONT_BOARD = style.GOTHIC


def font(size, path=None):
    return style.font(size, path or FONT_BOARD)


def tfont(size):
    return style.font(size, FONT_TELOP)

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


# 表情名 → 「口を閉じた絵」。クチパクの土台になるので、必ず閉じた口を指す。
# char_point（顔が右を向いた絵）は口だけの差分が作れないので使わない。
# 代わりに char_point_open（正面・指さし）の口を閉じた版を mklips.py が作る。
FACE_FILES = dict(surprise='char_surprise.png', explain='char_explain.png',
                  serious='char_serious.png', proud='char_proud.png',
                  point='char_point_closed.png', arms='char_arms_closed.png')

# クチパク用の「口だけ開けた絵」。表情名 → ファイル名。
# mklips.py が char_arms の口を移植して作る（無ければ静かに口を閉じたまま）。
# char_point は顔の向きが違うので対象外。ここに入れると頭が跳ねる。
MOUTH_FILES = dict(explain='char_explain_mouth.png',
                   proud='char_proud_mouth.png',
                   serious='char_serious_mouth.png',
                   surprise='char_surprise_mouth.png',
                   point='char_point_open.png',      # もらった絵をそのまま使う
                   arms='char_arms.png')
# まばたきと重なったとき用
BLINK_MOUTH = dict(explain='char_blink_mouth.png')

# ナレーションから作った「このコマは口を開けているか」の並び。
# voice.envelope() が入れる。これがあると、決まった速さではなく
# 実際に声が出ているところで口が開く。
MOUTH_ENV = None
MOUTH_HZ = 6.5           # 波形が無いときの代わり（一定の速さでパクパク）

# 口を閉じたままにする時間帯。カワウソ以外（視聴者役）が喋っている所。
# 波形は1本にまとめてあるので、これが無いと誰の声でも先生の口が動く。
MOUTH_MUTE = []


def mouth_open(t):
    """その時刻に口を開けているか。波形が無ければ None。"""
    if MOUTH_ENV is None:
        return None
    for a, b in MOUTH_MUTE:
        if a <= t < b:
            return False
    i = int(t * FPS)
    return bool(MOUTH_ENV[i]) if 0 <= i < len(MOUTH_ENV) else False

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
        z = ZOOM_CYCLE[i % len(ZOOM_CYCLE)]
        # 文字のあるショットで横に振ると、端の字が切れる。
        # 寄り／引きなら倍率が変わり続けるので、切らずに動きだけ稼げる。
        if s['kind'] in ('board', 'wide', 'stage') and z in ('left', 'right'):
            z = 'in' if z == 'left' else 'out'
        s.setdefault('zoom', z)
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


# 影。伸びているショート30本を1本ずつ見た記録では、フチが30本中30本、
# 影が29本。フチだけだと文字が背景に貼り付いて見え、影を付けると浮く。
# ここが素人との差として一番はっきり数字に出ていた。
SHADOW = (7, 8, (0, 0, 0, 135))


def rich(d, x, y, text, fnt, base, hi, stroke=0, scol=BLACK, anchor_c=False,
         hifnt=None, shadow=SHADOW):
    """{ } で囲んだ語だけ色を変える。hifnt を渡すと、その語だけ別サイズで描く。"""
    segs = parts(text)
    hf = hifnt or fnt
    total = sum(d.textlength(s, font=(hf if h else fnt)) for s, h in segs)
    x0 = x - total / 2 if anchor_c else x
    # 影を先に一周描いてから、本体を上に重ねる
    for is_shadow in ((True, False) if shadow else (False,)):
        cx = x0
        for s, is_hi in segs:
            f = hf if is_hi else fnt
            dy = -(hf.size - fnt.size) * 0.42 if (is_hi and hifnt is not None) else 0
            if is_shadow:
                d.text((cx + shadow[0], y + dy + shadow[1]), s, font=f,
                       fill=shadow[2], stroke_width=stroke, stroke_fill=shadow[2])
            else:
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
    _bg['wide'] = vignette(im, 0.30)
    return _bg['wide']


def vignette(im, strength=0.62):
    """中央を明るく、周辺を落とす。全面が同じ色だと平板に見えるので、
    面の中に明暗を作る。参考動画は明るい画素と暗い画素の差が大きい。"""
    import numpy as np
    a = np.array(im).astype(np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w*0.5)/(w*0.62))**2 + ((yy - h*0.42)/(h*0.72))**2)
    k = np.clip(1.42 - strength * r**1.5, 0.38, 1.55)[..., None]
    a[..., :3] = np.clip(a[..., :3] * k, 0, 255)
    return Image.fromarray(a.astype('uint8'), 'RGBA')


def bg_board():
    """黒板だけに寄った画面。"""
    if 'board' in _bg: return _bg['board']
    im = Image.new('RGBA', (W, H), BOARD)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 26], fill=WOOD)
    d.rectangle([0, H-26, W, H], fill=WOOD)
    _bg['board'] = vignette(im)
    return _bg['board']


# ------------------------------------------------------------- 黒板の中身

def wipe(t0, t, dur=0.22):
    return 0.0 if t < t0 else min(1.0, (t - t0) / dur)


def entry(t0, t, dur=0.22, delay=0.0):
    """カットの頭の出し方。0→1 の進み具合を返す。

    動画の1コマ目（t0<=0）だけは、最初から出し切った状態にする。
    LEADIN（1コマの間）も POP_IN（出そろうまで）も 0秒に効かせると、
    何も描かれていない黒板が1コマ目に入る。そこにフラッシュもかかるので、
    白く飛んだ空の板が1枚だけ挟まって見える。
    実測では伸びている21本中18本が、0秒の時点で既に何かが動いていた。
    """
    if t0 <= 0.0:
        return 1.0
    return wipe(LEADIN + delay, t - t0, dur)


def board_area(kind):
    if kind == 'board':
        return (SAFE_X0, int(H*.19), SAFE_X1, int(H*.79))
    return TEXT_BOX


_measure = ImageDraw.Draw(Image.new('RGBA', (4, 4)))


def fit_size(text, size, maxw):
    """はみ出すなら字を小さくする。台本を書き換えるたびに幅を数えるのは
    現実的でないので、切れるくらいなら自動で縮める。"""
    for ln in text.split('\n'):
        plain = ''.join(x for x, _ in parts(ln))
        while size > 40 and _measure.textlength(plain, font=font(size)) > maxw:
            size -= 4
    return size



# 図を貼る「板」。黒板の上に一段暗い面を置いて、そこに図と文字をまとめる。
#
# 参考にしている3人・6本を測ったら、画面の埋まりが66〜85%だった。
# こちらは30%で、内訳を見ると board のショットが11.6%しかない（face は50.4%）。
# 黒板の緑が広いまま空いているのが原因で、動きやカットの速さは共通点ではなかった
# （6本の動きは0.29〜9.04と30倍ばらついていて、静止83%の回も伸びている）。
#
# 白い紙を敷くとチョークの白い線が消えるので、板より暗い面にする。
# コントラストが上がって図も読みやすくなる。
CARD_ON   = False        # 話ごとに render.CARD_ON = True で入れる
CARD_PAD  = 0.030        # 描画領域の外側に足す余白（画面幅に対する比）
CARD_DARK = 0.62         # 黒板の色に掛ける倍率。1.0で黒板と同じ
CARD_EDGE = (214, 226, 214, 90)


def draw_card(canvas, kind):
    """図と文字の下に敷く面。board / stage のときだけ。"""
    if not CARD_ON or kind not in ('board', 'stage'):
        return
    a = board_area(kind)
    pad = int(W * CARD_PAD)
    box = (max(4, a[0] - pad), max(4, a[1] - pad),
           min(W - 4, a[2] + pad), min(H - 4, a[3] + pad))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    col = tuple(int(c * CARD_DARK) for c in BOARD[:3]) + (236,)
    d.rounded_rectangle(box, radius=int(W * 0.035), fill=col,
                        outline=CARD_EDGE, width=5)
    canvas.alpha_composite(lay)


def draw_content(canvas, s, t, kind):
    a = board_area(kind)
    local = t - s['t']
    draw_card(canvas, kind)
    rows = []

    if s.get('fig'):
        name, scale, spin = s['fig']
        # 名前が「/」で終わるものは clips/ の連番。空気が曲がる動きなど、
        # 1枚絵では伝わらないものはここで再生する。
        img = (seq_frame(name, local, spin == 'hold') if name.endswith('/')
               else load(name))
        if spin == 'hold':
            spin = None
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
        it['size'] = fit_size(it['text'], it['size'], a[2] - a[0])
        rows.append(('txt', it))

    total = 0
    for r in rows:
        total += (r[3] + 30) if r[0] == 'fig' else \
                 int(r[1]['size'] * 1.32) * len(r[1]['text'].split('\n')) + 18
    y = a[1] + max(0, int(((a[3]-a[1]) - total) * (0.5 if kind == 'board' else 0.30)))

    d = ImageDraw.Draw(canvas)
    for ri, r in enumerate(rows):
        # 1つずつ間を置いて出す。これが「小さい変化」の本体。
        p = entry(s['t'], t, POP, ri * STAGGER)
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
                slide = int(46 * (1 - p) ** 2)      # 出るときに左から滑り込む
                x0 = ((a[0]+a[2])//2 if ctr else a[0]) - slide
                # 黒フチを入れる。ここだけフチ無しで描いていたので、
                # 黒板の緑に対して明るさの差がほとんど無かった。
                # 実測で赤は1.40:1、黄でも2.78:1（見出しの目安は3:1）。
                # 色だけで差を付けると、赤緑の見分けが付きにくい人には読めない。
                # フチを入れれば、色に頼らず明るさで輪郭が出る。
                wid = rich(dl, x0, y, ln, fnt, col, MUSTARD,
                           stroke=max(5, it['size'] // 20), scol=BLACK,
                           anchor_c=ctr)
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
ROLL = 0.30                   # 降りてくる時間（秒）

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

    # 声が出ているコマだけ口を開ける（波形が無ければ一定の速さで代用）
    op = mouth_open(t)
    if op is None:
        op = bool(s.get('tele')) and bool(int((t - s['t']) * MOUTH_HZ * 2) % 2)
    blinking = any(b <= t < b + BLINK_LEN for b in BLINKS)

    # まばたき×口の4通りを、あるものから順に選ぶ
    cands = []
    if blinking and op: cands.append(BLINK_MOUTH.get(face))
    if blinking:        cands.append(BLINK_FILES.get(face))
    if op:              cands.append(MOUTH_FILES.get(face))
    cands.append(FACE_FILES.get(face))
    for c in cands:
        im = load(c) if c else None
        if im is not None:
            return im
    return placeholder()


def ease_out(x):
    return 1 - (1 - x) ** 3


def seq_frame(name, local, hold=False):
    """clips/<名前>/ の連番を図として再生する。矢印1本では伝わらない
    「空気が実際に曲がる」ような動きは、連番で見せるしかない。

    hold=True … 最後まで行ったらそこで止める。オチのある図（同時に着かない）は
    ショットが連番より長いと頭から巻き戻ってしまい、結論が消える。"""
    fs = clip_frames(name.rstrip('/'))
    if not fs:
        return None
    i = int(local * FPS)
    if hold:
        i = min(i, len(fs) - 1)
    return clip_frame(name.rstrip('/'), i)


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
    # 以前ここで体を±1.4度ゆっくり傾けていたが、首が動いているように見えて
    # 気持ち悪かった。絵が1枚しかないので、傾けても生き物っぽくはならない。

    e = ease_out(min(1.0, local / 0.14))          # カット頭の立ち上がり
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


FACE_HEAD  = 0.66    # 中身の高さのうち、切り出す割合（胸から上）
FACE_FILL  = 0.86    # 切り出した絵を画面幅の何倍にするか
FACE_CY    = 0.36    # 切り出した絵の中心を画面のどの高さに置くか


def face_shot(s, t):
    """キャラの顔だけを全画面に。

    画像の上端から切ると、透明な余白の量が絵ごとに違うので顔の位置がずれる
    （表情を変えるたびに顔が切れたり、画面外に飛んだりする）。
    必ず「中身の範囲」を測ってから、その上から4割を頭として切り出す。
    """
    img = char_img(s, t)
    local = t - s['t']
    box = img.getbbox() or (0, 0, img.width, img.height)
    x0, y0, x1, y1 = box
    head = img.crop((x0, y0, x1, y0 + max(8, int((y1 - y0) * FACE_HEAD))))
    # 指さしポーズは腕の分だけ横に広い。切り出したあとで測り直さないと
    # 顔が中心から外れて、画面の端に寄ってしまう。
    hb = head.getbbox()
    if hb:
        head = head.crop(hb)

    br = 1.0 + 0.012 * (0.5 - 0.5*math.cos(2*math.pi*(t % 2.6)/2.6))
    e = ease_out(min(1.0, local / 0.14))
    push = 1 + 0.10 * min(1.0, local / max(s['dur'], .01))   # ずっとゆっくり寄る
    k = (W * FACE_FILL) / head.width * br * push * (1 + 0.03*(1-e))
    head = head.resize((max(2, int(head.width*k)), max(2, int(head.height*k))),
                       Image.LANCZOS)
    im = Image.new('RGBA', (W, H), BOARD)
    im.alpha_composite(head, (W//2 - head.width//2,
                              int(H*FACE_CY) - head.height//2 + int(30*(1-e))))
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
        p = wipe(0.02 + i*0.06, local, 0.11)
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
    if s['kind'] not in TELOP_KINDS and not s.get('tele_force'):
        return
    txt = s.get('tele', '')
    if not txt: return
    # 出はじめだけ大きめから縮めて収める。ただ現れるより目が止まる
    ent = pop(entry(s['t'], t, POP_IN)) if t is not None else 1.0
    size = max(24, int(TELOP_SIZE * ent))
    fnt = tfont(size)
    # 強調語だけ一瞬大きくする（画面のどこかが常に動いている状態を作る）
    hifnt = None
    if t is not None:
        d0 = (t - s['t']) - POP_AT
        if 0 <= d0 < POP_LEN:
            k = math.sin(math.pi * d0 / POP_LEN)
            hifnt = tfont(int(size * (1 + 0.14 * k)))
    d = ImageDraw.Draw(canvas)
    # 視聴者役の台詞は、色と位置の両方を変える。声だけ変えても
    # 「誰が喋っているのか」は画面から分からない。
    vw = s.get('who') == 'viewer'
    ink, hi = (VIEWER_INK, VIEWER_HI) if vw else (WHITE, MUSTARD)
    pcol = VIEWER_PLATE if vw else None
    ty = TELOP_Y_VIEWER if vw else (TELOP_Y_FACE if s['kind'] == 'face' else TELOP_Y)
    # 長い行は2行に折る
    segs = parts(txt)
    plain = ''.join(x for x, _ in segs)
    if d.textlength(plain, font=fnt) > W*0.88:
        half = len(plain)//2
        cut = plain.rfind('、', 0, half+6)
        cut = cut+1 if cut > 3 else half
        rows = [plain[:cut], plain[cut:]]
        hi_set = set(x for x, h in segs if h)
        y = int(H*ty) - int(size*0.67)
        for rw in rows:
            lay = Image.new('RGBA', (W, H), (0,0,0,0))
            dl = ImageDraw.Draw(lay)
            marked = rw
            for h in hi_set:
                if h in marked: marked = marked.replace(h, '{'+h+'}')
            plate(canvas, rich_box(W//2, y, marked, fnt, TELOP_STROKE, True, hifnt),
                  col=pcol)
            rich(dl, W//2, y, marked, fnt, ink, hi, TELOP_STROKE, BLACK, True, hifnt)
            canvas.alpha_composite(lay)
            y += int(size*1.34)
    else:
        y = int(H*ty)
        plate(canvas, rich_box(W//2, y, txt, fnt, TELOP_STROKE, True, hifnt), col=pcol)
        lay = Image.new('RGBA', (W, H), (0,0,0,0))
        dl = ImageDraw.Draw(lay)
        rich(dl, W//2, y, txt, fnt, ink, hi, TELOP_STROKE, BLACK, True, hifnt)
        canvas.alpha_composite(lay)
    if vw:
        # 誰が喋っているかを一言だけ出す。実測で「話者の絵」が7本あったが、
        # 視聴者役の絵は持っていないので、名札で代える。
        tf = tfont(38)
        ty2 = int(H*ty) - 52
        lay = Image.new('RGBA', (W, H), (0,0,0,0))
        plate(canvas, rich_box(W//2, ty2, VIEWER_TAG, tf, 4, True), col=VIEWER_PLATE)
        rich(ImageDraw.Draw(lay), W//2, ty2, VIEWER_TAG, tf, VIEWER_INK, VIEWER_INK,
             4, BLACK, True)
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
    # カットの頭で寄りを少しだけ行き過ぎさせて戻す。30本の記録で
    # 単純なカット以外の切り替えは15本、その内訳の1位がこのズームだった
    # （11本。フラッシュは3本しかない）。派手さより、これが効く。
    d0 = t - s['t']
    if 0 <= d0 < PUNCH_LEN:
        step += PUNCH_AMP * (1 - d0 / PUNCH_LEN) ** 2
    z = s['zoom']
    # 寄りと振りの幅は、そのショットに文字があるかで変える。
    # 1.34倍で端まで振ると、見えるのは元の横幅の 53% しかない。
    # 黒板の文字はそこからはみ出して切れるので、文字ショットは控えめにする。
    text_shot = s['kind'] in ('board', 'wide', 'stage')
    Z, PAN = (1.26, 0.30) if text_shot else (1.34, 0.84)
    drift = (0.03 if text_shot else 0.06) * \
        math.sin(2*math.pi*((t - s['t']) / max(s['dur'],.01)) * 0.5)
    c0 = 0.5 - PAN/2
    if z == 'in':    k, ox, oy = 1 + (Z-1)*p + step, 0.5, 0.5 + drift
    elif z == 'out': k, ox, oy = Z - (Z-1)*p + step, 0.5, 0.5 - drift
    elif z == 'left':  k, ox, oy = Z + step, c0 + PAN*p, 0.5
    else:              k, ox, oy = Z + step, 1 - c0 - PAN*p, 0.5
    bw, bh = int(W*k), int(H*k)
    big = im.resize((bw, bh), Image.LANCZOS)
    x = int((bw - W) * ox); y = int((bh - H) * oy)
    return big.crop((x, y, x+W, y+H))


# --------------------------------------------------- 切り替えと当たりの演出
#
# 伸びているショート30本を Gemini に1本ずつ見せて、編集の手つきだけを
# 書き出させた（yt-analysis/data/craft_raw.md）。素人との差はここに出ていた:
#   ・切り替えが単純なカットだけではない。白フラッシュが一番多い
#   ・文字が「ポン」と出る。ただ現れるのではなく、大きめから縮んで収まる
#   ・文字に黒フチと影、その下に半透明の板。背景が何であっても読める
#   ・決め所で画面が揺れる
# どれも1コマずつ描くこちらの作り方で実装できる。順に足す。

FLASH_LEN  = 0.12        # 白フラッシュの長さ（秒）
FLASH_MAX  = 0.42        # 一番白いときの混ぜ具合。1.0 は真っ白で目に痛い
SHAKE_LEN  = 0.22        # 揺れの長さ
SHAKE_AMP  = 14          # 揺れ幅（px）
PUNCH_LEN  = 0.20        # カット頭の寄りの当て（秒）
PUNCH_AMP  = 0.032       # その寄り幅（倍率）
# 文字の出し方は30本中26本が「ポンと一瞬で出る」だった。拡大しながらは4本。
# なので伸び縮みは見せる演出ではなく、4コマで収める“当て”にする。
POP_IN     = 0.13        # 文字が出そろうまで（秒）
_WHITE_IM  = {}


def apply_flash(im, s, t):
    """一瞬だけ画面を白く飛ばす。

    30本のうちフラッシュを使っていたのは3本だけだった。全部のカットに
    入れると安っぽくなる。話が裏返る所（flash=True と書いた所）だけ。
    """
    if not s.get('flash'):
        return im
    d = t - s['t']
    if d < 0 or d >= FLASH_LEN:
        return im
    k = FLASH_MAX * (1 - d / FLASH_LEN) ** 2
    w = _WHITE_IM.get(im.mode)
    if w is None:
        w = _WHITE_IM[im.mode] = Image.new(im.mode, (W, H), (255, 255, 255)
                                           if im.mode == 'RGB' else WHITE)
    return Image.blend(im, w, k)


def apply_shake(im, s, t):
    """決め台詞の頭で画面を短く揺らす。音の一撃と合わせると効く。"""
    if not s.get('shake', s.get('se') == 'impact'):
        return im
    d = t - s['t']
    if d < 0 or d >= SHAKE_LEN:
        return im
    a = SHAKE_AMP * (1 - d / SHAKE_LEN) ** 2
    dx = int(round(a * math.sin(d * 2*math.pi * 13)))
    dy = int(round(a * math.cos(d * 2*math.pi * 9)))
    if not dx and not dy:
        return im
    # ずらすと端に穴が空くので、少し大きく描いてから切り出す
    pad = SHAKE_AMP + 2
    big = im.resize((W + 2*pad, H + 2*pad), Image.LANCZOS)
    return big.crop((pad+dx, pad+dy, pad+dx+W, pad+dy+H))


def pop(p):
    """0→1 の進み具合を、行き過ぎて戻る倍率に変える。

    ただ出すのと、いったん大きく出してから収めるのとでは、
    同じ0.2秒でも目の止まり方が違う。30本中ほとんどがこれをやっていた。
    """
    if p >= 1:
        return 1.0
    e = 1 - (1 - p) ** 3                 # 立ち上がりを速く
    return 0.62 + 0.44 * e - 0.06 * math.sin(math.pi * e)


PLATE_PAD = (34, 14)     # 板の余白（横, 縦）
PLATE_COL = (14, 20, 17, 150)


def rich_box(x, y, text, fnt, stroke=0, anchor_c=False, hifnt=None,
             shadow=SHADOW):
    """rich() が実際に紙に乗せる範囲を返す。板の位置合わせに使う。

    フォントの「サイズ」と、実際に描かれる高さは別物。明朝の128ptで測ると
    インクは y+31 から y+175 に乗る（高さ144）。サイズから cy = y+64 と
    当てずっぽうに置くと、板が文字より40pxほど上にずれる。
    強調語で別サイズを使うときは横幅も変わるので、そこも数え直す。
    """
    d = _measure
    segs = parts(text)
    hf = hifnt or fnt
    total = sum(d.textlength(s, font=(hf if h else fnt)) for s, h in segs)
    cx = x - total / 2 if anchor_c else x
    box = None
    for s, is_hi in segs:
        f = hf if is_hi else fnt
        dy = -(hf.size - fnt.size) * 0.42 if (is_hi and hifnt is not None) else 0
        b = d.textbbox((cx, y + dy), s, font=f, stroke_width=stroke)
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                     max(box[2], b[2]), max(box[3], b[3]))
        cx += d.textlength(s, font=f)
    if box is None:
        return None
    # 影は文字の右下に落ちる。板からはみ出すと浮いて見えるので中に入れる
    return (box[0], box[1], box[2] + (shadow[0] if shadow else 0),
            box[3] + (shadow[1] if shadow else 0))


def plate(canvas, box, alpha=1.0, col=None):
    """文字の下に敷く半透明の板。背景が図でも実写でも読めるようにする。

    box は rich_box() が返した実際のインクの範囲。
    """
    if alpha <= 0 or box is None:
        return
    x0, y0, x1, y1 = box
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    r = int(min(y1 - y0, 90) * 0.34)
    ImageDraw.Draw(lay).rounded_rectangle(
        [x0 - PLATE_PAD[0], y0 - PLATE_PAD[1],
         x1 + PLATE_PAD[0], y1 + PLATE_PAD[1]], radius=r, fill=col or PLATE_COL)
    if alpha < 1:
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v*alpha)))
    canvas.alpha_composite(lay)


# ------------------------------------------------------------- 1フレーム

# ------------------------------------------------------------- 舞台（stage）
#
# 336万再生の長尺解説を実測したところ、1秒ごとの画面変化はこうだった:
#   ほぼ同じ 92〜96%  /  一部だけ変わる 3〜5%  /  全面入れ替え 0〜3%
# つまりあの見やすさは「よく動くから」ではない。レイアウトが動かないまま
# 中身が1つずつ足されていくから、視聴者は毎回どこを見るか探さなくていい。
#
# こちらは短尺なので止めはしないが、役割の分け方はそのまま持ってくる:
#   主役 … 画面中央の図
#   補助 … 図の下に1行ずつ積み上がる結論
#   案内 … カワウソ（右下に小さく固定。主役にしない）
#   補足 … 字幕（下・小さめ。音声の書き起こしであって見出しではない）
#   目印 … 章タイトル（左上に出しっぱなし）

STAGE_BOX  = (0.085, 0.115, 0.915, 0.545)   # 図の置き場（画面比）
# 伸びているショート40本の文字の置き方を実測した結果（docs/text.md）:
#   同時に出す行数 … 2行 23本 ／ 3行以上 16本 ／ 1行 1本
#   文字の位置     … 上〜中央 33本 ／ 下部 7本
#   行間           … 余裕がある 33本 ／ 詰まっている 7本
# 下端を 0.760 から上げた。下部が少数派なのに加えて、板の下端が画面の86%まで
# 来ていて、縦動画のUI（いいね・コメント）と重なる位置だった。
STAGE_BOT  = 0.700                          # 積み上がる行の下端（ここは動かさない）
STAGE_SIZE = 128                            # 短い言葉を大きく。読ませない
STAGE_GAP  = 12                             # 板と板のあいだの隙間（px）
# 既定は2行。40本で一番多いのがこれ。
# ただし因果を1枚で見せる場面だけは shot に stack=3 と書いて増やせる。
# 3行そのものが説明の中身になっている所（翼は上向き→空気を下に押す→翼は上へ）
# まで2行にすると、話の筋が画面から消える。
STAGE_MAX  = 2


def _stage_lh():
    """行送りを実測から出す。

    148px という数字を手で置いていたが、これは板を「フォントの公称サイズ」で
    作っていた頃の値。板を実際のインクに合わせた途端、板の高さが180pxになり、
    行送りのほうが小さいので板どうしが32px重なった。
    字の大きさや余白を変えても崩れないように、ここも数えて決める。
    """
    b = _measure.textbbox((0, 0), '翼は上向き', font=font(STAGE_SIZE),
                          stroke_width=7)
    return (b[3] - b[1]) + SHADOW[1] + 2 * PLATE_PAD[1] + STAGE_GAP


STAGE_LH   = _stage_lh()                    # 行の高さ（px）
# 右下。下端で切れる。
# 0.34 だと口の幅が画面上で約97pxしかなく、クチパクが読み取れなかった。
# 行を2行に減らして下に余白ができたぶん、少し大きくする。
CHAR_STAGE = dict(w=0.40, cx=0.855, foot=1.075)
# 画面下の長文テロップは廃止した。短尺の視聴者は2行以上出た時点で読むのをやめる。
# 細かい説明は全部ナレーションに持たせて、画面には短い言葉だけを大きく出す。
SUB_ON     = False
SUB_Y      = 0.792                          # 字幕の位置（SUB_ON のときだけ）
SUB_SIZE   = 50
CHAP_XY    = (0.058, 0.043)
CHAP_SIZE  = 52
CHAPTERS   = {}                             # sec名 → 章タイトル（各話で入れる）


def scene_shots(s):
    """同じ scene の、先頭から自分までのショット。ここまでに出た要素が舞台に残る。"""
    sc = s.get('scene')
    if not sc:
        return [s]
    out = []
    for x in SHOTS:
        if x.get('scene') == sc:
            out.append(x)
            if x is s:
                break
    return out


def chapter_of(s):
    """自分より前（自分を含む）で最後に指定された sec の章タイトル。"""
    lab = None
    for x in SHOTS:
        if x.get('sec') in CHAPTERS:
            lab = CHAPTERS[x['sec']]
        if x is s:
            break
    return lab


def draw_chapter(canvas, s):
    lab = chapter_of(s)
    if not lab:
        return
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    dl.text((int(W*CHAP_XY[0]), int(H*CHAP_XY[1])), lab, font=tfont(CHAP_SIZE),
            fill=CHALK, stroke_width=4, stroke_fill=(24, 42, 36, 220))
    canvas.alpha_composite(lay)


def draw_sub(canvas, s):
    """字幕。見出しではないので小さく、下に置く。"""
    if not SUB_ON:
        return
    txt = (s.get('sub') or s.get('say') or '').replace('{', '').replace('}', '')
    if not txt:
        return
    fnt = tfont(SUB_SIZE)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    cx, maxw = int(W*0.44), int(W*0.80)
    rows, cur = [], ''
    for ch in txt:
        if dl.textlength(cur + ch, font=fnt) > maxw and len(rows) < 1:
            rows.append(cur); cur = ''
        cur += ch
    rows.append(cur)
    y = int(H*SUB_Y)
    for r in rows[:2]:
        dl.text((cx, y), r, font=fnt, fill=WHITE, anchor='mm',
                stroke_width=5, stroke_fill=BLACK)
        y += int(SUB_SIZE*1.32)
    canvas.alpha_composite(lay)


def draw_char_small(canvas, s, t):
    """案内役としてのカワウソ。右下に小さく、下端で切れる位置に置く。
    主役は図なので、ここは動かしすぎない。"""
    img = char_img(s, t)
    local = t - s['t']
    br = 1.0 + 0.008 * (0.5 - 0.5*math.cos(2*math.pi*(t % 2.6)/2.6))
    e = ease_out(min(1.0, local / 0.16))
    tw = int(W * CHAR_STAGE['w'] * br)
    th = int(img.height * tw / img.width)
    im = img.resize((max(tw, 2), max(th, 2)), Image.LANCZOS)
    canvas.alpha_composite(im, (int(W*CHAR_STAGE['cx']) - im.width//2,
                                int(H*CHAR_STAGE['foot']) - im.height + int(26*(1-e))))


def stage_shot(s, t):
    frame = bg_board().copy()
    seq = scene_shots(s)
    local = t - s['t']
    a = (int(W*STAGE_BOX[0]), int(H*STAGE_BOX[1]),
         int(W*STAGE_BOX[2]), int(H*STAGE_BOX[3]))

    # 図は scene のあいだ出しっぱなし。新しい fig が来たらそこで差し替わる
    figspec, fig_at = None, 0.0
    for x in seq:
        if x.get('fig'):
            figspec, fig_at = x['fig'], x['t']
    if figspec:
        name, scale, anim = figspec
        img = (seq_frame(name, t - fig_at, anim == 'hold') if name.endswith('/')
               else load(name))
        if img is not None:
            tw = min(int((a[2]-a[0]) * scale), int(W*0.79))
            th = int(img.height * tw / img.width)
            if th > a[3]-a[1]:
                th = a[3]-a[1]; tw = int(img.width * th / img.height)
            f = img.resize((tw, th), Image.LANCZOS)
            if anim and anim != 'hold':
                f = animate_fig(f, anim, t - fig_at)
            p = entry(fig_at, t, 0.20)
            if p < 1:
                f.putalpha(f.getchannel('A').point(lambda v: int(v*p)))
            frame.alpha_composite(f, ((a[0]+a[2])//2 - tw//2,
                                      (a[1]+a[3])//2 - th//2))

    # ここまで（背景と図）だけを寄せる。文字とカワウソは動かさない。
    # 参考動画はレイアウトが1pxも動かないので、視聴者が毎回探さなくて済む。
    frame = apply_zoom(frame, s, t)
    draw_char_small(frame, s, t)

    # 結論の行は消さずに積む。1枚の画面の中で話が進んでいく形にする
    rows = [(x, x['add']) for x in seq if x.get('add')][-s.get('stack', STAGE_MAX):]
    # 下から積む。新しい行がいつも同じ高さに出るので、視線が迷わない
    y = int(H*STAGE_BOT) - STAGE_LH * (len(rows) - 1)
    d = ImageDraw.Draw(frame)
    for x, item in rows:
        it = item if isinstance(item, dict) else dict(text=item)
        size = fit_size(it['text'], it.get('size', STAGE_SIZE), int(W*0.84))
        newest = (x is s)
        p = entry(x['t'], t, POP_IN) if newest else 1.0
        if p <= 0:
            continue
        # 実測した人気ショートは8本中8本が、背景の上に載る巨大テロップだった。
        # 黒板に書いた文字に見えると弱いので、フチを付けて前面に浮かせる。
        # 出し方はスライドをやめて「大きめから縮んで収まる」にした。
        # 30本の記録で一番多かったのがこれ。目が止まる位置がはっきりする。
        k = pop(p) if newest else 1.0
        fs = max(24, int(size * k))
        fnt = font(fs)
        # 字が大きくなるぶん上に伸ばして、行の中心を動かさない
        ly = y - int((fs - size) * 0.5)
        al = (1.0 if newest else 0.52) * min(1.0, p*1.4)
        # 板は実際に描かれる範囲から作る。サイズから作ると文字とずれる
        plate(frame, rich_box(W//2, ly, it['text'], fnt, 7, True), al * 0.85)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        rich(dl, W//2, ly, it['text'], fnt,
             it.get('color', CHALK), MUSTARD, 7, BLACK, True)
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v*al)))
        frame.alpha_composite(lay)
        y += STAGE_LH

    draw_sub(frame, s); draw_chapter(frame, s)
    return frame.convert('RGB')


def _finish(frame, s, t):
    """揺れ → 白フラッシュ の順で仕上げる。
    フラッシュは切り替えの合図なので、揺れた後の絵に被せる。"""
    return apply_flash(apply_shake(frame.convert('RGB'), s, t), s, t)


def render_frame(t):
    s = shot_at(t)
    k = s['kind']

    if k == 'stage':
        return _finish(stage_shot(s, t), s, t)

    if k == 'title':
        return _finish(apply_zoom(title_shot(s, t), s, t), s, t)

    if k == 'face':
        frame = face_shot(s, t)
        frame = apply_zoom(frame, s, t)
        draw_telop(frame, s, t); draw_logo(frame, t)
        return _finish(frame, s, t)

    if k == 'screen':
        frame = bg_wide().copy()
        draw_screen(frame, s, t)
        draw_char(frame, s, t)
        frame = apply_zoom(frame, s, t)
        draw_telop(frame, s, t); draw_logo(frame, t)
        return _finish(frame, s, t)

    if k == 'board':
        frame = bg_board().copy()
        draw_content(frame, s, t, 'board')
        frame = apply_zoom(frame, s, t)
        draw_telop(frame, s, t); draw_logo(frame, t)
        return _finish(frame, s, t)

    frame = bg_wide().copy()
    draw_content(frame, s, t, 'wide')
    draw_pointer(frame, s, t)
    draw_char(frame, s, t)
    frame = apply_zoom(frame, s, t)
    draw_telop(frame, s, t); draw_logo(frame, t)
    return _finish(frame, s, t)


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
