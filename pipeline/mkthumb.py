"""サムネイルを書き出す。

ショートはフィードでは1コマ目が出るのでサムネは効かないが、
チャンネルの一覧と検索結果ではサムネが出る。1本見た人が2本目に行くかは
そこで決まるので、動画と同じ色・同じ書体で揃えておく。

サムネの画像そのものは取れない（i.ytimg.com が組織のポリシーで遮断）。
そこで、伸びているショート20本の「1コマ目」を Gemini に見せて数えた
（docs/firstframe.md）。ショートはフィードで1コマ目が出るので、
そこが実質のサムネになる。分かったこと:
  ・文字は20本中20本にある。10〜20文字がボリュームゾーン
  ・フチか背景板 18/20
  ・位置は上部13・中央5・下部2 → 上寄せ
  ・顔があるのは10/20。写すときは画面の4〜8割と大きく
  ・背景は実写13・イラスト7。そして明るい16 / 暗い4
  ・続きを見たくなる要素の1位は「9割が知らない」系のフレーズ 8/20

一番外していたのが明るさ。黒板は暗い側の少数派なので、実写クリップが
ある回はそれを背景に使って明るくする。文字の下の板は暗いままでいい
（明るい背景の上では、むしろ暗い板のほうが読める）。

同じ40本で測った「画面の文字の置き方」も引き続き当てる（docs/text.md）:
  ・フチ 30/30本、影 29/30本 → 両方付ける
  ・色は白35本・黄18本 → 白地に黄の強調
  ・同時に2行が23本で最多 → 2行に収める
  ・1行5〜10文字 → それ以上は入れない
  ・位置は上〜中央が33本 → 上寄せ

動画の中の文字より一段大きくする。一覧では実寸が親指くらいなので、
動画で読める大きさでは読めない。

  python3 mkthumb.py
"""
import os
from PIL import Image, ImageDraw
import render
from render import CHALK, MUSTARD, BLACK, CRIMSON
import math as _m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'brand')

W, H = 1080, 1920

