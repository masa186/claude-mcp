"""書き出す前に、板の文字がはみ出さないか・フォントに無い字が無いかを見る。

書き出してから気づくと1本まるごと（10〜25分）無駄になる。
第11話で丸数字が全部□になり、第12話で板の文字が45px はみ出していた。
どちらも書き出す前にここで捕まえられる。

  python3 checkfit.py ep12.py
"""
import sys, re, ast
from PIL import ImageDraw, Image
import render, style

def check(path):
    src = open(path, encoding='utf-8').read()
    d = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    a = render.board_area('board')
    w = a[2] - a[0]
    bad = 0

    # 板の文字。ast で読むので \n がそのまま改行になる
    for m in re.finditer(r"text=('(?:[^'\\]|\\.)*')\s*,\s*size=(\d+)", src):
        txt = ast.literal_eval(m.group(1))
        sz = int(m.group(2))
        for line in re.sub(r'[{}]', '', txt).split('\n'):
            px = d.textlength(line, font=style.font(sz))
            if px > w:
                print('  ★はみ出す size%-4d %5.0f>%d  %s' % (sz, px, w, line))
                bad += 1

    # フォントに無い字
    miss = set()
    for m in re.finditer(r"('(?:[^'\\]|\\.)*')", src):
        try:
            t = ast.literal_eval(m.group(1))
        except Exception:
            continue
        if not isinstance(t, str):
            continue
        for face, nm in ((style.GOTHIC, '図'), (style.SERIF, '板')):
            x = style.missing(t, face)
            if x:
                miss.add((nm, x))
    for nm, x in sorted(miss):
        print('  ★%sのフォントに無い字: %s' % (nm, x))
        bad += 1

    print('%s → %s' % (path, 'OK' if bad == 0 else '%d件' % bad))
    return bad

if __name__ == '__main__':
    sys.exit(1 if sum(check(p) for p in sys.argv[1:]) else 0)
