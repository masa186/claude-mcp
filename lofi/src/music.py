# -*- coding: utf-8 -*-
"""Lo-fi study BGM をゼロから合成する。出力: out/loop.wav（シームレスループ）"""
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
BPM = 72.0
BEAT = 60.0 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(20260824)

def n2f(m):                      # MIDIノート番号 -> 周波数
    return 440.0 * 2 ** ((m - 69) / 12.0)

def env_ad(n, a, d, curve=2.2):   # アタック/ディケイ包絡
    at = max(1, int(a * SR))
    e = np.empty(n)
    e[:at] = np.linspace(0, 1, at) ** 0.6
    rest = n - at
    e[at:] = np.exp(-np.linspace(0, curve * 3, rest)) if rest > 0 else 0
    return e

class Track:
    """秒指定で音を書き込めるステレオバッファ"""
    def __init__(self, dur):
        self.buf = np.zeros((int(dur * SR) + SR, 2))
    def add(self, t, mono, gain=1.0, pan=0.0):
        i = int(t * SR)
        n = len(mono)
        l = gain * np.sqrt((1 - pan) / 2) * 1.414
        r = gain * np.sqrt((1 + pan) / 2) * 1.414
        self.buf[i:i + n, 0] += mono * l
        self.buf[i:i + n, 1] += mono * r
    def get(self, dur):
        return self.buf[:int(dur * SR)]

# ---------------------------------------------------------------- 音色
def rhodes(freq, dur, vel=1.0):
    """FM合成のエレピ。倍音が減衰で減る＝ローズらしさ"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    idx = 2.4 * np.exp(-t * 5.5) * vel          # 変調指数は速く減る
    mod = np.sin(2 * np.pi * freq * 2.0 * t) * idx
    car = np.sin(2 * np.pi * freq * t + mod)
    car += 0.28 * np.sin(2 * np.pi * freq * 1.001 * t + mod * 0.7)   # デチューン
    body = np.exp(-t * (1.5 + 260 / freq))       # 高音ほど速く減衰
    tine = np.sin(2 * np.pi * freq * 4.02 * t) * np.exp(-t * 22) * 0.16 * vel
    return (car * body + tine) * 0.5 * vel

def sub_bass(freq, dur, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t + 0.7 * np.sin(2 * np.pi * freq * t))
    x = np.tanh(x * 1.35)                         # 軽いサチュレーション
    e = np.minimum(1.0, t / 0.012) * np.exp(-t * 2.1)
    return x * e * vel * 0.9

def kick(dur=0.55, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 48 + 82 * np.exp(-t * 34)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR)
    click = rng.normal(0, 1, n) * np.exp(-t * 420) * 0.10
    return (x * np.exp(-t * 6.2) + click) * vel * 0.95

def snare(dur=0.32, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = rng.normal(0, 1, n)
    b, a = signal.butter(2, [1400 / (SR / 2), 7200 / (SR / 2)], "band")
    nz = signal.lfilter(b, a, nz)
    tone = np.sin(2 * np.pi * 196 * t) * np.exp(-t * 34) * 0.35
    return (nz * np.exp(-t * 19) + tone) * vel * 0.5

def hat(dur=0.09, vel=1.0, open_=False):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = rng.normal(0, 1, n)
    b, a = signal.butter(3, 4200 / (SR / 2), "high")
    nz = signal.lfilter(b, a, nz)
    return nz * np.exp(-t * (13 if open_ else 46)) * vel * 0.30

def bell(freq, dur, vel=1.0):
    """メロディ用のやわらかいベル/オルゴール"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t)
         + 0.34 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 7)
         + 0.13 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t * 12))
    return x * np.exp(-t * 3.0) * np.minimum(1, t / 0.008) * vel * 0.3