# 各話。fig は clips/ の連番か assets/ の1枚
EPS = [
    # 第12話。フックの数字をそのままサムネに出す。答え（3つの守りかた）は
    # 書かない。伸びた参考4本は題名にもサムネにも答えを書いていなかった。
    # 実写が無いので、浴槽＋振り切れた温度計のアイコンで「熱さの話」だと示す。
    dict(file='thumb_ep12.png', label='風呂',
         bg='board', lines=['交通事故の7.5倍', '風呂で死ぬ人'],
         fig=('icon:bath', 0), face='serious'),
    # 第10話。陰キャの憧れ707本で、題名に「なぜ」が入ると1.77倍だった。
    # サムネは題名と役割を分ける。題名が「なぜ」を言うので、サムネは
    # 「え、穴？」という違和感だけを見せる。答え（外側が全部受け持つ）は書かない。
    # 背景は wing（窓から見た主翼・明るさ163で手持ち最明）。
    # ただし wing に穴は映っていないので、窓のアイコンを重ねて穴を指す。
    dict(file='thumb_ep10.png', label='飛行機の窓',
         bg='clip:wing', lines=['飛行機の窓', 'この穴、わざと'],
         fig=('icon:window', 0), face='surprise'),
    # 図は「色が付いていて太いもの」を選ぶ。線画は親指の大きさでは消える。
    # bg  … 'clip:名前' なら実写を背景に敷いて明るくする。無ければ黒板
    # lines … 1行目に煽り、2行目に結論。合計10〜20文字に収める
    # 第7話。化け学のふしぎ250本で「◯年間」が入ると1.78倍だった。
    # サムネにも数字を入れて、答え（缶切り）は出さない。
    # 背景は実写の缶詰。1コマ目の実測は 実写13/20・明るい16/20 で、
    # cans は明るさ146と手持ちで一番明るい。
    dict(file='thumb_ep07.png', label='缶詰',
         bg='clip:cans', lines=['48年間', '誰も開けられなかった'],
         fig=None, face='surprise'),
    # 第6話。参考チャンネル18本の実測で、伸びた4本はタイトルにもサムネにも
    # 答えを書いていなかった（「火を使わずにお湯を沸かす天才的発明」の中身がIH）。
    # ここでも「蚊取り線香」とは書かない。渦巻きの絵も出さない。
    # 出すのは「燃やすと蚊が落ちる草」までにして、正体は動画の中で明かす。
    dict(file='thumb_ep06.png', label='ぐるぐる',
         bg='board', lines=['燃やすと蚊が落ちる', 'この草の正体'],
         fig=('kiku/', 46), face='surprise'),
    dict(file='thumb_ep02.png', label='飛行機',
         bg='clip:plane', lines=['9割が勘違い', '翼の形は関係ない'],
         fig=None, face='surprise'),
    # 実写4本（fridge/2/3/4）を1コマずつ見比べたが、どれも「野菜のアップ」
    # 「海外の業務用ガラス扉」で、親指サイズでは冷蔵庫と読めなかった。
    # 背景はいちばん明るい fridge のまま使い、太い輪郭のアイコンを重ねて
    # 「これは冷蔵庫の話だ」を一目で伝える。
    dict(file='thumb_ep05.png', label='冷蔵庫',
         bg='clip:fridge', lines=['開けっぱなしにしたら', '部屋は涼しくなる？'],
         fig=('icon:fridge', 0), face='surprise'),
    # 冷蔵庫の実写がまだ無いので黒板。届いたら bg='clip:fridge' にする。
    # 20本の実測では 実写13/20・明るい16/20 で、黒板は少数派。
    dict(file='thumb_ep04.png', label='冷蔵庫',
         bg='board', lines=['9割が勘違い', '冷やしてない'],
         fig=('pump/', 40), face='surprise'),
    dict(file='thumb_ep03.png', label='ペンギン',
         bg='clip:peng2', lines=['9割が知らない', '足は0度でも凍らない'],
         fig=None, face='surprise'),
    dict(file='thumb_ep01.png', label='電子レンジ',
         bg='board', lines=['9割が勘違い', '食べ物を温めてない'],
         # 02_collision.png は白い線画で、一覧の親指サイズでは消えていた。
         # 動画で使っている色付きの分子（spin/）に差し替える。
         fig=('spin/', 10), face='surprise'),
]

TOP = 0.055          # 文字の上端（上寄せ。実測は上〜中央が33/40本）
SIZE = 168           # 動画の128より大きい。一覧では親指の大きさで見られる
LH = 1.16            # 行送り（文字の高さに対する倍率）
# カワウソは大きく。一覧の実寸では、図より顔のほうが先に認識される。
# Gemini に人気動画と見比べさせたとき、こちらの強みとして挙がったのが
# 「キャラクターによるブランディング」だった。そこを一番大きく使う。
CHAR = dict(w=0.66, cx=0.70, foot=1.03)


ICE = (140, 210, 245, 255)

