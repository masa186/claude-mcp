"""音の大きさと、突き出た音（効果音）の目立ち方を測る。

    python3 measaudio.py ep12.mp4 参考.mp4 ...

  ラウドネス   EBU R128 の統合値（LUFS）。放送で使う物差し。
  レンジ       LRA。大小の開き。効果音だけ突出していると広がる。
  真のピーク   dBTP。
  突出         200ms ごとの音量を出し、中央値より 6dB 以上大きい区間の割合。
               喋りの上に効果音を重ねると、ここが上がる。
"""
import sys, os, subprocess, re
import numpy as np
import imageio_ffmpeg as ie

FF = ie.get_ffmpeg_exe()

def r128(path):
    o = subprocess.run([FF, '-nostats', '-i', path, '-af', 'ebur128=peak=true',
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    tail = o[-1500:]
    def g(k):
        m = re.findall(k + r':\s*(-?[\d.]+)', tail)
        return float(m[-1]) if m else float('nan')
    return g('I'), g('LRA'), g('Peak')

def spikes(path):
    p = subprocess.Popen([FF, '-v', 'error', '-i', path, '-ac', '1', '-ar', '16000',
                          '-f', 'f32le', '-'], stdout=subprocess.PIPE)
    x = np.frombuffer(p.stdout.read(), np.float32); p.wait()
    w = int(0.2 * 16000)
    n = len(x) // w
    if n < 5: return float('nan')
    lv = np.array([np.sqrt((x[i*w:(i+1)*w].astype(np.float64)**2).mean()) for i in range(n)])
    lv = lv[lv > 1e-5]
    if len(lv) < 5: return float('nan')
    db = 20 * np.log10(lv)
    return float((db > np.median(db) + 6).mean()) * 100

if __name__ == '__main__':
    print(f'{"":34s} {"ラウドネス":>9s} {"レンジ":>7s} {"ピーク":>7s} {"突出":>6s}')
    for f in sys.argv[1:]:
        I, LRA, TP = r128(f)
        sp = spikes(f)
        print(f'{os.path.basename(f)[:34]:34s} {I:7.1f}LUFS {LRA:6.1f} {TP:6.1f}dB {sp:5.1f}%')