# ---------------------------------------------------------------- 空間
def reverb_ir(dur=2.1, decay=4.2, pre=0.02):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-t * decay)[:, None]
    b, a = signal.butter(2, 4200 / (SR / 2), "low")
    ir = signal.lfilter(b, a, ir, axis=0)
    ir[:int(pre * SR)] = 0
    ir[0] = 0
    return ir / np.abs(ir).max()

def convolve_st(x, ir):
    return np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)

def wow_flutter(x, depth=0.0016, rate=0.55):
    """テープの揺れ。読み出し位置を微妙に揺らす"""
    n = len(x)
    t = np.arange(n) / SR
    drift = depth * (np.sin(2 * np.pi * rate * t) + 0.45 * np.sin(2 * np.pi * rate * 3.7 * t + 1.1))
    pos = np.clip(np.arange(n) + drift * SR, 0, n - 1)
    i0 = pos.astype(int); fr = pos - i0
    i1 = np.minimum(i0 + 1, n - 1)
    return np.stack([x[i0, c] * (1 - fr) + x[i1, c] * fr for c in range(2)], 1)

def vinyl(n):
    """レコードのパチパチ＋針のノイズ"""
    crackle = np.zeros(n)
    hits = rng.random(n) < 0.00055
    crackle[hits] = rng.normal(0, 1, hits.sum()) * 0.8
    b, a = signal.butter(2, [1800 / (SR / 2), 9000 / (SR / 2)], "band")
    crackle = signal.lfilter(b, a, crackle)
    hiss = rng.normal(0, 1, n)
    b2, a2 = signal.butter(2, [500 / (SR / 2), 8000 / (SR / 2)], "band")
    hiss = signal.lfilter(b2, a2, hiss) * 0.014
    out = crackle * 0.28 + hiss
    return np.stack([out, np.roll(out, 313)], 1)

# ---------------------------------------------------------------- 曲を組む
BARS = 16
DUR = BARS * BAR                      # 16小節 = 53.33秒

CHORDS = [                            # Imaj9 - vi7 - ii7 - V7（4小節で1周）
    ([52, 55, 59, 62], 36),           # Cmaj9
    ([52, 55, 57, 60], 33),           # Am7
    ([50, 53, 57, 60], 38),           # Dm7
    ([50, 53, 55, 59], 31),           # G7
]
MELODY = [   # (小節, 拍, ノート, 長さ拍)  ペンタトニックの短い動機
    (0, 2.0, 72, 1.0), (0, 3.0, 74, 1.0),
    (1, 0.0, 76, 1.5), (1, 2.5, 72, 1.0),
    (2, 1.0, 69, 1.0), (2, 2.0, 72, 2.0),
    (3, 2.0, 74, 1.0), (3, 3.0, 76, 1.0),
    (4, 0.0, 79, 2.0), (4, 3.0, 76, 1.0),
    (5, 1.0, 74, 1.5), (5, 3.0, 72, 1.0),
    (6, 0.0, 69, 1.5), (6, 2.5, 67, 1.5),
    (8, 2.0, 72, 1.0), (8, 3.0, 76, 1.0),
    (9, 0.0, 79, 1.5), (9, 2.5, 77, 1.0),
    (10, 1.0, 76, 1.0), (10, 2.0, 74, 2.0),
    (11, 2.0, 72, 2.0),
    (12, 0.0, 76, 1.5), (12, 2.5, 79, 1.0),
    (13, 1.0, 81, 2.0),
    (14, 0.0, 79, 1.5), (14, 2.5, 76, 1.5),
]

keys = Track(DUR + 4); bass = Track(DUR + 4); drums = Track(DUR + 4); lead = Track(DUR + 4)