def window_icon(w, h):
    """飛行機の窓のアイコン。真ん中のガラスの穴を矢印で指す。

    背景の wing（窓から見た主翼）には穴が映っていないので、
    文字だけだと「この穴」が何を指すか分からない。第5話で冷蔵庫の
    実写が親指サイズで冷蔵庫に見えなかったときと同じ手当て。
    板を敷いて、どんな背景の上でも輪郭が潰れないようにする。
    """
    S = 4
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    W2, H2 = w * S, h * S

    pad = int(W2 * 0.02)
    d.rounded_rectangle((pad, pad, W2 - pad, H2 - pad), radius=int(W2 * 0.08),
                        fill=(255, 255, 255, 238), outline=BLACK, width=int(W2 * 0.012))

    # 窓（角の丸い縦長。旅客機の窓の形）
    ow = max(6, int(W2 * 0.024))
    wx0, wy0 = int(W2 * 0.28), int(H2 * 0.13)
    wx1, wy1 = int(W2 * 0.72), int(H2 * 0.87)
    d.rounded_rectangle((wx0, wy0, wx1, wy1), radius=int(W2 * 0.20),
                        fill=(176, 214, 240, 255), outline=BLACK, width=ow)
    # 内側の枠（ガラスが何枚も入っている感じ）
    m = int(W2 * 0.055)
    d.rounded_rectangle((wx0 + m, wy0 + m, wx1 - m, wy1 - m),
                        radius=int(W2 * 0.155), outline=BLACK, width=max(4, ow // 2))

    # 穴。ここが主役なので大きめの黒丸にする
    cx, cy = (wx0 + wx1) // 2, int(H2 * 0.66)
    # 親指サイズで穴が点にしか見えなかったので大きくする。
    # この穴が見えないと「この穴、わざと」の文字が何も指さない。
    r = int(W2 * 0.082)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLACK)

    # 穴を指す矢印（右から）
    ax0, ax1 = int(W2 * 0.95), cx + int(r * 2.1)
    aw = max(6, int(W2 * 0.040))
    d.line((ax0, cy, ax1, cy), fill=CRIMSON, width=aw)
    hd = int(W2 * 0.072)
    d.polygon([(ax1 - hd, cy), (ax1 + hd // 2, cy - hd * 3 // 4),
               (ax1 + hd // 2, cy + hd * 3 // 4)], fill=CRIMSON)
    return im.resize((w, h), Image.LANCZOS)


def fridge_icon(w, h):
    """一目で「冷蔵庫」と分かる簡易アイコン。実写(iyxtimg不可)の代わりに描く。

    第5話は実写4本を1コマずつ見比べたが、どれも「野菜のアップ」「海外の
    業務用ガラス扉冷蔵庫」で、サムネの親指サイズでは冷蔵庫と読めなかった
    （視聴者コメント相当のAI講評でも同じ指摘）。実写を諦めて、太い輪郭の
    アイコンに切り替える。板を敷いて、どんな背景の上でも潰れないようにする。
    """
    S = 4
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    W2, H2 = w * S, h * S

    # 背景の板（実写の上に乗せても輪郭が潰れないように）
    pad = int(W2 * 0.02)
    d.rounded_rectangle((pad, pad, W2 - pad, H2 - pad), radius=int(W2 * 0.08),
                         fill=(255, 255, 255, 235), outline=BLACK, width=int(W2 * 0.012))

    # 本体
    bx0, by0 = int(W2 * 0.24), int(H2 * 0.10)
    bx1, by1 = int(W2 * 0.76), int(H2 * 0.90)
    ow = max(6, int(W2 * 0.020))
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=int(W2 * 0.035),
                         fill=(250, 250, 252, 255), outline=BLACK, width=ow)

    # 冷凍室と冷蔵室の仕切り線
    split_y = by0 + int((by1 - by0) * 0.32)
    d.line((bx0 + ow, split_y, bx1 - ow, split_y), fill=BLACK, width=ow)

    # 取っ手（縦バー）。両室とも右寄りに1本ずつ
    hx = bx1 - int((bx1 - bx0) * 0.14)
    hw = max(4, int(W2 * 0.012))
    d.rounded_rectangle((hx - hw, by0 + int((split_y - by0) * 0.20),
                          hx + hw, split_y - int((split_y - by0) * 0.18)),
                         radius=hw, fill=BLACK)
    d.rounded_rectangle((hx - hw, split_y + int((by1 - split_y) * 0.10),
                          hx + hw, by1 - int((by1 - split_y) * 0.10)),
                         radius=hw, fill=BLACK)

    # ひんやりを示す水色のギザギザ（雪）を扉のすき間に
    zig_y = split_y
    zx0, zx1 = bx0 + int(W2 * 0.06), hx - int(W2 * 0.05)
    n = 5
    pts = []
    for i in range(n + 1):
        x = zx0 + (zx1 - zx0) * i / n
        y = zig_y + (-1 if i % 2 == 0 else 1) * int(H2 * 0.02)
        pts.append((x, y))
    d.line(pts, fill=ICE, width=max(4, int(W2 * 0.014)), joint='curve')

    im = im.resize((w, h), Image.LANCZOS)
    return im


HOT = (240, 120, 70, 255)

def bath_icon(w, h):
    """一目で「風呂」と分かるアイコン。湯気と、赤く振り切れた温度計を添える。

    第12話の背景に使える実写が手元に無い。第5話で実写の冷蔵庫が親指サイズ
    では冷蔵庫に見えなかったのと同じ理由で、太い輪郭で描いたほうが読める。
    温度計を入れるのは、文字（交通事故の7.5倍）だけだと「なぜ風呂で死ぬのか」
    の手掛かりが画に無いため。熱さが原因だと1枚で分かるようにする。
    """
    S = 4
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    W2, H2 = w * S, h * S
    ow = max(6, int(W2 * 0.020))

    pad = int(W2 * 0.02)
    d.rounded_rectangle((pad, pad, W2 - pad, H2 - pad), radius=int(W2 * 0.08),
                        fill=(255, 255, 255, 235), outline=BLACK, width=int(W2 * 0.012))

    # 湯船（浴槽の断面）。下半分に置いて、上を湯気に空ける
    # 一覧の実寸（幅160px）で見ると、湯船が小さくて板の白が目立っていた。
    # 湯船を広げて、白い余白を減らす。
    tx0, tx1 = int(W2 * 0.11), int(W2 * 0.89)
    ty0, ty1 = int(H2 * 0.47), int(H2 * 0.86)
    d.rounded_rectangle((tx0, ty0, tx1, ty1), radius=int(W2 * 0.10),
                        fill=(250, 250, 252, 255), outline=BLACK, width=ow)

    # 湯。ふちより少し下まで入れて、水面を波線で描く
    wy = ty0 + int((ty1 - ty0) * 0.26)
    d.rounded_rectangle((tx0 + ow, wy, tx1 - ow, ty1 - ow), radius=int(W2 * 0.08),
                        fill=(250, 150, 110, 255))
    pts = []
    n = 7
    for i in range(n + 1):
        x = tx0 + ow + (tx1 - tx0 - 2 * ow) * i / n
        pts.append((x, wy + (-1 if i % 2 == 0 else 1) * int(H2 * 0.012)))
    d.line(pts, fill=BLACK, width=max(4, int(W2 * 0.012)), joint='curve')

    # 脚
    for fx in (tx0 + int((tx1 - tx0) * 0.16), tx1 - int((tx1 - tx0) * 0.16)):
        d.rounded_rectangle((fx - ow, ty1, fx + ow * 2, ty1 + int(H2 * 0.05)),
                            radius=ow, fill=BLACK)

    # 湯気。3本の曲線を上へ
    for k, sx in enumerate((0.34, 0.50, 0.66)):
        x = int(W2 * sx)
        top = int(H2 * (0.16 + 0.04 * (k % 2)))
        cur = []
        steps = 14
        for i in range(steps + 1):
            t = i / steps
            y = ty0 - int((ty0 - top) * t)
            cur.append((x + int(W2 * 0.035 * _m.sin(t * 3.4 * _m.pi)), y))
        d.line(cur, fill=(150, 150, 158, 255),
               width=max(4, int(W2 * 0.026)), joint='curve')

    # 温度計。赤が上まで振り切れている
    mx = int(W2 * 0.82)
    my0, my1 = int(H2 * 0.09), int(H2 * 0.42)
    r = int(W2 * 0.075)
    d.rounded_rectangle((mx - r // 2, my0, mx + r // 2, my1),
                        radius=r // 2, fill=(255, 255, 255, 255),
                        outline=BLACK, width=ow)
    d.ellipse((mx - r, my1 - r // 2, mx + r, my1 + r * 3 // 2),
              fill=HOT, outline=BLACK, width=ow)
    d.rounded_rectangle((mx - r // 4, my0 + ow * 2, mx + r // 4, my1),
                        radius=r // 4, fill=HOT)

    im = im.resize((w, h), Image.LANCZOS)
    return im


def figure(spec):
    name, idx = spec
    if name == 'icon:fridge':
        return fridge_icon(680, 680)
    if name == 'icon:window':
        return window_icon(560, 700)
    if name == 'icon:bath':
        return bath_icon(680, 680)
    if name.endswith('/'):
        fs = render.clip_frames(name.rstrip('/')) if False else None
        d = os.path.join(render.CLIP_DIR, name.rstrip('/'))
        fs = sorted(os.listdir(d))
        return Image.open(os.path.join(d, fs[min(idx, len(fs) - 1)])).convert('RGBA')
    return render.load(name)


def background(ep):
    """実写があれば敷いて明るくする。1コマ目の実測で明るい16／暗い4だった。"""
    spec = ep.get('bg', 'board')
    if not spec.startswith('clip:'):
        return render.bg_board().copy()
    d = os.path.join(render.CLIP_DIR, spec.split(':', 1)[1])
    fs = sorted(os.listdir(d))
    src = Image.open(os.path.join(d, fs[len(fs) // 3])).convert('RGBA')
    # 縦画面を埋めるように、中央を切って引き伸ばす
    k = max(W / src.width, H / src.height)
    src = src.resize((int(src.width * k), int(src.height * k)), Image.LANCZOS)
    src = src.crop(((src.width - W) // 2, 0, (src.width + W) // 2, H))
    return src


def thumb(ep):
    im = background(ep)

    # 図は中ほどに大きく置く。文字と重ならない高さに収める
    fig = figure(ep['fig']) if ep.get('fig') else None
    if fig is not None:
        tw = int(W * 0.90)
        th = int(fig.height * tw / fig.width)
        cap = int(H * 0.26)
        if th > cap:
            th = cap; tw = int(fig.width * th / fig.height)
        fig = fig.resize((tw, th), Image.LANCZOS)
        im.alpha_composite(fig, (int(W * 0.46) - tw // 2, int(H * 0.44) - th // 2))

    # カワウソ。誰のチャンネルか一覧で分かるように、必ず入れる
    ch = render.load(render.FACE_FILES[ep['face']])
    if ch is not None:
        cw = int(W * CHAR['w'])
        chh = int(ch.height * cw / ch.width)
        ch = ch.resize((cw, chh), Image.LANCZOS)
        im.alpha_composite(ch, (int(W * CHAR['cx']) - cw // 2,
                                int(H * CHAR['foot']) - chh))

    d = ImageDraw.Draw(im)
    # 話のラベル。小さく上に置く。何の回かが一覧で分かる
    lf = render.font(78)
    lw = d.textlength(ep['label'], font=lf)
    render.plate(im, render.rich_box(W // 2, int(H * 0.022), ep['label'], lf, 5, True))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    render.rich(ImageDraw.Draw(lay), W // 2, int(H * 0.022), ep['label'], lf,
                MUSTARD, MUSTARD, 5, BLACK, True)
    im.alpha_composite(lay)

    # 本文2行。1行ずつ幅に収まるまで縮める
    y = int(H * TOP) + int(SIZE * 0.95)
    for i, ln in enumerate(ep['lines']):
        size = SIZE
        while size > 90 and d.textlength(ln, font=render.font(size)) > W * 0.88:
            size -= 6
        fnt = render.font(size)
        col = MUSTARD if i == len(ep['lines']) - 1 else CHALK
        render.plate(im, render.rich_box(W // 2, y, ln, fnt, 9, True))
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        render.rich(ImageDraw.Draw(lay), W // 2, y, ln, fnt, col, MUSTARD, 9, BLACK, True)
        im.alpha_composite(lay)
        y += int(size * LH)
    return im.convert('RGB')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for ep in EPS:
        im = thumb(ep)
        p = os.path.join(OUT, ep['file'])
        im.save(p)
        print('%s  %dx%d  「%s」' % (ep['file'], *im.size, '／'.join(ep['lines'])))
