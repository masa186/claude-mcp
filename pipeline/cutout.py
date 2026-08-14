"""
背景を抜いて透過PNGにする
==========================
「透過したつもりが、チェック柄が画像に焼き込まれている」という一番よくある事故を
自動で直す。白一色の背景にも使える。

  python3 cutout.py 入力1.png 入力2.png ...            # 抜くだけ
  python3 cutout.py --name in.png:char_explain.png ... # 抜いてリネームして assets/ へ

やっていること:
  1. 画像の四隅から色をサンプルして、背景色（チェック柄なら2色、白背景なら1色）を推定
  2. 縁から塗りつぶしで背景をたどる（キャラの内側にある白は消さない）
  3. 境界を1px ぼかしてギザギザを消す
"""
import os, sys, argparse
import numpy as np
from PIL import Image, ImageFilter

HERE   = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')


def guess_bg_colors(a):
    """四隅40x40からよく出る色を最大2つ拾う。"""
    h, w = a.shape[:2]
    k = max(8, min(60, w//14))
    corners = np.concatenate([
        a[:k, :k].reshape(-1, 3), a[:k, -k:].reshape(-1, 3),
        a[-k:, :k].reshape(-1, 3), a[-k:, -k:].reshape(-1, 3)])
    q = (corners // 12 * 12).astype(np.int32)
    keys, counts = np.unique(q[:, 0]*65536 + q[:, 1]*256 + q[:, 2], return_counts=True)
    order = np.argsort(-counts)
    out = []
    for i in order[:4]:
        if counts[i] / len(q) < 0.06:
            break
        v = keys[i]
        out.append(np.array([v // 65536, (v // 256) % 256, v % 256], dtype=np.int32))
        if len(out) == 2:
            break
    return out


def flood_bg(mask_bgish):
    """縁から連結している背景だけを True にする（キャラ内部の白は残す）。"""
    h, w = mask_bgish.shape
    out = np.zeros((h, w), dtype=bool)
    stack = []
    for x in range(w):
        if mask_bgish[0, x]:    stack.append((0, x))
        if mask_bgish[h-1, x]:  stack.append((h-1, x))
    for y in range(h):
        if mask_bgish[y, 0]:    stack.append((y, 0))
        if mask_bgish[y, w-1]:  stack.append((y, w-1))

    # 走査線方式（再帰なし・十分速い）
    while stack:
        y, x = stack.pop()
        if out[y, x] or not mask_bgish[y, x]:
            continue
        xl = x
        while xl > 0 and mask_bgish[y, xl-1] and not out[y, xl-1]:
            xl -= 1
        xr = x
        while xr < w-1 and mask_bgish[y, xr+1] and not out[y, xr+1]:
            xr += 1
        out[y, xl:xr+1] = True
        for ny in (y-1, y+1):
            if 0 <= ny < h:
                seg = mask_bgish[ny, xl:xr+1] & ~out[ny, xl:xr+1]
                idx = np.flatnonzero(seg)
                for i in idx:
                    stack.append((ny, xl + int(i)))
    return out


def largest_blob(mask):
    """True の連結成分のうち一番大きいものだけ残す。取り残しのゴミを一掃する。"""
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    best, best_n = None, 0
    ys, xs = np.where(mask)
    for sy, sx in zip(ys, xs):
        if seen[sy, sx]:
            continue
        comp = np.zeros((h, w), dtype=bool)
        stack, n = [(sy, sx)], 0
        while stack:
            y, x = stack.pop()
            if seen[y, x] or not mask[y, x]:
                continue
            xl = x
            while xl > 0 and mask[y, xl-1] and not seen[y, xl-1]:
                xl -= 1
            xr = x
            while xr < w-1 and mask[y, xr+1] and not seen[y, xr+1]:
                xr += 1
            seen[y, xl:xr+1] = True
            comp[y, xl:xr+1] = True
            n += xr - xl + 1
            for ny in (y-1, y+1):
                if 0 <= ny < h:
                    seg = mask[ny, xl:xr+1] & ~seen[ny, xl:xr+1]
                    for i in np.flatnonzero(seg):
                        stack.append((ny, xl + int(i)))
        if n > best_n:
            best, best_n = comp, n
    return best if best is not None else mask


def cutout(path, tol=26):
    im = Image.open(path).convert('RGB')
    a = np.array(im).astype(np.int32)
    bgs = guess_bg_colors(a)
    if not bgs:
        print('  ! 背景色を推定できませんでした: ' + os.path.basename(path))
        return None

    bgish = np.zeros(a.shape[:2], dtype=bool)
    for c in bgs:
        bgish |= (np.abs(a - c).max(axis=2) <= tol)

    bg = flood_bg(bgish)
    keep = largest_blob(~bg)          # 取り残しのゴミを一掃
    alpha = np.where(keep, 255, 0).astype(np.uint8)

    out = Image.fromarray(np.dstack([np.array(im), alpha]), 'RGBA')
    # 境界を少しだけぼかしてギザギザを取る
    al = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(0.8))
    al = al.point(lambda v: 0 if v < 96 else (255 if v > 190 else int((v-96)*255/94)))
    out.putalpha(al)
    return out, len(bgs), (alpha == 0).mean()


def report(images):
    """5枚のキャラの大きさ・位置が揃っているか確認する。"""
    print('\n--- 5枚の位置合わせ ---')
    print('%-22s %-13s %-9s %s' % ('ファイル', '中身の幅x高さ', '顔の高さ', '判定'))
    rows = []
    for name, im in images:
        al = np.array(im.getchannel('A'))
        ys, xs = np.where(al > 24)
        if not len(xs):
            continue
        bw, bh = xs.max()-xs.min()+1, ys.max()-ys.min()+1
        rows.append((name, bw, bh, ys.min(), im.height))
    if not rows:
        return
    hs = [r[2] for r in rows]
    med = sorted(hs)[len(hs)//2]
    for name, bw, bh, top, H in rows:
        d = (bh - med) / med * 100
        mark = 'OK' if abs(d) < 4 else ('やや大きい +%.0f%%' % d if d > 0 else 'やや小さい %.0f%%' % d)
        print('%-22s %-13s %-9s %s' % (name, '%dx%d' % (bw, bh),
                                       '%.0f%%' % (top/H*100), mark))
    print('\n※ 高さが±4%以内なら、話ごとにキャラが伸縮して見えることはありません。')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+', help='入力PNG。--name なら in.png:出力名.png')
    ap.add_argument('--tol', type=int, default=26, help='背景色の許容差（既定26）')
    ap.add_argument('--name', action='store_true', help='in.png:out.png 形式で受け取る')
    a = ap.parse_args()

    os.makedirs(ASSETS, exist_ok=True)
    done = []
    for spec in a.inputs:
        src, _, dst = spec.partition(':') if a.name else (spec, '', '')
        dst = dst or os.path.basename(src)
        r = cutout(src, a.tol)
        if r is None:
            continue
        im, ncol, ratio = r
        p = os.path.join(ASSETS, dst)
        im.save(p)
        print('  %-22s 背景%d色  透過 %.0f%%  -> assets/%s' % (
            os.path.basename(src)[:20], ncol, ratio*100, dst))
        done.append((dst, im))

    report(done)


if __name__ == '__main__':
    main()