for bar in range(BARS):
    ch, root = CHORDS[bar % 4]
    t0 = bar * BAR
    # --- エレピ：1拍目と2拍半の裏に置く
    for beat, vel, spread in ((0.0, 0.85, 1.0), (2.5, 0.55, 0.85)):
        if beat > 0 and bar % 4 == 3 and bar % 8 != 7:
            vel *= 0.7
        for k, m in enumerate(ch):
            roll = k * 0.011                              # かるいアルペジオ感
            pan = (k - 1.5) * 0.26 * spread
            keys.add(t0 + beat * BEAT + roll, rhodes(n2f(m), 2.6, vel * (1 - 0.06 * k)),
                     0.5, pan)
    # --- ベース：1拍目と3拍半
    bass.add(t0, sub_bass(n2f(root), BEAT * 1.9, 1.0), 0.58)
    bass.add(t0 + BEAT * 3.5, sub_bass(n2f(root + (7 if bar % 2 else 0)), BEAT * 0.8, 0.62), 0.52)
    # --- ドラム
    drums.add(t0, kick(vel=0.92), 0.66)
    drums.add(t0 + BEAT * 2.5, kick(vel=0.70), 0.66)
    if bar % 4 == 3:
        drums.add(t0 + BEAT * 3.75, kick(vel=0.5), 0.72)
    drums.add(t0 + BEAT * 1, snare(vel=0.92), 0.62, -0.06)
    drums.add(t0 + BEAT * 3, snare(vel=0.92), 0.62, -0.06)
    for i in range(8):                                    # ハイハット（スイング）
        sw = 0.0 if i % 2 == 0 else 0.115
        v = (0.85 if i % 2 == 0 else 0.46) * (1 + 0.1 * rng.normal())
        drums.add(t0 + (i * 0.5 + sw) * BEAT, hat(vel=v, open_=(i == 7 and bar % 4 == 3)),
                  0.5, 0.18)

for bar, beat, note, ln in MELODY:                        # メロディ
    lead.add(bar * BAR + beat * BEAT, bell(n2f(note), ln * BEAT + 0.9, 0.9), 0.4, -0.12)

# ---------------------------------------------------------------- ミックス
n = int(DUR * SR)
mix = (keys.get(DUR) * 0.82 + bass.get(DUR) * 0.72 + drums.get(DUR) * 0.88 + lead.get(DUR) * 0.72)

wet_src = keys.get(DUR) * 0.75 + lead.get(DUR) * 0.9 + drums.get(DUR) * 0.18
mix += convolve_st(wet_src, reverb_ir()) * 0.30           # リバーブ

b, a = signal.butter(2, 9800 / (SR / 2), "low")           # テープ的に上を削る
mix = signal.lfilter(b, a, mix, axis=0)
b, a = signal.butter(2, 38 / (SR / 2), "high")
mix = signal.lfilter(b, a, mix, axis=0)
mix = wow_flutter(mix)
mix += vinyl(len(mix)) * 0.85

env = np.abs(mix).max(axis=1)                             # ゆるいコンプ
b, a = signal.butter(2, 12 / (SR / 2), "low")
sm = signal.lfilter(b, a, env)
gain = 1.0 / (1.0 + np.maximum(0, sm - 0.55) * 1.5)
mix *= gain[:, None]
mix = np.tanh(mix * 1.05) * 0.92

# ループの継ぎ目を消す（先頭と末尾を数ms クロスフェード）
xf = int(0.012 * SR)
fade = np.linspace(0, 1, xf)[:, None]
mix[:xf] = mix[:xf] * fade + mix[-xf:] * (1 - fade)
mix = mix[:-xf]

peak = np.abs(mix).max()
mix = mix / np.sqrt((mix ** 2).mean()) * 0.23
mix = np.tanh(mix * 1.02)
mix = mix / np.sqrt((mix ** 2).mean()) * 0.20          # BGMとして扱いやすい音量に揃える
mix = np.clip(mix, -0.97, 0.97)
wavfile.write("out/loop.wav", SR, (mix * 32767).astype(np.int16))
print(f"len={len(mix)/SR:.3f}s bars={BARS} peak={peak:.3f} rms={np.sqrt((mix**2).mean()):.4f}")
