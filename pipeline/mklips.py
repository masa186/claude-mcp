"""口を開けた絵を、いまある絵から作る。

もらった8枚には「口だけが違う組み合わせ」が無かった。
char_point と char_point_open は名前が対に見えて、実際は顔の向きも腕も違う
別の絵で、切り替えると口ではなく頭が跳ねる。

ただし正面向きの絵（explain / proud / serious / surprise / blink / arms）は、
どれも同じ顔の上に目と口だけを描き替えたものだった。マズル・ヒゲ・あごの線は
1pxもズレていない。つまり口のまわりの四角を丸ごと入れ替えれば、
描き足しも塗りつぶしもせずに口だけを差し替えられる。

開いた口の絵は char_arms から借りる。作者が描いた口をそのまま使うので、
線の太さも色も浮かない。

  python3 mklips.py            assets/char_*_mouth.png を書き出す
  python3 mklips.py --sheet    閉じ／開きの見比べを出す
"""
import os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')

# 口のまわりの四角（原寸座標）。図を拡大して目で測った。
# 左右はヒゲの内側まで、上は鼻の下、下はあごの線の手前。
# ここを丸ごと差し替える。ヒゲとあごの線も一緒に持ってくるので継ぎ目が出ない。
BOX = (322, 398, 608, 532)

SRC = 'char_arms.png'                   # 開いた口の出どころ
TARGETS = ['char_explain', 'char_proud', 'char_serious', 'char_surprise',
           'char_blink']
# char_point は顔の向きが違うので対象外（自動で弾かれる）

# 正面顔かどうかの確認に使う。ここがズレている絵は差し替えてはいけない
CHECK = (322, 398, 608, 412)            # 鼻の下の帯（口が無い場所）


SEARCH = 30                             # 顔の位置ズレを探す範囲（px）
THR = 6.0                               # これ以上ズレていたら別の顔とみなす


def offset(src, tgt):
    """鼻の下の帯が一番よく重なる位置を探す。絵によって顔が数px動いている。
    合わないまま貼ると、ヒゲやあごの線が二重になる。"""
    pa = np.asarray(src.crop(CHECK).convert('RGB'), dtype=np.float64)
    best = None
    for dy in range(-SEARCH, SEARCH+1):
        for dx in range(-SEARCH, SEARCH+1):
            b = (CHECK[0]+dx, CHECK[1]+dy, CHECK[2]+dx, CHECK[3]+dy)
            d = float(np.abs(pa - np.asarray(tgt.crop(b).convert('RGB'),
                                             dtype=np.float64)).mean())
            if best is None or d < best[0]:
                best = (d, dx, dy)
    return best


def build(verbose=True):
    src = Image.open(os.path.join(ASSETS, SRC)).convert('RGBA')
    patch = src.crop(BOX)
    made, skipped = [], []
    for name in TARGETS:
        p = os.path.join(ASSETS, name + '.png')
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGBA')
        if im.size != src.size:
            skipped.append(name + '(大きさ違い)'); continue
        d, dx, dy = offset(src, im)
        if d > THR:
            skipped.append('%s(顔が別物 差%.1f)' % (name, d)); continue
        out = im.copy()
        out.paste(patch, (BOX[0]+dx, BOX[1]+dy))   # 差し替え（合成ではなく置き換え）
        f = name + '_mouth.png'
        out.save(os.path.join(ASSETS, f))
        made.append(f + ('' if (dx, dy) == (0, 0) else '[%+d%+d]' % (dx, dy)))
    if verbose:
        print('  口を開けた絵 %d枚: %s' % (len(made), ' '.join(made)))
        if skipped:
            print('  顔の作りが違うので飛ばした: ' + ' '.join(skipped))
    return made


def sheet(path=None):
    path = path or os.path.join(HERE, 'lips_sheet.png')
    tiles = []
    for name in TARGETS:
        for suf in ('', '_mouth'):
            f = os.path.join(ASSETS, name + suf + '.png')
            if not os.path.exists(f):
                continue
            c = Image.open(f).convert('RGBA').crop((250, 230, 700, 600))
            tiles.append(c.resize((430, int(c.height * 430 / c.width)), Image.LANCZOS))
    if not tiles:
        return
    H = max(t.height for t in tiles)
    sh = Image.new('RGB', (2*436, ((len(tiles)+1)//2)*(H+6)), (250, 248, 244))
    for i, t in enumerate(tiles):
        bg = Image.new('RGBA', (430, H), (250, 248, 244, 255)); bg.alpha_composite(t)
        sh.paste(bg.convert('RGB'), ((i % 2)*436+3, (i//2)*(H+6)+3))
    sh.save(path); print('  ' + path)


if __name__ == '__main__':
    print('口を開けた絵を作成中...')
    build()
    if '--sheet' in sys.argv:
        sheet()
