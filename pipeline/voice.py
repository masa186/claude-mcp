"""ナレーションを用意して、ショットの頭に貼り付けた1本のWAVを作る。

声の出どころは3つ。上から優先される。
  1. narration.wav / narration2.wav … 自分で録った通しの声
  2. voicevox/ の連番WAV          … VOICEVOX で1行ずつ書き出したもの
  3. Open JTalk の合成            … 何も無いときの仮の声

尺に収まらない行は「早口にする」のをやめた。速くすると聞き取れなくなる。
代わりにショットのほうを伸ばす。台本の意味を削らずに済むのはこちら。

  python3 voice.py --demo     合成音声の設定3つを聞き比べ
  python3 voice.py --text     VOICEVOX に貼る用のテキストを書き出す
"""
import os, re, sys, wave, math, glob, shutil, subprocess, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100

OJT = shutil.which('open_jtalk')
DIC = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
HTS = '/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice'

# -a  声道の長さ。小さいほど細く若い声
# -fm 音の高さ（半音）
# -jf 抑揚
# 青山龍星は低くて太い男声。Open JTalk でそこに寄せるなら、
# 声道を長く（-a を大きく）して、音の高さを下げる（-fm を負に）。
PRESETS = {
    'ryusei': dict(a=0.61, fm=-4.0, jf=1.15),   # 低く太い（青山龍星寄り。既定）
    # 決め台詞だけ上げる。全部同じ抑揚だと、どこが山か分からない
    'punch':  dict(a=0.58, fm=-1.0, jf=1.70),
    'deep':   dict(a=0.58, fm=-2.5, jf=1.25),   # 低め。少し抑揚を残す
    'otter':  dict(a=0.47, fm=2.2, jf=1.35),    # 前の声（軽い）
    'calm':   dict(a=0.54, fm=0.0, jf=1.00),
    'bright': dict(a=0.42, fm=4.0, jf=1.55),
}
DEFAULT = 'ryusei'

# open_jtalk の -r は 1.0 が「かなりゆっくり」。実測で 1.75 前後が
# 日本語のふつうのナレーション速度（1秒あたり9〜10モーラ）になる。
NATURAL = 1.75
HEAD = 0.06          # カットの頭から何秒後に喋り出すか
TAIL = 0.14          # 次のカットに食い込ませない余白
MAX_DUR = 4.2        # これ以上長いショットは絵がもたない。台本を割るべき合図


def available():
    return bool(OJT) and os.path.exists(DIC) and os.path.exists(HTS)


def clean(text):
    """テロップ用の { } を外し、読み上げに向かない記号を落とす。"""
    t = text.replace('{', '').replace('}', '').replace('\n', '、')
    t = t.replace('bro、', 'ブロ、').replace('bro', 'ブロ')
    t = re.sub(r'[「」『』]', '', t)
    return t.strip()


def lines(shots):
    """(ショット番号, 読む文) を返す。say があれば say、無ければ tele。"""
    out = []
    for i, s in enumerate(shots):
        t = clean(s.get('say') or s.get('tele') or '')
        if t:
            out.append((i, t))
    return out


# ------------------------------------------------------------- 音を読む

def read_wav(path):
    """44.1kHz モノラルに揃えて読む。"""
    with wave.open(path, 'rb') as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        x = np.interp(np.linspace(0, len(x)-1, int(len(x)*SR/sr)), np.arange(len(x)), x)
    return x


