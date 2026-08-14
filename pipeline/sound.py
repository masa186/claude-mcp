"""
効果音トラックを作る ＋ BGMの音量設計を出す
=============================================
render.py の SHOTS から、カットの切り替わりと指し棒のタップを拾って
効果音を鳴らした1本のWAVを書き出す。効果音そのものもここで合成するので、
素材をどこかから拾ってくる必要はない。

  python3 sound.py              # se.wav を書き出し、BGMの音量式を表示
  python3 sound.py --preview    # 効果音3種だけを並べた確認用WAVも書き出す

出てくるもの:
  se.wav   … 動画と同じ長さの効果音トラック（ナレーションとBGMに重ねる）
  BGMの音量オートメーション式（ffmpeg の volume= にそのまま貼る）
"""
import os, wave, argparse, math
import numpy as np
import render

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100


# ------------------------------------------------------------- 効果音の合成

def env(n, attack=0.004, power=2.2):
    a = max(1, int(SR * attack))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[a:] = (1 - np.linspace(0, 1, n - a)) ** power
    return e


def tail(x, times=(0.021, 0.037, 0.058), gains=(0.30, 0.19, 0.11)):
    """短い残響。合成音が「ペラい」と感じるのは、ほぼ余韻が無いから。"""
    out = np.zeros(len(x) + int(SR * 0.20))
    out[:len(x)] = x
    for tt, g in zip(times, gains):
        d = int(SR * tt)
        out[d:d+len(x)] += x * g
    dec = np.exp(-np.arange(len(out)) / (SR * 0.075))
    return out * dec


def lowpass(x, fc, poles=2):
    """高域を落として重心を下げる。合成音が安く聞こえる一番の原因は
    「シャリついた高域ばかりで芯が無い」こと。"""
    k = 1 - math.exp(-2 * math.pi * fc / SR)
    y = x.copy()
    for _ in range(poles):
        acc = 0.0
        out = np.empty_like(y)
        for i in range(len(y)):
            acc += k * (y[i] - acc)
            out[i] = acc
        y = out
    return y


def bandnoise(n, f0, f1, q, seed):
    """共振する帯域を f0→f1 へ動かしながらノイズを通す。whoosh の芯になる。"""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    y = np.zeros(n)
    lp = bp = 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * (i / n)
        k = min(0.99, 2 * math.pi * f / SR)
        hp = x[i] - lp - q * bp
        bp += k * hp
        lp += k * bp
        y[i] = bp
    return y / (np.abs(y).max() + 1e-9)


def modal(n, freqs, gains, decays):
    """減衰する正弦を重ねる。木や金属の「当たり」はこれで出る。"""
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, g, d in zip(freqs, gains, decays):
        y += g * np.sin(2 * math.pi * f * t) * np.exp(-t * d)
    return y


def whoosh(v=0):
    """カットの切り替わり。空気が抜ける「シュッ」。"""
    dur = 0.16 + 0.02 * v
    n = int(SR * dur)
    core = lowpass(bandnoise(n, 500 + 90*v, 1900 + 200*v, 0.32, 7 + v), 2200)
    body = modal(n, (190 + 16*v, 330), (0.60, 0.34), (22, 30))
    y = (core * 1.5 + body) * env(n, 0.006, 2.0)
    return tail(y, (0.017, 0.031), (0.26, 0.15)) * 0.34


def don(v=0):
    """章の切り替わり。低域だけだとスマホで鳴らないので中高域を重ねる。"""
    dur = 0.42
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = (190 + 20*v) * np.exp(-t * 9) + 72
    sub = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    mid = modal(n, (430, 690, 1180, 1900), (0.62, 0.44, 0.30, 0.16), (16, 22, 30, 38))
    hit = lowpass(bandnoise(int(SR*0.05), 900, 2400, 0.5, 31 + v), 2600)
    y = sub * 0.42 + mid * 1.5
    y[:len(hit)] += hit * 0.30
    y = lowpass(y * env(n, 0.002, 1.5), 5200)
    return tail(y, (0.028, 0.049, 0.077), (0.34, 0.22, 0.13)) * 0.5


