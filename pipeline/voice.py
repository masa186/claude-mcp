"""ナレーションを合成して、ショットの頭に貼り付けた1本のWAVを作る。

エンジンは Open JTalk（オフライン）。この環境から出られる先が制限されていて、
Edge TTS / Google TTS のホストは 403 で塞がれているため、選択肢がこれになる。
声は素直に言えば合成くさい。人の声にしたいときは自分で録って
narration.wav / narration2.wav に置けば、そちらが優先される。

  python3 voice.py --demo     声の設定を3つ並べた聞き比べWAVを書き出す

使い方（ふつうはこちらは呼ばない。build.py / ep02.py が呼ぶ）:
  import voice; voice.build('voice2.wav')
"""
import os, re, sys, wave, math, shutil, subprocess, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100

OJT  = shutil.which('open_jtalk')
DIC  = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
HTS  = '/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice'

# -a  声道の長さ。小さいほど細く若い声
# -fm 音の高さ（半音）。上げすぎると子どもっぽくなる
# -jf 抑揚。上げるとよく喋る感じになる
PRESETS = {
    'otter':  dict(a=0.47, fm=2.2, jf=1.35),   # 少し高く、抑揚を強め
    'calm':   dict(a=0.54, fm=0.0, jf=1.00),   # 素の声
    'bright': dict(a=0.42, fm=4.0, jf=1.55),   # かなり高い
}

# open_jtalk の -r は 1.0 が「かなりゆっくり」。実測で 1.75 前後が
# 日本語のふつうのナレーション速度（1秒あたり9〜10モーラ）になる。
BASE_RATE = 1.75
RATE_MAX = 2.60          # これ以上速くすると聞き取れなくなる
HEAD     = 0.05          # カットの頭から何秒後に喋り出すか
TAIL     = 0.12          # 次のカットに食い込ませない余白


def available():
    return bool(OJT) and os.path.exists(DIC) and os.path.exists(HTS)


def clean(text):
    """テロップ用の { } を外し、読み上げに向かない記号を落とす。"""
    t = text.replace('{', '').replace('}', '').replace('\n', '、')
    t = t.replace('bro、', 'ブロ、').replace('bro', 'ブロ')
    t = re.sub(r'[「」『』]', '', t)
    return t.strip()


def _synth(text, rate, p):
    """1行だけ合成して、44.1kHz モノラルの配列で返す。"""
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, 'in.txt')
        out = os.path.join(d, 'out.wav')
        open(src, 'w', encoding='utf-8').write(text + '\n')
        cmd = [OJT, '-x', DIC, '-m', HTS, '-ow', out,
               '-r', '%.3f' % rate, '-a', '%.3f' % p['a'],
               '-fm', '%.2f' % p['fm'], '-jf', '%.2f' % p['jf']]
        r = subprocess.run(cmd + [src], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out):
            return np.zeros(0)
        with wave.open(out, 'rb') as w:
            sr, n = w.getframerate(), w.getnframes()
            raw = w.readframes(n)
    x = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768
    if sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)),
                      np.arange(len(x)), x)
    return trim_silence(x)


def trim_silence(x, thr=0.006):
    """前後の無音を落とす。合成音は頭に無音が入るので、そのままだと
    カットの頭からずれて、絵と声が合わなくなる。"""
    if not len(x):
        return x
    a = np.abs(x)
    idx = np.nonzero(a > thr)[0]
    if not len(idx):
        return x
    return x[max(0, idx[0] - int(SR * 0.01)):idx[-1] + int(SR * 0.02)]


def lines(shots):
    """(開始秒, 使える長さ, 読む文) を作る。say があれば say、無ければ tele。"""
    out = []
    for s in shots:
        t = clean(s.get('say') or s.get('tele') or '')
        if t:
            out.append((s['t'] + HEAD, max(0.4, s['dur'] - HEAD - TAIL), t))
    return out


def build(path, preset='otter', verbose=True):
    """render.SHOTS からナレーションを合成して1本にまとめる。"""
    import render
    if not available():
        if verbose:
            print('  open_jtalk が無いのでナレーションは飛ばす')
        return False
    p = PRESETS[preset]
    track = np.zeros(int(SR * render.DURATION) + SR)
    over = []
    for t0, room, text in lines(render.SHOTS):
        x = _synth(text, BASE_RATE, p)
        if not len(x):
            continue
        need = len(x) / SR
        if need > room:
            # ショットに収まらないぶんだけ早口にする。それでも溢れるなら記録する
            # 長さは rate のおよそ -0.78 乗で縮む（実測）
            rate = min(RATE_MAX, BASE_RATE * (need / room) ** 1.28)
            x = _synth(text, rate, p)
            if len(x) / SR > room + 0.25:
                over.append((t0, len(x) / SR - room, text))
        m = np.abs(x).max()
        if m > 0:
            x = x * (0.62 / m)
        i = int(SR * t0)
        track[i:i + len(x)] += x[:max(0, len(track) - i)]
    pk = np.abs(track).max()
    if pk > 0.90:
        track *= 0.90 / pk
    import sound
    sound.write_wav(path, track[:int(SR * render.DURATION)])
    if verbose:
        print('  ナレーション %d行 → %s' % (len(lines(render.SHOTS)), path))
        for t0, ex, text in over:
            print('    %5.1fs %.1f秒はみ出す: %s' % (t0, ex, text[:24]))
    return True


def demo(path=None):
    import sound
    path = path or os.path.join(HERE, 'voice_demo.wav')
    txt = '飛行機は、空気を下に殴って進んでる。これが揚力。'
    gap = np.zeros(int(SR * 0.6))
    parts = []
    for name in ('otter', 'calm', 'bright'):
        parts += [_synth(txt, BASE_RATE, PRESETS[name]), gap]
    sound.write_wav(path, np.concatenate(parts))
    print('聞き比べ → %s（otter / calm / bright の順）' % path)


if __name__ == '__main__':
    if not available():
        raise SystemExit('open_jtalk がありません:\n'
                         '  apt-get install open-jtalk open-jtalk-mecab-naist-jdic '
                         'hts-voice-nitech-jp-atr503-m001')
    if '--demo' in sys.argv:
        demo()
    else:
        print(__doc__)
