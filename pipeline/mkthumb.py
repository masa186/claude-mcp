"""サムネイルを書き出す。

ショートはフィードでは1コマ目が出るのでサムネは効かないが、
チャンネルの一覧と検索結果ではサムネが出る。1本見た人が2本目に行くかは
そこで決まるので、動画と同じ色・同じ書体で揃えておく。

伸びているショートのサムネそのものは取れなかった（i.ytimg.com が
組織のポリシーで遮断されている）。代わりに、同じ40本で測った
「画面の文字の置き方」をそのまま当てる（docs/text.md）:
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
from render import CHALK, MUSTARD, BLACK

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'brand')

W, H = 1080, 1920

# 各話。fig は clips/ の連番か assets/ の1枚
EPS = [
    # 図は「色が付いていて太いもの」を選ぶ。線画は親指の大きさでは消える。
    dict(file='thumb_ep02.png', label='飛行機',
         lines=['翼の形は', '関係ない'],
         fig=('aoa/', 60), face='surprise'),
    dict(file='thumb_ep01.png', label='電子レンジ',
         lines=['食べ物を', '温めてない'],
         fig=('02_collision.png', None), face='surprise'),
]

TOP = 0.055          # 文字の上端（上寄せ。実測は上〜中央が33/40本）
SIZE = 190           # 動画の128より大きい。一覧では親指の大きさで見られる
LH = 1.16            # 行送り（文字の高さに対する倍率）
# カワウソは大きく。一覧の実寸では、図より顔のほうが先に認識される。
# Gemini に人気動画と見比べさせたとき、こちらの強みとして挙がったのが
# 「キャラクターによるブランディング」だった。そこを一番大きく使う。
CHAR = dict(w=0.66, cx=0.70, foot=1.03)


def figure(spec):
    name, idx = spec
    if name.endswith('/'):
        fs = render.clip_frames(name.rstrip('/')) if False else None
        d = os.path.join(render.CLIP_DIR, name.rstrip('/'))
        fs = sorted(os.listdir(d))
        return Image.open(os.path.join(d, fs[min(idx, len(fs) - 1)])).convert('RGBA')
    return render.load(name)


def thumb(ep):
    im = render.bg_board().copy()

    # 図は中ほどに大きく置く。文字と重ならない高さに収める
    fig = figure(ep['fig'])
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
