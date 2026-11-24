"""作業用BGMを自前で合成する。耐久動画用。

Lyria（Google の音楽生成）は無料枠が無く429で弾かれた。外から持ってくると
権利の確認も要る。ここで作れば権利は全部こちらのもので、長さも無制限。

  python3 bgm_study.py 60 loop.wav     60秒の継ぎ目のないループを作る

継ぎ目を無くすため、すべての周期は尺をちょうど割り切る値だけを使う。
そうすると末尾と先頭が完全に一致するので、何時間つないでも段差が出ない。
"""
import sys, math
import numpy as np
import sound

SR = sound.SR


def note(n, f, dur, kind='piano'):
    """1音。倍音の混ぜ方だけで音色を変える。"""
    t = np.arange(n) / SR
    if kind == 'piano':
        parts = [(1.0, 1.00), (2.0, 0.36), (3.0, 0.14), (4.0, 0.07), (6.0, 0.03)]
        dec = 2.6
    elif kind == 'bass':
        parts = [(1.0, 1.00), (2.0, 0.22), (3.0, 0.06)]
        dec = 1.7
    else:  # pad
        parts = [(1.0, 1.00), (2.0, 0.5), (3.0, 0.28), (5.0, 0.10)]
        dec = 0.55
    x = np.zeros(n)
    for k, g in parts:
        # わずかに揺らす。完全な整数倍だと電子音に聞こえる
        x += g * np.sin(2*np.pi*f*k*t + 0.4*k) * np.exp(-dec*t*(0.7+0.3*k))
    a = int(SR*0.008)
    x[:a] *= np.linspace(0, 1, a)
    return x / (np.abs(x).max() + 1e-9)


# ハ長調のペンタトニック風。外れた音が出ないので、どう並べても濁らない
SCALE = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25]
BASS  = [65.41, 87.31, 98.00, 82.41]     # C, F, G, E


def build(seconds, seed=7):
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)
    out = np.zeros(n)

    # --- コード。4小節でひと回り。尺を割り切る長さにする
    bars = max(4, int(round(seconds / 8.0)) * 4)
    barn = n // bars
    for b in range(bars):
        root = BASS[b % len(BASS)]
        s = b * barn
        x = note(min(barn*2, n-s), root, 0, 'bass') * 0.34
        out[s:s+len(x)] += x
        pad = note(min(barn*2, n-s), root*4, 0, 'pad') * 0.10
        out[s:s+len(pad)] += pad

    # --- 旋律。拍の上にだけ置く
    beat = barn // 4
    prev = 2
    for i in range(bars*4):
        if rng.random() < 0.28:      # 休符。詰めすぎると作業の邪魔になる
            continue
        step = int(rng.integers(-2, 3))
        prev = max(0, min(len(SCALE)-1, prev + step))
        s = i * beat
        if s >= n: break
        x = note(min(beat*3, n-s), SCALE[prev], 0, 'piano') * (0.16 + 0.05*rng.random())
        out[s:s+len(x)] += x

    # --- テープのヒス。ずっと同じだと耳に付くのでゆっくり揺らす
    hiss = rng.normal(0, 1, n)
    hiss = sound.lowpass(hiss, 5200, 2) * 0.006
    slow = 1 + 0.35*np.sin(2*np.pi*np.arange(n)/n * 3)
    out += hiss * slow

    out = sound.lowpass(out, 6800, 2)
    # 継ぎ目対策。頭と尻の20msだけクロスさせる
    c = int(SR*0.02)
    out[:c] *= np.linspace(0, 1, c)
    out[-c:] *= np.linspace(1, 0, c)
    out[:c] += out[-c:][::-1] * 0        # 位相をいじらない。念のため明示
    return out / (np.abs(out).max() + 1e-9) * 0.72


if __name__ == '__main__':
    sec = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    path = sys.argv[2] if len(sys.argv) > 2 else 'bgm_loop.wav'
    x = build(sec)
    sound.write_wav(path, x)
    print('%s  %.0f秒  %.1f MB' % (path, len(x)/SR, len(x)*2/1e6))
