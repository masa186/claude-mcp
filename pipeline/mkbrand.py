"""チャンネルのアイコンとバナーを書き出す。

外から探してきた画像を使うと、色と書体が動画とズレる。同じ render.py の
色（黒板の緑・チョークの白・からしの黄）と同じ書体で作れば、
サムネ・アイコン・バナーが一続きに見える。ここが揃っていないと、
おすすめに並んだときに同じチャンネルだと気づかれない。

  python3 mkbrand.py

出てくるもの（brand/）:
  icon.png        800x800    YouTube・TikTok 共通のアイコン（丸く切られる前提）
  banner.png      2560x1440  YouTube のバナー
  banner_check.png            バナーの安全域を赤枠で示した確認用
"""
import os
from PIL import Image, ImageDraw
import render
from render import BOARD, CHALK, MUSTARD, WOOD, BLACK

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'brand')

NAME = 'カワウソ先生の黒板'
SUB = '身の回りの仕組みを 40秒で'

# YouTube のバナーは端末ごとに見える範囲が違う。2560x1440 で上げて、
# どの端末でも必ず見えるのは中央の 1546x423 だけ（テレビは全面、
# スマホはこの中央だけ）。文字はここから絶対に出さない。
BANNER = (2560, 1440)
SAFE = (1546, 423)


def board_bg(w, h):
    """動画と同じ黒板。中央がわずかに明るいのも同じ作り。"""
    im = Image.new('RGB', (w, h), BOARD[:3])
    d = ImageDraw.Draw(im, 'RGBA')
    cx, cy = w // 2, int(h * 0.44)
    for i in range(28, 0, -1):
        a = int(9 * (i / 28))
        rx, ry = int(w * 0.10 * i / 6), int(h * 0.12 * i / 6)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(255, 255, 255, a))
    # チョークの粉っぽさ。真っ平らだと板に見えない
    for i in range(h // 3):
        y = i * 3
        d.line([(0, y), (w, y)], fill=(255, 255, 255, 3))
    return im


def icon(size=800):
    """アイコン。丸く切られるので、顔を中央の円の中だけに収める。

    円の外は見えないが、四角のまま出す場所（検索結果など）もあるので
    背景は端まで塗る。
    """
    im = board_bg(size, size)
    face = render.load('char_proud.png')
    # 胸から上だけを切り出す。全身を入れると顔が小さすぎて誰か分からない
    # 上の余白（額の上）は詰める。丸く切られるので、顔が円に対して
     # 小さいと一覧で誰か分からなくなる
    crop = face.crop((int(face.width * 0.09), int(face.height * 0.045),
                      int(face.width * 0.91), int(face.height * 0.395)))
    k = (size * 1.02) / crop.width
    crop = crop.resize((int(crop.width * k), int(crop.height * k)), Image.LANCZOS)
    # 切った下端をぼかして黒板に溶かす。そのまま貼ると胸のあたりで
    # 白い帯がまっすぐ切れて、切り抜き損じに見える
    a = crop.getchannel('A')
    fade = Image.new('L', crop.size, 255)
    fd = ImageDraw.Draw(fade)
    h = int(crop.height * 0.16)
    for i in range(h):
        y = crop.height - h + i
        fd.line([(0, y), (crop.width, y)], fill=int(255 * (1 - i / h) ** 1.4))
    crop.putalpha(Image.composite(a, Image.new('L', crop.size, 0), fade))
    im.paste(crop, (size // 2 - crop.width // 2, int(size * 0.09)), crop)
    return im


def banner():
    im = board_bg(*BANNER)
    W, H = BANNER
    sx, sy = (W - SAFE[0]) // 2, (H - SAFE[1]) // 2

    # 木枠。動画の黒板と同じ縁取りにする
    d = ImageDraw.Draw(im)
    m = 26
    d.rectangle([0, 0, W - 1, m], fill=WOOD[:3])
    d.rectangle([0, H - m, W - 1, H - 1], fill=WOOD[:3])

    # カワウソは安全域の右外。スマホでは見えないが、
    # テレビ・PCでは見える「おまけ」の位置に置く
    ch = render.load('char_arms_closed.png')
    k = (H * 0.86) / ch.height
    ch = ch.resize((int(ch.width * k), int(ch.height * k)), Image.LANCZOS)
    im.paste(ch, (sx + SAFE[0] - int(ch.width * 0.32), H - ch.height), ch)

    # 文字は安全域の中だけ。左寄せにしてカワウソと衝突させない
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    size = 150
    while dl.textlength(NAME, font=render.font(size)) > SAFE[0] * 0.72:
        size -= 4
    ny = sy + int(SAFE[1] * 0.20)
    render.rich(dl, sx + int(SAFE[0] * 0.045), ny, NAME, render.font(size),
                CHALK, MUSTARD, stroke=7, scol=BLACK)
    render.rich(dl, sx + int(SAFE[0] * 0.05), ny + int(size * 1.28), SUB,
                render.font(int(size * 0.42)), CHALK, MUSTARD, stroke=5, scol=BLACK)
    im.paste(lay, (0, 0), lay)
    return im


def check(im):
    """安全域を赤枠で描いた確認用。上げるのはこちらではない。"""
    c = im.copy()
    d = ImageDraw.Draw(c)
    W, H = BANNER
    sx, sy = (W - SAFE[0]) // 2, (H - SAFE[1]) // 2
    d.rectangle([sx, sy, sx + SAFE[0], sy + SAFE[1]], outline=(255, 60, 60), width=6)
    d.text((sx + 10, sy - 46), 'スマホでも見える範囲（ここから文字を出さない）',
           font=render.font(34), fill=(255, 90, 90))
    return c


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    ic = icon()
    ic.save(os.path.join(OUT, 'icon.png'))
    bn = banner()
    bn.save(os.path.join(OUT, 'banner.png'))
    check(bn).save(os.path.join(OUT, 'banner_check.png'))
    print('brand/icon.png        %dx%d' % ic.size)
    print('brand/banner.png      %dx%d' % bn.size)
    print('brand/banner_check.png（安全域の確認用。上げない）')