def ton(v=0):
    """指し棒が黒板を叩く音。木の当たりなので倍音は整数比にしない。"""
    n = int(SR * 0.22)
    body = modal(n, (430 + 22*v, 1080, 1720, 2540),
                    (0.66, 0.30, 0.15, 0.07), (30, 44, 58, 78))
    click = lowpass(bandnoise(int(SR*0.02), 1200, 3000, 0.6, 11 + v), 3000)
    y = body * env(n, 0.0008, 2.4)
    y[:len(click)] += click * 0.22
    return tail(lowpass(y, 5000), (0.013, 0.026), (0.24, 0.13)) * 0.42


def chalk(v=0):
    """黒板に文字が書かれる音。細かい擦れの粒。"""
    dur = 0.30
    n = int(SR * dur)
    rng = np.random.default_rng(23 + v)
    grains = np.zeros(n)
    step = int(SR * 0.0095)
    for i in range(0, n - step, step):
        grains[i:i+step] += rng.normal(0, 1, step) * np.hanning(step) * (0.4 + 0.6*rng.random())
    y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc += 0.40 * (grains[i] - acc)
        y[i] = grains[i] - acc
    y = lowpass(y, 1150) * 7.0                          # 12kHz のシャリつきを落とす
    y += modal(n, (300, 520), (0.16, 0.09), (12, 18))   # 芯を足す
    y *= env(n, 0.008, 1.1)
    return tail(y, (0.019,), (0.18,)) * 0.26


VARIANTS = 3          # 毎回まったく同じ波形だと機械っぽく聞こえる


# ------------------------------------------------------------- 配置

def se_events():
    """(秒, 音の種類) の一覧を SHOTS から作る。

    参考動画は音の立ち上がりが 0.75〜0.89秒に1回。カットの切り替わりだけでは
    足りないので、黒板に文字や図が出る瞬間にもチョークの音を置いて密度を埋める。
    """
    ev = []
    for i, s in enumerate(render.SHOTS):
        if i > 0:
            prev = render.SHOTS[i-1]
            章 = s['kind'] == 'title' or prev['kind'] == 'title'
            ev.append((s['t'], 'don' if 章 else 'whoosh'))
        if s.get('board') or s.get('fig'):
            ev.append((s['t'] + 0.10, 'chalk'))
        if s.get('tap'):
            ev.append((s['t'] + 0.34, 'ton'))
    return sorted(ev)


def build_track(dur):
    n = int(SR * dur) + SR
    track = np.zeros(n)
    # 参考動画のアタックは周波数重心が約1900Hz。合成音は放っておくと高域に
    # 寄って「安っぽい」音になるので、最後に全部を同じ処理に通して揃える。
    def shape(x, target=2000.0, peak=0.55):
        for fc in (9000, 7000, 5600, 4600, 3800, 3200, 2700, 2300, 2000, 1700):
            y = lowpass(x, fc)
            w = np.abs(np.fft.rfft(y * np.hanning(len(y))))
            fr = np.fft.rfftfreq(len(y), 1 / SR)
            if (w * fr).sum() / (w.sum() + 1e-9) <= target:
                x = y
                break
            x = y
        m = np.abs(x).max()
        return x * (peak / m) if m > 0 else x

    banks = {k: [shape(f(v), peak=pk) for v in range(VARIANTS)]
             for k, f, pk in (('whoosh', whoosh, 0.42), ('don', don, 0.62),
                              ('ton', ton, 0.55), ('chalk', chalk, 0.26))}
    for j, (t, kind) in enumerate(se_events()):
        s = banks[kind][j % VARIANTS]          # 同じ音を続けて鳴らさない
        i = int(SR * t)
        track[i:i+len(s)] += s[:max(0, len(track)-i)]
    peak = np.abs(track).max()
    if peak > 0.95:
        track *= 0.95 / peak
    return track[:int(SR * dur)]


