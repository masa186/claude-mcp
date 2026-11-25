"""参考動画の字幕帯の変化点を見つけて、1枚につき1コマだけ切り出す。

    python3 tools/subs.py <動画> <出力先> [上端 下端]

Gemini に読ませると取り漏らすので、こちらで全部拾うために作った。
"""
import subprocess, sys, os, numpy as np

FF = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
if not os.path.exists(FF):
    FF = 'ffmpeg'


def find_band(src, fps=2, w=200):
    """字幕帯が縦のどこにあるかを自動で探す。

    動画ごとに高さが違う（47%のものも70%のものもある）ので、
    固定値で切ると丸ごと取り落とす。

    顔カメラも明るくて動くので、明るさだけでは区別できない。
    **字は「振り切った明るい点のすぐ横に黒フチがある」**のが特徴なので、
    それを数える。肌や空にはこの並びが出ない。
    """
    probe = subprocess.run([FF, '-v', 'error', '-i', src, '-vf', f'scale={w}:-1',
        '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
        capture_output=True).stdout
    h = len(probe) // (w * 3)
    raw = subprocess.run([FF, '-v', 'error', '-i', src, '-vf',
        f'fps={fps},scale={w}:-1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
        capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    a = np.frombuffer(raw[:n*w*h*3], np.uint8).reshape(n, h, w, 3).astype(np.float32)
    mx = a.max(axis=3)
    bright = mx > 180
    dark = mx < 60
    # 横に±4px 以内に黒フチがあるか
    near = np.zeros_like(dark)
    for k in range(1, 5):
        near[:, :, k:] |= dark[:, :, :-k]
        near[:, :, :-k] |= dark[:, :, k:]
    txt = (bright & near).mean(axis=2)            # コマ×行
    txt = txt[:, :]
    score = ((txt > 0.02) & (txt < 0.45)).mean(axis=0)
    score[:int(h*0.22)] = 0                       # 上の固定タイトルを除く
    score[int(h*0.88):] = 0                       # 下の黒帯を除く
    win = max(4, int(h*0.06))
    best, bi = -1, int(h*0.63)
    for i in range(int(h*0.22), int(h*0.88)-win):
        v = score[i:i+win].sum()
        if v > best:
            best, bi = v, i
    lo = max(0.22, bi/h - 0.02)
    return round(lo, 3), round(min(0.88, lo + win/h + 0.045), 3)


def scan(src, out, lo=0.63, hi=0.77, fps=10, w=180):
    probe = subprocess.run([FF, '-v', 'error', '-i', src, '-vf',
        f'crop=iw:ih*{hi-lo}:0:ih*{lo},scale={w}:-1', '-frames:v', '1',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    hc = len(probe) // (w * 3)
    raw = subprocess.run([FF, '-v', 'error', '-i', src, '-vf',
        f'fps={fps},crop=iw:ih*{hi-lo}:0:ih*{lo},scale={w}:-1',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    n = len(raw) // (w * hc * 3)
    a = np.frombuffer(raw[:n*w*hc*3], np.uint8).reshape(n, hc, w, 3).astype(np.float32)
    # 赤(255,59,48)は輝度116しかなく、明るさで見ると落ちる。
    # 字の色は白・水色・赤・黄・緑・橙どれも「どれか1色が振り切っている」ので
    # RGBの最大チャンネルで見る。
    m = (a.max(axis=3) > 175).astype(np.float32)
    d = np.abs(np.diff(m, axis=0)).mean(axis=(1, 2))
    th = max(0.004, np.percentile(d, 88))
    cut = [0] + [i+1 for i, v in enumerate(d) if v > th] + [n]
    segs = []
    for i in range(len(cut)-1):
        a0, b0 = cut[i], cut[i+1]
        if b0 - a0 < 3:                       # 0.3秒未満は無視
            continue
        if m[a0:b0].mean() < 0.0015:          # 字が無い区間は捨てる
            continue
        segs.append((a0/fps, b0/fps))
    os.makedirs(out, exist_ok=True)
    print(f"{os.path.basename(src)}  {n/fps:.1f}秒  字幕 {len(segs)}枚  "
          f"({len(segs)/(n/fps):.2f}枚/秒)")
    for i, (s, e) in enumerate(segs):
        subprocess.run([FF, '-v', 'error', '-ss', f'{(s+e)/2:.2f}', '-i', src,
            '-frames:v', '1', '-vf',
            f'crop=iw:ih*{hi-lo+0.01}:0:ih*{lo-0.005},scale=430:-1',
            f'{out}/{i:02d}.png', '-y'])
        print(f"  {i:02d}  {s:5.1f}〜{e:5.1f}秒 ({e-s:.1f}s)")
    return segs


if __name__ == '__main__':
    if len(sys.argv) > 4:
        lo, hi = float(sys.argv[3]), float(sys.argv[4])
    else:
        lo, hi = find_band(sys.argv[1])
        print(f"字幕帯を自動検出: {lo*100:.1f}%〜{hi*100:.1f}%")
    scan(sys.argv[1], sys.argv[2], lo, hi)
