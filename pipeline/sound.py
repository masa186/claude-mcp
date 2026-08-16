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
import os, wave, argparse, math, glob
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


def reveal(v=0):
    """答え・否定が出る瞬間の「キラン」。倍音を整数比から少しずらして、
    ベルにも金物にも寄りすぎない位置に置く。"""
    n = int(SR * 0.55)
    y = modal(n, (1180 + 30*v, 1790, 2410, 3260, 4380),
                 (0.55, 0.40, 0.26, 0.15, 0.08),
                 (5.0, 6.5, 8.5, 11.0, 15.0))
    y += modal(n, (590, 880), (0.22, 0.14), (4.0, 5.5))     # 下の芯
    y *= env(n, 0.002, 0.9)
    return tail(lowpass(y, 6200), (0.031, 0.057, 0.092), (0.30, 0.20, 0.12)) * 0.40


def impact(v=0):
    """オチの一撃。ドンより重く、余韻を長めに取る。"""
    n = int(SR * 0.70)
    t = np.arange(n) / SR
    f = (150 + 14*v) * np.exp(-t * 11) + 52
    sub = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 4.2)
    body = modal(n, (240, 390, 620, 1050), (0.5, 0.34, 0.22, 0.12), (9, 13, 18, 26))
    hit = lowpass(bandnoise(int(SR*0.07), 700, 2600, 0.45, 41 + v), 2400)
    y = sub * 0.62 + body * 1.1
    y[:len(hit)] += hit * 0.34
    y = lowpass(y * env(n, 0.002, 1.2), 4200)
    return tail(y, (0.034, 0.061, 0.098), (0.36, 0.24, 0.15)) * 0.55


def rise(v=0):
    """溜め。次に何か出るぞ、と思わせる上昇音。"""
    n = int(SR * 0.85)
    t = np.arange(n) / SR
    f = 260 + 520 * (t / t[-1]) ** 1.7
    y = np.sin(2 * math.pi * np.cumsum(f) / SR) * 0.5
    y += np.sin(2 * math.pi * np.cumsum(f * 1.5) / SR) * 0.22
    y += lowpass(bandnoise(n, 900, 3400, 0.35, 53 + v), 3600) * 0.5
    y *= np.linspace(0, 1, n) ** 1.4
    y[-int(SR*0.06):] *= np.linspace(1, 0, int(SR*0.06))
    return tail(lowpass(y, 5200), (0.026, 0.048), (0.22, 0.13)) * 0.34


def pa(v=0):
    """文字が出る瞬間の「パッ」。伸びているショート40本のうち20本で聞こえた音。

    黒板のチョーク音は、実際にチョークで書いている board のときだけ使う。
    stage の行は板の上に浮いている字なので、擦れではなく破裂音のほうが合う。
    ポンより短く、キランより低い。ここが空いていた。
    """
    n = int(SR * 0.14)
    click = lowpass(bandnoise(int(SR*0.012), 1800, 6000, 0.5, 61 + v), 7000)
    body = modal(n, (900 + 40*v, 1520, 2340), (0.55, 0.30, 0.16), (34, 46, 62))
    y = body * env(n, 0.001, 2.6)
    y[:len(click)] += click * 0.42
    return tail(lowpass(y, 7000), (0.011, 0.021), (0.20, 0.11)) * 0.30


def dodon(v=0):
    """決め台詞の「ドドン」。40本の記録では、決め台詞に低音の二連打が15本、
    キランが10本。こちらは一撃しか持っていなかったので足す。"""
    gap = int(SR * 0.115)
    a, b = impact(v), impact(v + 1)
    n = gap + len(b)
    y = np.zeros(n)
    y[:len(a)] += a * 0.72          # 1発目は軽く
    y[gap:gap+len(b)] += b          # 2発目で決める
    return y * 0.86


VARIANTS = 3          # 毎回まったく同じ波形だと機械っぽく聞こえる

SE_DIR = os.path.join(HERE, 'se')

# 本物の効果音があればそちらを使う。合成音はあくまで代役。
#   se/whoosh.wav  カットの切り替わり・映像が入る
#   se/pop.wav     文字・図が出る
#   se/don.wav     章の切り替わり・重要な答え
#   se/tap.wav     指し棒で黒板を叩く
#   se/rise.wav    溜め（ズームの前）
#   se/reveal.wav  答え・否定が出る（キラン）
#   se/impact.wav  オチの一撃
REAL = dict(whoosh='whoosh.wav', chalk='pop.wav', don='don.wav',
            ton='tap.wav', rise='rise.wav', pa='pa.wav', dodon='dodon.wav',
            reveal='reveal.wav', impact='impact.wav')