def trim_silence(x, thr=0.006):
    """前後の無音を落とす。頭に無音が残ると、絵と声がずれる。"""
    if not len(x):
        return x
    idx = np.nonzero(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    return x[max(0, idx[0] - int(SR*0.01)):idx[-1] + int(SR*0.02)]


# ------------------------------------------------------------- 合成

def _synth(text, rate, p):
    with tempfile.TemporaryDirectory() as d:
        src, out = os.path.join(d, 'in.txt'), os.path.join(d, 'out.wav')
        open(src, 'w', encoding='utf-8').write(text + '\n')
        cmd = [OJT, '-x', DIC, '-m', HTS, '-ow', out, '-r', '%.3f' % rate,
               '-a', '%.3f' % p['a'], '-fm', '%.2f' % p['fm'], '-jf', '%.2f' % p['jf']]
        r = subprocess.run(cmd + [src], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out):
            return np.zeros(0)
        return trim_silence(read_wav(out))


# ------------------------------------------------------------- VOICEVOX から

VV_DIR = os.path.join(HERE, 'voicevox')


def from_voicevox(shots):
    """voicevox/ に並んだ連番WAVを、台詞の順に割り当てる。

    VOICEVOX アプリで docs/narration_*.txt を読み込んで「音声書き出し」すると
    1行1ファイルで出てくる。それをこのフォルダに入れるだけでいい。
    """
    fs = sorted(glob.glob(os.path.join(VV_DIR, '*.wav')))
    ls = lines(shots)
    if not fs:
        return None
    if len(fs) != len(ls):
        print('  voicevox/ は %d本、台詞は %d行。数が合わないので飛ばす'
              % (len(fs), len(ls)))
        return None
    return {i: trim_silence(read_wav(f)) for (i, _), f in zip(ls, fs)}


# ------------------------------------------------------------- 割り付け

def resample(x, src, dst=SR):
    if src == dst or not len(x):
        return x
    return np.interp(np.linspace(0, len(x)-1, int(len(x)*dst/src)),
                     np.arange(len(x)), x)


def from_gemini(shots):
    """Gemini の音声合成。Open JTalk より人の声に近いので、あればこちらを使う。"""
    try:
        import gtts
    except Exception:
        return None
    if not gtts.available():
        return None
    ls = lines(shots)
    # 無料枠は1日10リクエストしかないので、台本ぜんぶを1回で合成して切り分ける
    segs = gtts.say_script([t for _, t in ls])
    if segs is None:
        return None
    return {i: trim_silence(resample(x, gtts.SR))
            for (i, _), x in zip(ls, segs)}


def collect(shots, preset=DEFAULT):
    """各行の音を用意する。自分で録った声 > VOICEVOX > Gemini > Open JTalk。"""
    vv = from_voicevox(shots)
    if vv is not None:
        print('  声: VOICEVOX（voicevox/ の %d本）' % len(vv))
        return vv
    g = from_gemini(shots)
    if g is not None:
        print('  声: Gemini の音声合成（%d行）' % len(g))
        return g
    if not available():
        return {}
    print('  声: Open JTalk の合成（仮）')
    out = {}
    for i, t in lines(shots):
        # ショットに voice='punch' と書いてあれば、その行だけ別の声色にする
        name = shots[i].get('voice', preset)
        out[i] = _synth(t, NATURAL, PRESETS.get(name, PRESETS[preset]))
    return out


def fit(shots, audio):
    """尺に収まらない行はショットを伸ばす。早口にはしない。

    1行の声が1ショットに収まりきらないときは、次のショットにまたがせる。
    台詞の途中でカットが変わるのは編集としてふつうで、むしろ4秒5秒を
    1枚の絵で持たせるより見やすい。またげるのは「自分の台詞を持たない
    ショット」だけ。声が重なると何も聞き取れなくなる。
    """
    grew = []
    for i, x in audio.items():
        if not len(x):
            continue
        need = HEAD + len(x)/SR + TAIL
        # 次に台詞があるショットの手前まで、この声が使える。
        # ただし章タイトルは「わざと置いた間」なので、そこへは食い込ませない。
        j = i
        while (j + 1 < len(shots) and not len(audio.get(j + 1, ()))
               and shots[j + 1].get('kind') != 'title'
               and not shots[j + 1].get('nospan')):
            j += 1
        room = sum(shots[k]['dur'] for k in range(i, j + 1))
        if room >= need - 0.02:
            continue
        # 足りないぶんは、またいだ最後のショットに足す
        add = need - room
        grew.append((j, shots[j]['dur'], shots[j]['dur'] + add, j != i))
        shots[j]['dur'] = math.ceil((shots[j]['dur'] + add) * 30) / 30.0
    if grew:
        print('  声に合わせて %d ショットを伸ばした' % len(grew))
        for i, a, b, spans in grew:
            flag = '  ← 長い。台本を割ったほうがいい' if b > MAX_DUR else ''
            flag += '（前のショットからまたいでいる）' if spans else ''
            print('    #%02d  %.2f→%.2f秒%s' % (i+1, a, b, flag))
    return shots


def write(path, shots, audio, duration):
    """ショットの頭に貼って1本にまとめる。"""
    import sound
    track = np.zeros(int(SR * duration) + SR)
    for i, x in audio.items():
        if not len(x):
            continue
        m = np.abs(x).max()
        if m > 0:
            x = x * (0.62 / m)
        j = int(SR * (shots[i]['t'] + HEAD))
        track[j:j+len(x)] += x[:max(0, len(track)-j)]
    pk = np.abs(track).max()
    if pk > 0.90:
        track *= 0.90 / pk
    sound.write_wav(path, track[:int(SR*duration)])
    print('  ナレーション %d行 → %s' % (len(audio), path))
    return path


# ------------------------------------------------------------- 口の開き具合

MIN_RUN = 3          # 開き／閉じは最低3コマ続ける（1〜2コマ交互はチラついて読めない）


def envelope(path, fps, duration):
    """1コマごとに「口を開けているか」を返す。

    決まった速さでパクパクさせると、喋っていない間も口が動いて気持ち悪い。
    実際の波形から作れば、黙っているところは閉じたままになる。

    しきい値は声の大きさの中央値に合わせる。固定値にすると、声の録り方で
    「ずっと開きっぱなし」や「ずっと閉じっぱなし」になってしまう。
    """
    try:
        x = read_wav(path)
    except Exception:
        return None
    n = int(duration * fps) + 2
    win = max(1, int(SR / fps))
    env = np.array([np.sqrt(np.mean(x[i*win:(i+1)*win]**2))
                    if len(x[i*win:(i+1)*win]) else 0.0 for i in range(n)])
    voiced = env[env > env.max() * 0.06] if env.max() > 0 else env
    if not len(voiced):
        return np.zeros(n, dtype=bool)
    thr = np.median(voiced)
    # 開くほうは高め、閉じるほうは低めにして、境目でのバタつきを止める。
    # 以前は 1.15 / 0.72 で、喋っている間も口が開くのは34%しかなく、
    # 「たまに動く」ようにしか見えなかった。喋っている所はしっかり開ける。
    hi, lo = thr * 0.92, thr * 0.52
    open_ = np.zeros(n, dtype=bool)
    st = False
    for i, v in enumerate(env):
        st = (v > lo) if st else (v > hi)
        open_[i] = st
    # 短すぎる区間をならす
    i = 0
    while i < n:
        j = i
        while j < n and open_[j] == open_[i]:
            j += 1
        if j - i < MIN_RUN and i > 0:
            open_[i:j] = open_[i-1]
        i = j
    return open_


# ------------------------------------------------------------- 台本の書き出し

def dump_text(shots, path):
    """VOICEVOX に読み込ませる用。1行1台詞、それだけ。"""
    with open(path, 'w', encoding='utf-8') as f:
        for _, t in lines(shots):
            f.write(t + '\n')
    print('  VOICEVOX用のテキスト → %s（%d行）' % (path, len(lines(shots))))
    return path


# ------------------------------------------------------------- 単体で動かす

def demo(path=None):
    import sound
    path = path or os.path.join(HERE, 'voice_demo.wav')
    txt = '飛行機は、空気を下に殴って飛んでる。普通にすごくね。'
    gap = np.zeros(int(SR * 0.6))
    parts = []
    for name in ('ryusei', 'deep', 'otter'):
        parts += [_synth(txt, NATURAL, PRESETS[name]), gap]
    sound.write_wav(path, np.concatenate(parts))
    print('聞き比べ → %s（ryusei / deep / otter の順）' % path)


if __name__ == '__main__':
    if '--demo' in sys.argv:
        if not available():
            raise SystemExit('open_jtalk がありません')
        demo()
    else:
        print(__doc__)
