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
import os, wave, argparse
import numpy as np
import render

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100


# ------------------------------------------------------------- 効果音の合成

def env(n, attack=0.004, decay=0.12, power=2.2):
    a = int(SR * attack)
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    tail = np.linspace(0, 1, n - a)
    e[a:] = (1 - tail) ** power
    return e


def whoosh(dur=0.13):
    """カットの切り替わり。短く「スッ」。"""
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.random.default_rng(7).normal(0, 1, n)
    # 一次ローパスの係数を時間で動かして、高い方へ抜ける感じを作る
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        k = 0.06 + 0.55 * (i / n)
        acc += k * (noise[i] - acc)
        y[i] = noise[i] - acc          # ハイパス側を取る
    return y * env(n, 0.003, dur, 2.6) * 0.30


def don(dur=0.30):
    """章の切り替わり（title）。低い「ドン」。"""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 92 * np.exp(-t * 7) + 46
    body = np.sin(2 * np.pi * np.cumsum(f) / SR)
    click = np.random.default_rng(3).normal(0, 1, n) * np.exp(-t * 190) * 0.35
    return (body * 0.85 + click) * env(n, 0.002, dur, 1.7) * 0.55


def ton(dur=0.10):
    """指し棒で黒板を叩く「トン」。"""
    n = int(SR * dur)
    t = np.arange(n) / SR
    body = (np.sin(2 * np.pi * 520 * t) * 0.5 +
            np.sin(2 * np.pi * 880 * t) * 0.3)
    click = np.random.default_rng(11).normal(0, 1, n) * np.exp(-t * 260) * 0.5
    return (body + click) * env(n, 0.001, dur, 3.0) * 0.42


# ------------------------------------------------------------- 配置

def se_events():
    """(秒, 音の種類) の一覧を SHOTS から作る。"""
    ev = []
    for i, s in enumerate(render.SHOTS):
        if i > 0:
            prev = render.SHOTS[i-1]
            章 = s['kind'] == 'title' or prev['kind'] == 'title'
            ev.append((s['t'], 'don' if 章 else 'whoosh'))
        if s.get('tap'):
            ev.append((s['t'] + 0.34, 'ton'))
    return sorted(ev)


def build_track(dur):
    n = int(SR * dur) + SR
    track = np.zeros(n)
    sounds = dict(whoosh=whoosh(), don=don(), ton=ton())
    for t, kind in se_events():
        s = sounds[kind]
        i = int(SR * t)
        track[i:i+len(s)] += s
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

BGM_PLAN = [
    (0.0,  3.4,  0.00, 'フック — 無音。音がないと逆に注意が向く'),
    (3.4,  28.0, 0.18, '本編 — 軽快に、邪魔をしない'),
    (28.0, 35.8, 0.22, '具体例 — 一段上げる'),
    (35.8, 37.1, 0.00, 'オチ直前 — 完全に無音。ここが一番効く'),
    (37.1, 42.5, 0.25, 'オチ — 盛り上げる'),
    (42.5, 99.0, 0.14, '予告 — 落として余韻'),
]


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
    print('  ドン（章の切替）   %d' % c['don'])
    print('  トン（棒で叩く）   %d' % c['ton'])
    print('  -> se.wav')

    if a.preview:
        demo = np.concatenate([whoosh(), np.zeros(SR//3), don(),
                               np.zeros(SR//3), ton(), np.zeros(SR//3)])
        write_wav(os.path.join(HERE, 'se_preview.wav'), demo)
        print('  -> se_preview.wav（スッ / ドン / トン の順に3つ）')

    print('\nBGMの音量設計')
    for s, e, v, why in BGM_PLAN:
        print('  %5.1f〜%5.1f秒  音量 %3d%%   %s' % (s, min(e, dur), v*100, why))
    print('\nffmpeg にそのまま貼る式:')
    print("  volume='" + volume_expr() + "':eval=frame")
    print('\n※ BGMは2曲使う。本編用を bgm.mp3、オチ用を bgm_climax.mp3 に。')
    print('  1曲を音量で上下させても盛り上がりは作れません。')


if __name__ == '__main__':
    main()