def write_wav(path, mono):
    data = np.clip(mono, -1, 1)
    pcm = (data * 32767).astype('<i2')
    stereo = np.repeat(pcm[:, None], 2, axis=1).tobytes()
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(stereo)


# ------------------------------------------------------------- BGMの音量設計

# 参考動画2本を解析したところ、0.35秒以上の無音は1箇所も無かった。
# 完全に落とすと「切れた」と感じさせるので、下げ切らずに絞る形に変更。
_LEVELS = [
    ('hook',    0.10, 'フック — かなり絞る。テロップと声に集中させる'),
    ('setup',   0.18, '本編 — 軽快に、邪魔をしない'),
    ('how',     0.18, '仕組み — そのまま'),
    ('example', 0.22, '具体例 — 一段上げる'),
    ('punch',   0.26, 'オチ — 盛り上げる（直前の title で一度絞る）'),
    ('next',    0.14, '予告 — 落として余韻'),
]


def bgm_plan():
    """秒数を手で書かず、SHOTS の区切りから組み立てる。台本を変えても追従する。"""
    tm = render.section_times()
    plan, keys = [], [k for k, _, _ in _LEVELS if k in tm]
    for i, key in enumerate(keys):
        lv  = next(v for k, v, _ in _LEVELS if k == key)
        why = next(w for k, _, w in _LEVELS if k == key)
        start = tm[key]
        end   = tm[keys[i+1]] if i+1 < len(keys) else render.DURATION
        if key == 'punch':
            # オチの直前（title のあいだ）だけ絞る。無音にはしない
            duck = next(s['dur'] for s in render.SHOTS if s.get('sec') == 'punch')
            plan.append((start, start+duck, 0.07, 'オチ直前 — ぐっと絞る（無音にはしない）'))
            start += duck
        plan.append((start, end, lv, why))
    return plan


BGM_PLAN = bgm_plan()


def volume_expr():
    """ffmpeg の volume= にそのまま貼れる式を作る。"""
    e = '%.2f' % BGM_PLAN[-1][2]
    for a, b, v, _ in reversed(BGM_PLAN[:-1]):
        e = "if(lt(t,%.2f),%.2f,%s)" % (b, v, e)
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true')
    a = ap.parse_args()

    dur = render.DURATION
    ev = se_events()
    track = build_track(dur)
    p = os.path.join(HERE, 'se.wav')
    write_wav(p, track)

    from collections import Counter
    c = Counter(k for _, k in ev)
    print('効果音トラック  %.1f秒  %d個  平均 %.2f秒に1回' % (dur, len(ev), dur/len(ev)))
    print('  スッ（カット切替） %d' % c['whoosh'])
    print('  カリ（文字を書く） %d' % c['chalk'])
    print('  ドン（章の切替）   %d' % c['don'])
    print('  トン（棒で叩く）   %d' % c['ton'])
    print('  -> se.wav')

    if a.preview:
        gap = np.zeros(SR//3)
        demo = np.concatenate([whoosh(), gap, chalk(), gap, don(), gap, ton(), gap])
        write_wav(os.path.join(HERE, 'se_preview.wav'), demo)
        print('  -> se_preview.wav（シュッ / カリ / ドン / トン の順に4つ）')

    print('\nBGMの音量設計')
    for s, e, v, why in BGM_PLAN:
        print('  %5.1f〜%5.1f秒  音量 %3d%%   %s' % (s, min(e, dur), v*100, why))
    print('\nffmpeg にそのまま貼る式:')
    print("  volume='" + volume_expr() + "':eval=frame")
    print('\n※ BGMは2曲使う。本編用を bgm.mp3、オチ用を bgm_climax.mp3 に。')
    print('  1曲を音量で上下させても盛り上がりは作れません。')


if __name__ == '__main__':
    main()
