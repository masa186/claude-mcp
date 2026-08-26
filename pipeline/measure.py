"""書き出した動画の「動き・カット・埋まり」を測る。

    python3 measure.py ep12.mp4 [ep10.mp4 ...]

参考チャンネルと同じ物差しで並べたいので、測り方は docs/reference.md に
書いた手順に合わせてある。

  動きの量  135x240 に落として、隣り合うコマの平均絶対差（MAE）の中央値。
            大きいほど画が動いている。化け学の参考2本は 11.55 と 高め。
  カット    その差が 18 を超えたコマを切り替わりと見なす。秒/カットで出す。
  埋まり    そのコマの中央値の色から 60 以上離れた画素の割合。
            黒板の余白が多いと下がる。

  ※ 埋まりは必ず黒の上に重ねてから測る。convert('L') は透明を捨てるので、
     アルファ付きのまま測ると余白まで「埋まっている」ことになる。
"""
import os, sys, subprocess
import numpy as np
import imageio_ffmpeg as ie

W, H = 135, 240
CUT = 18          # この値を超えた差を「切り替わり」と見なす
FILL = 60         # 中央値の色からこれだけ離れたら「何か描いてある」


def frames(path):
    ff = ie.get_ffmpeg_exe()
    p = subprocess.Popen(
        [ff, '-v', 'error', '-i', path, '-vf', f'scale={W}:{H}',
         '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
        stdout=subprocess.PIPE)
    n = W * H
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W).astype(np.int16)
    p.stdout.close(); p.wait()


def measure(path):
    fs = list(frames(path))
    if len(fs) < 2:
        raise SystemExit(f'{path}: コマが読めない')
    d = np.array([np.abs(fs[i] - fs[i - 1]).mean() for i in range(1, len(fs))])
    fill = np.array([(np.abs(f - np.median(f)) > FILL).mean() for f in fs])
    cuts = int((d > CUT).sum())
    sec = len(fs) / 30.0
    return dict(尺=sec, コマ=len(fs), 動き=float(np.median(d)),
                カット=cuts, 秒每カット=sec / cuts if cuts else float('inf'),
                埋まり=float(fill.mean()) * 100)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        m = measure(p)
        print(f"{os.path.basename(p):12s} {m['尺']:5.1f}秒 "
              f"動き {m['動き']:5.2f}  カット {m['カット']:3d}本 "
              f"{m['秒每カット']:4.2f}秒/カット  埋まり {m['埋まり']:4.1f}%")
