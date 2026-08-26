"""書体と色を1箇所にまとめる。

render.py / mkanim.py / mkpng.py が別々にフォントを選んでいると、
黒板の文字と図の中の文字で書体がズレる。ここを唯一の出どころにする。

書体は Noto Serif CJK JP Bold（明朝）。
ゴシックの極太は「量産系まとめ動画」の見た目に直結するので、
教養寄りの落ち着き（高級感）を出すために明朝に振っている。
明朝は横画が細いぶん、フチを1px厚くして潰れないようにしてある。
"""
import os
from PIL import ImageFont


def pick(*cands):
    for p in cands:
        if os.path.exists(p if isinstance(p, str) else p[0]):
            return p if isinstance(p, tuple) else (p, 0)
    return None


# (パス, ttcの中の何番目か)。Noto Serif CJK の ttc は 0 番が JP。
SERIF = pick(('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc', 0),
             ('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc', 0),
             ('/usr/share/fonts/opentype/mplus/Mplus1-Black.otf', 0),
             ('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf', 0))

# 図の中の細かい注記だけは、小さくても読めるゴシックを使う。
GOTHIC = pick(('/usr/share/fonts/opentype/mplus/Mplus1-Bold.otf', 0),
              ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 0),
              ('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf', 0))

if SERIF is None:
    raise SystemExit('日本語フォントがありません:\n'
                     '  apt-get install fonts-noto-cjk fonts-mplus')

_cache = {}


def font(size, face=None):
    face = face or SERIF
    key = (face, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(face[0], size, index=face[1])
    return _cache[key]

def missing(text, face=None):
    """そのフォントに無い字を返す。豆腐（□）で出る前に気づくため。

    第11話で「①②③」が全部 □ になった。Mplus1-Bold（図の注釈用）に
    丸数字が入っていない。書き出してから気づくと1本まるごと無駄になる。
    """
    from PIL import ImageFont
    f = font(40, face or GOTHIC)
    try:
        cmap = f.font.getbestcmap() if hasattr(f, 'font') else None
    except Exception:
        cmap = None
    if not cmap:
        return ''
    return ''.join(sorted(set(c for c in text
                              if ord(c) not in cmap and not c.isspace())))