def load_wav(path):
    """44.1kHz モノラルに揃えて読む。"""
    with wave.open(path, 'rb') as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:                                   # 直線補間で十分
        x = np.interp(np.linspace(0, len(x)-1, int(len(x)*SR/sr)),
                      np.arange(len(x)), x)
    return x


# 役割ごとの最大の長さ。効果音は0.75秒に1回鳴るので、長い音をそのまま
# 重ねると濁る。頭を残して尻をフェードで落とす。
MAXLEN = dict(whoosh=0.70, chalk=0.45, don=1.20, ton=0.50, rise=1.60,
              reveal=1.10, impact=1.40, pa=0.35, dodon=1.60)


def trim(x, sec):
    n = int(SR * sec)
    if len(x) <= n:
        return x
    y = x[:n].copy()
    f = int(SR * 0.08)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def real_se(kind):
    """se/pop.wav / se/pop2.wav / se/pop3.wav … と置くと順番に鳴らす。
    同じ波形が延々続くと、効果音は「癖」として耳につく。
    増やしたいときはファイルを足すだけでいい。"""
    f = REAL.get(kind)
    if not f:
        return None
    base = os.path.splitext(f)[0]
    xs = []
    for p in sorted(glob.glob(os.path.join(SE_DIR, base + '*.wav'))):
        try:
            xs.append(load_wav(p))
        except Exception:
            pass
    return xs or None


# ------------------------------------------------------------- 配置

