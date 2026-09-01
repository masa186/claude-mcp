"""参考動画の字幕帯の変化点を見つけて、1枚につき1コマだけ切り出す。

    python3 tools/subs.py <動画> <出力先> [上端 下端]

Gemini に読ませると取り漏らすので、こちらで全部拾うために作った。
"""
import subprocess, sys, os, numpy as np

FF = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
if not os.path.exists(FF):
    FF = 'ffmpeg'


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
    scan(sys.argv[1], sys.argv[2],
         float(sys.argv[3]) if len(sys.argv) > 3 else 0.63,
         float(sys.argv[4]) if len(sys.argv) > 4 else 0.77)