def se_events():
    """(秒, 音の種類) を SHOTS から作る。

    伸びているショート40本を1本ずつ聞いた記録（~/yt-analysis/data/sound.md）で
    分かったこと:
      ・音を置く瞬間は「文字が出る時」40/40、「画面が切り替わる時」38/40。
        つまりカットには例外なく音が付いている
      ・頻度は 1.1〜1.5秒に1回が最多（12本）。こちらは 2.2秒に1回で遅かった
      ・決め台詞は低音の二連打（ドドン）15本 ＞ キラン 10本
    以前は「意味のあるところだけ鳴らす」にしていたが、それは鳴らしすぎを
    避けるための判断で、実測は逆だった。カットには必ず音を置く。

      whoosh … 何かが入ってくる／動く（スクリーンが降りる・映像が入る）
      pa     … 板の上に浮いた文字が出る（40本中20本で聞こえた「パッ」）
      chalk  … 黒板にチョークで書かれる。board のときだけ
      dodon  … 決め台詞の二連打
      reveal … 答え・否定が出る（キラン）
    """
    ev = []
    for i, s in enumerate(render.SHOTS):
        k = s['kind']
        n0 = len(ev)
        # 明示指定が最優先
        if 'se' in s:
            if s['se']:
                ev.append((s['t'] + s.get('se_at', 0.02), s['se']))
        elif k == 'screen' and s.get('roll', True):
            ev.append((s['t'] + 0.02, 'whoosh'))      # スクリーンが降りてくる
        elif k == 'title':
            ev.append((s['t'] + 0.02, 'don'))         # 章が変わる
        elif s.get('board'):
            ev.append((s['t'] + render.LEADIN, 'chalk'))   # チョークで書く
        elif s.get('add'):
            # 文字が主役。図も同時に入るが、音は文字に当てる。
            # 図の「シュッ」を先に取ると、40本すべてがやっていた
            # 「文字が出る瞬間の音」が消えてしまう（13ms差は同じ音に聞こえる）。
            ev.append((s['t'] + render.LEADIN, 'pa'))
        elif s.get('fig'):
            ev.append((s['t'] + 0.02, 'whoosh'))      # 図だけのときは図に当てる
        # se=None と自分で書いたショット以外は、カットに必ず音を置く。
        # 38/40 がそうしていた。ここが頻度の差になっていた。
        if len(ev) == n0 and s.get('se', True) is not None:
            ev.append((s['t'] + 0.02, 'whoosh'))

        # se_more=[(秒, 種類), ...] … 1ショットの途中で追加で鳴らす。
        # 絵が2秒動き続けるのに音が頭の1発だけだと、目と耳がばらばらに感じる。
        for at, name in s.get('se_more', ()):
            if at < s['dur'] - 0.06:
                ev.append((s['t'] + at, name))

        if s.get('beat'):
            ev.append((s['t'] + s.get('beat_at', 0.34), 'don'))
        if s.get('tap'):
            ev.append((s['t'] + 0.34, 'ton'))
        # 2つ目以降の要素が出るときだけ、追加でポンを鳴らす
        rows = len(s.get('board') or []) + (1 if s.get('fig') else 0)
        for ri in range(1, rows):
            at = s['t'] + render.LEADIN + ri * render.STAGGER
            if at < s['t'] + s['dur'] - 0.06:
                ev.append((at, 'chalk' if s.get('board') else 'pa'))

        # 文字が出るコマに必ず音を置く。
        # 伸びているショート30本を1本ずつ見た記録で、「プロっぽさ」の
        # 一番の理由に挙がったのが『映像・文字・効果音がぴたりと合っている』
        # （10本）だった。ここまでの分岐だと、fig や se を明示したショットの
        # 文字は無音で出てしまう。同じ時刻に既に音があるときだけ足さない。
        if s.get('add'):
            at = s['t'] + render.LEADIN
            if not any(abs(at - e[0]) < 0.10 for e in ev):
                ev.append((at, 'pa'))
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

    banks = {}
    used_real = []
    for k, f, pk in (('whoosh', whoosh, 0.36), ('don', don, 0.50),
                     ('ton', ton, 0.55), ('chalk', chalk, 0.26),
                     ('reveal', reveal, 0.42), ('impact', impact, 0.58),
                     ('rise', rise, 0.40), ('pa', pa, 0.30),
                     ('dodon', dodon, 0.60)):
        rs = real_se(k)
        if rs is not None:
            bank = []
            for r in rs:
                r = trim(r, MAXLEN.get(k, 0.8))
                m = np.abs(r).max()
                bank.append(r * (pk / m) if m > 0 else r)  # 音量だけ揃える。加工しない
            banks[k] = bank
            used_real.append((k, len(bank)))
        else:
            banks[k] = [shape(f(v), peak=pk) for v in range(VARIANTS)]
    build_track.used_real = used_real
    for j, (t, kind) in enumerate(se_events()):
        bank = banks[kind]
        s = bank[j % len(bank)]                # 合成音のときは変種を巡回させる
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
# 曲は1本しかないので、切り替えの代わりに音量で起伏をつける。
# 「否定」で一度沈めて、「解決編」で上げると、同じ曲でも展開が出る。
_LEVELS = [
    ('hook',    0.10, 'フック — かなり絞る。声に集中させる'),
    ('setup',   0.16, '問い — 軽快に、邪魔をしない'),
    ('how',     0.13, '勘違いの提示 — 一度沈める'),
    ('proof',   0.20, '反証 — 上げる。ここが山のひとつ'),
    ('example', 0.20, '体の記憶 — そのまま'),
    ('bridge',  0.24, '橋 — 解決編に入るので上げる'),
    ('lift',    0.28, '本題 — 一番上げる'),
    ('punch',   0.30, 'オチ — 最大（直前の title で一度絞る）'),
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
        if key == 'punch' and plan:
            # オチの直前をひと呼吸だけ絞る。無音にはしない。
            # 以前は「つまり」の暗転のあいだ絞っていたが、その暗転を外したので
            # 尺をショットから取ると、オチ本体をまるごと絞ってしまう。
            # 前の区間の尻を削る形に変えた。
            duck = 0.35
            ps, pe, plv, pw = plan[-1]
            if pe - ps > duck:
                plan[-1] = (ps, pe - duck, plv, pw)
                plan.append((pe - duck, pe, 0.07, 'オチ直前 — ひと呼吸絞る'))
        plan.append((start, end, lv, why))
    return plan


BGM_PLAN = bgm_plan()


def volume_expr(scale=1.0):
    """ffmpeg の volume= にそのまま貼れる式を作る。
    scale は全体の掛け算。声を乗せるときは 0.6 くらいまで下げる。"""
    e = '%.2f' % (BGM_PLAN[-1][2] * scale)
    for a, b, v, _ in reversed(BGM_PLAN[:-1]):
        e = "if(lt(t,%.2f),%.2f,%s)" % (b, v * scale, e)
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
    real = dict(getattr(build_track, 'used_real', []))
    名 = dict(whoosh='シュッ', chalk='ポン', don='ドン', ton='コツ',
              reveal='キラン', impact='ドンッ', rise='溜め')
    if real:
        print('  本物の音を使用: ' + '  '.join(
            名.get(k, k) + ('（%d種）' % n if n > 1 else '') for k, n in real.items()))
    if len(real) < len(名):
        print('  合成音のまま: ' + '  '.join(名[k] for k in 名 if k not in real))
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
    print('\n※ BGMは bgm.mp3 の1曲。オチで曲を変えない代わりに、')
    print('  オチ直前で7%まで絞ってから26%に上げる落差で持ち上げる。')


if __name__ == '__main__':
    main()
