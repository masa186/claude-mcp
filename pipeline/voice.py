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
    # フリ（疑問）。結論ほど張らず、地の文より少し抑揚を付ける
    'ask':    dict(a=0.60, fm=-2.0, jf=1.45),
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

# 読み方ごとの「タメ」と「速さ」。
# 合成の指示文だけでは差が耳に届かなかった（語尾 +1.8半音 / 0.0 / +1.7半音
# まで測れているのに「声が変わってない」と言われた）。
#
# 伸びているショート41本のナレーションを1本ずつ聞いて数えたら、決め台詞を
# 立てている手はこうだった（複数回答）:
#     声が大きい 33本 / 直前に間 32本 / 直後に間 18本 / ゆっくり 17本
#     速い 3本 / 変わらない 1本
# 一番長い無音は中央値 0.5秒で、置き場所は決め台詞の前が最多（15本）。
# 全体の喋る速さは「速い」が30/41本。
# 高い11本／低い9本と割れていたので、高さは追わない。半音や dB より、
# 間と速さのほうがはるかに効く。ここは合成に頼らず自分で作る。
# 実測の中央値は 0.5秒だが、向こうは1本に決め台詞が1つ。こちらは9つあるので
# 全部に 0.5秒を入れると間延びして、逆にどれも立たなくなる。
# 既定は短くしておいて、本当の山だけ台本側で tame=0.45 と書いて伸ばす。
PAUSE = {'punch': 0.20, 'ask': 0.12}     # 喋り出す前に置く無音
HOLD  = {'punch': 0.30, 'ask': 0.18}     # 言い終わってから次に行くまでの無音
# 速さの加工はやめた（全部 1.0）。
# 「まだ声が混じって聞こえる」と言われて、原因を1つずつ潰していった:
#   モデル違い  → いまの19行は全部 gemini-3.1-flash-tts-preview。揃っている
#   演技指示違い → いまは1種類だけ。揃っている
#   録音回の違い → まとまりどうしの距離 0.32 に対し、まとまりの中のばらつき
#                  0.53。回ごとに声が変わってはいない
#   WSOLA のざらつき → 周期成分と雑音の比は +0.7dB で、むしろ良くなっている
# ここまでで、こちらがいじれる所は全部つぶれた。それでも聞こえるなら、
# 残っているのは合成そのもののブレ。だったら波形に触る加工は外しておく。
# 決め台詞は「間」と「音量」で立てる。実測でも上位はその2つだった
# （声が大きい33本 / 直前に間32本 / ゆっくりは17本）。
# 間は無音を置くだけ、音量は掛けるだけで、どちらも声そのものは変わらない。
RATE  = {'punch': 1.0, 'ask': 1.0, None: 1.0}


def _head(shot):
    """カットの頭から喋り出すまでの秒数。決め台詞の前だけ長く取る。"""
    if 'head' in shot:
        return shot['head']      # 台本が明示している所は動かさない（冒頭の0秒など）
    return HEAD + shot.get('tame', PAUSE.get(shot.get('voice'), 0.0))


def _tail(shot):
    """言い終わってから次のカットまでに残す無音。"""
    return max(TAIL, HOLD.get(shot.get('voice'), 0.0))


def stretch(x, rate, win=2048, tol=600):
    """速さだけ変える。声の高さは変えない。

    はじめは間引き／水増しで済ませていたが、それだと速さと一緒に高さも
    動く。0.92倍にすると声が 1.3半音下がり、地の文（そのまま）と決め台詞が
    交互に来ると、行ごとに声の高さが変わって「同じ人が喋っていない」
    ように聞こえた。実際に聞いた人の「ごちゃごちゃ」はこれ。

    波形を窓で切って、貼る位置を少しずらしながら重ねていく（WSOLA）。
    貼る先は、直前の窓のつづきと一番よく合う所を相関で探す。周期を
    崩さずに詰めたり伸ばしたりできるので、高さは変わらない。
    """
    if rate == 1.0 or len(x) < win * 2:
        return x
    hs = win // 2                      # 貼る側の歩幅（固定）
    ha = int(round(hs * rate))         # 拾う側の歩幅。rate>1 で大きい＝速くなる
    w = np.hanning(win)
    n = int(len(x) / rate) + win
    out, norm = np.zeros(n), np.zeros(n)
    ref = x[hs:hs + win].copy()        # 次に来るはずの波形
    p, j = 0, 0
    while p + win < len(x) and j + win < n:
        lo = max(0, p - tol)
        hi = min(len(x) - win, p + tol)
        if hi > lo:
            # lo〜hi のどこに貼るのが一番なめらかか、まとめて相関を取る
            c = np.correlate(x[lo:hi + win], ref, 'valid')
            k = lo + int(np.argmax(c))
        else:
            k = min(p, max(0, len(x) - win))
        out[j:j + win] += x[k:k + win] * w
        norm[j:j + win] += w
        ref = x[k + hs:k + hs + win]
        if len(ref) < win:             # 端。次の窓が作れないので終わり
            break
        j += hs
        p = k + ha
    norm[norm < 1e-6] = 1.0
    return (out / norm)[:int(len(x) / rate)]
MAX_DUR = 4.2        # これ以上長いショットは絵がもたない。台本を割るべき合図


def available():
    return bool(OJT) and os.path.exists(DIC) and os.path.exists(HTS)


# 合成音声が読み違える語。画面に出す字は変えず、読ませる字だけ差し替える。
# 「逆さま」を「ぎゃくさま」と読んでいた。
YOMI = {'逆さま': 'さかさま'}


def clean(text):
    """テロップ用の { } を外し、読み上げに向かない記号を落とす。"""
    t = text.replace('{', '').replace('}', '').replace('\n', '、')
    t = t.replace('bro、', 'ブロ、').replace('bro', 'ブロ')
    for a, b in YOMI.items():
        t = t.replace(a, b)
    t = re.sub(r'[「」『』]', '', t)
    return t.strip()


def lines(shots):
    """(ショット番号, 読む文) を返す。say があれば say、無ければ tele。

    mute=True のショットは字だけ出して読まない。前の行の声がまたいで
    くる「間」のカットに使う。声を持たないカットでも画面から字が
    消えないので、決め台詞の途中で切り替えても読む物が残る。
    """
    out = []
    for i, s in enumerate(shots):
        if s.get('mute'):
            continue
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


MAXGAP = 0.20        # 台詞の途中に許す無音の長さ（秒）


def squeeze(x, thr=0.010, maxgap=MAXGAP):
    """台詞の途中の長すぎる無音を詰める。

    合成音声は、句読点のところで実際の人よりずっと長く止まることがある。
    「その分だけ、翼は上に持ち上がる。」に0.65秒の空白が入っていて、
    そのせいでショットが5.3秒に伸び、そこが動画で一番止まって見える区間に
    なっていた。喋っていない時間を削るだけなので、声そのものは変わらない。
    """
    if not len(x):
        return x
    w = int(SR * 0.02)
    n = len(x) // w
    if n < 2:
        return x
    rms = np.array([np.sqrt(np.mean(x[i*w:(i+1)*w] ** 2)) for i in range(n)])
    if rms.max() <= 0:
        return x
    quiet = rms < max(thr, rms.max() * 0.06)
    keep = np.ones(n, dtype=bool)
    lim = max(1, int(maxgap / 0.02))
    i = 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if j - i > lim:
                keep[i + lim // 2: j - (lim - lim // 2)] = False
            i = j
        else:
            i += 1
    if keep.all():
        return x
    return np.concatenate([x[i*w:(i+1)*w] for i in range(n) if keep[i]])


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


LINE_DIR = os.path.join(HERE, '.voicelines')

# 画面に出す読み方の名前
STYLE_NAME = {'': '地の文', 'ask': 'フリ（疑問）', 'punch': 'オチ（結論）'}


def _who_of(shot):
    """そのショットを喋るのは誰か。ショットに who='viewer' と書けば視聴者役。

    合成の指示文で読み方を分けると声そのものが別人になってしまった（前の
    コミット）。だったら初めから「別人が喋る」形にしたほうが筋が通る。
    実測でも、伸びているショート41本のうち20本が2人以上で喋っていた。
    """
    import gtts
    return gtts.VOICE_VIEWER if shot.get('who') == 'viewer' else gtts.VOICE


def mouth_mute(shots):
    """カワウソ以外が喋っている時間帯。render.MOUTH_MUTE に入れる。"""
    return [(s['t'], s['t'] + s['dur'])
            for s in shots if s.get('who') == 'viewer']


def _style_of(shot):
    """ショットの voice= を、演技指示の名前に直す。書いてなければ地の文。"""
    import gtts
    name = shot.get('voice')
    return name if name in gtts.STYLES else ''


def _line_file(text, style='', model=None, who=None):
    import gtts, hashlib
    # 地の文の鍵は昔の形のまま。ここに空の style を足すと、すでに録った
    # 行が全部ハッシュ違いになり、直していない行まで作り直しになる。
    k = '%s|%s|%s' % (model or gtts.MODEL, who or gtts.VOICE, text)
    if style:
        # 鍵に入れるのは演技指示の「中身」。名前（'ask'）だけで作ると、
        # 指示を書き直しても古い音を引き当ててしまい、直したつもりで
        # 何も変わらない。中身で作れば、書き直した読み方だけ録り直る。
        k += '|' + gtts.STYLES.get(style, style)
    return os.path.join(LINE_DIR, hashlib.sha1(k.encode()).hexdigest()[:16] + '.wav')


def _ltas(x, nb=32):
    """長時間平均スペクトル。声の持ち主の癖が出る。行の長さに引きずられにくい。"""
    v = x[np.abs(x) > 0.01]
    if len(v) < 4096:
        return None
    W = 2048
    w = np.hanning(W)
    acc = np.zeros(W // 2 + 1)
    n = 0
    for i in range(0, len(v) - W, W // 2):
        acc += np.abs(np.fft.rfft(v[i:i + W] * w))
        n += 1
    S = acc / n
    fr = np.fft.rfftfreq(W, 1 / SR)
    ed = np.logspace(np.log10(80), np.log10(8000), nb + 1)
    e = np.log10(np.array([S[(fr >= a) & (fr < b)].sum()
                           for a, b in zip(ed[:-1], ed[1:])]) + 1e-9)
    return (e - e.mean()) / (e.std() + 1e-9)


def takes(text, style_texts):
    """その台詞について手元にある録音を全部返す。

    同じ台詞でも、モデル・演技指示・声名の組み合わせのぶんだけ別々に
    録れている。どれか1つしか見ないと、たまたま別人の回を掴む。
    """
    import gtts, hashlib
    out = []
    for m in gtts.MODELS:
        for st in [''] + list(style_texts):
            for w in {gtts.VOICE, gtts.VOICE_VIEWER}:
                k = '%s|%s|%s' % (m, w, text)
                if st:
                    k += '|' + style_texts[st]
                f = os.path.join(LINE_DIR,
                                 hashlib.sha1(k.encode()).hexdigest()[:16] + '.wav')
                if os.path.exists(f):
                    out.append(f)
    return out


def pick_takes(texts, style_texts):
    """行ごとに録音が何本かあるとき、一番そろう組み合わせを選ぶ。

    録り直せない日の逃げ道。1本の中で声が変わるのが一番聞き苦しいので、
    「どの回を使うか」だけで、そろい方をできるだけ良くする。
    全体の平均に近い回を各行で選び、平均を取り直す、を繰り返す。
    """
    cand = []
    for t in texts:
        fs = takes(t, style_texts)
        vs = [(f, _ltas(read_wav(f))) for f in fs]
        cand.append([(f, v) for f, v in vs if v is not None])
    if not any(len(c) > 1 for c in cand):
        return None
    sel = [c[0] for c in cand if c]
    for _ in range(8):
        c0 = np.mean([v for _, v in sel], 0)
        new = []
        for c in cand:
            if not c:
                continue
            new.append(min(c, key=lambda fv: float(np.linalg.norm(fv[1] - c0))))
        if [f for f, _ in new] == [f for f, _ in sel]:
            break
        sel = new
    c0 = np.mean([v for _, v in sel], 0)
    d = float(np.mean([np.linalg.norm(v - c0) for _, v in sel]))
    return [f for f, _ in sel], d


def _borrow(have, k, texts, raw, sty, who, model=None):
    """枠が尽きて録り直せない行を、前に録った近い音で埋める。

    読み方が違っても、無音や Open JTalk の合成音に落ちるよりはましで、
    しかも「その行だけ声が別人」にならない。枠が戻った日に録り直せば済む。
    """
    for t, st, why in ((raw[k], sty[k], '読みを直す前の音'),
                       (texts[k], '', '前の読み方の音'),
                       (raw[k], '', '前の読み方の音')):
        if (t, st) == (texts[k], sty[k]):
            continue
        g = _line_file(t, st, model, who[k])
        if os.path.exists(g):
            have[k] = read_wav(g)
            print('    %d行目は%sで代用（枠が戻ったら録り直す）' % (k + 1, why))
            return True
    return False


def _save_line(path, x):
    os.makedirs(LINE_DIR, exist_ok=True)
    import sound
    sound.write_wav(path, x)


def from_gemini(shots):
    """Gemini の音声合成。Open JTalk より人の声に近いので、あればこちらを使う。

    行ごとにディスクへ残す。以前はまとめて投げた「かたまり」単位でしか
    キャッシュしていなかったので、台本の1語を直すと全行が作り直しになり、
    1日10回の枠にすぐぶつかっていた。行単位なら、直した行だけ録り直せる。
    """
    try:
        import gtts
    except Exception:
        return None
    if not gtts.available():
        return None
    ls = lines(shots)
    texts = [t for _, t in ls]
    sty = [_style_of(shots[i]) for i, _ in ls]
    who = [_who_of(shots[i]) for i, _ in ls]
    # 読みを直す前の文でも引けるようにしておく。枠が尽きて録り直せない日でも、
    # 前の音（読みは違うが中身はある）で穴を空けずに書き出せる。
    keep, globals()['YOMI'] = YOMI, {}
    raw = [t for _, t in lines(shots)]
    globals()['YOMI'] = keep
    # 1本の中の全部の行を、必ず「同じ1つのモデル」から取る。
    # 声の名前（Charon）が同じでも、モデルが違えば別人の声になる。
    # 行ごとに枠切れで別のモデルへ落ちていたせいで、22行の高さが
    # 85〜223Hz（16.7半音）に散らばり、1本の中に3人の男の声が混ざっていた。
    #
    # 「手持ちが一番多いモデル」を選ぶのでは駄目だった。手持ちが多いのは
    # 昨日まで使っていたモデルで、そのモデルは今日の枠が尽きている。
    # 全部を揃えられるモデルを順に探して、最初に揃った所で止める。
    best = None
    for model in gtts.MODELS:
        have, missing = {}, []
        for k, t in enumerate(texts):
            f = _line_file(t, sty[k], model, who[k])
            if os.path.exists(f):
                have[k] = read_wav(f)
            else:
                missing.append(k)
        if missing:
            print('  %s: %d行はそのまま使い、%d行を作る'
                  % (model, len(have), len(missing)))
            # 読み方ごとにまとめて投げる。1リクエストに付けられる演技指示は
            # 1つだけなので、疑問と結論を同じ塊に混ぜると片方の指示が消える。
            # 1リクエストに乗せられる声は1つ、演技指示も1つ。
            # 「誰が喋るか」と「読み方」の組ごとにまとめて投げる。
            for key in sorted(set((who[k], sty[k]) for k in missing)):
                w, name = key
                grp = [k for k in missing if (who[k], sty[k]) == key]
                print('    %s / %s %d行'
                      % (w, STYLE_NAME.get(name, name), len(grp)))
                segs = gtts.say_script([texts[k] for k in grp], voice=w,
                                       style=gtts.STYLES.get(name), model=model)
                if segs is None:
                    continue
                for k, x in zip(grp, segs):
                    y = squeeze(trim_silence(resample(x, gtts.SR), 0.010))
                    _save_line(_line_file(texts[k], sty[k], model, w), y)
                    have[k] = y
        if best is None or len(have) > len(best[1]):
            best = (model, have)
        if len(have) == len(texts):
            print('  声のモデル: %s（%d行すべて同じ声）' % (model, len(texts)))
            return {i: have.get(k, np.zeros(0)) for k, (i, _) in enumerate(ls)}
        print('  %s では %d/%d行どまり。次のモデルを試す'
              % (model, len(have), len(texts)))

    # どのモデルでも全部は揃わなかった。ここで行ごとに手当たり次第
    # 埋めると、同じ役割の行どうしで声が変わって一番ばらばらに聞こえる。
    # せめて「読み方ごとに1つのモデル」へ寄せる。地の文はこの声、
    # 決め台詞はこの声、と筋が通っていれば聞ける。
    have, used = dict(best[1]), {}   # {} に作り直すと、取れていた行を捨ててしまう
    for key in sorted(set(zip(who, sty))):
        w, name = key
        grp = [k for k in range(len(texts)) if (who[k], sty[k]) == key]
        for m in gtts.MODELS:
            fs = [_line_file(texts[k], name, m, w) for k in grp]
            if all(os.path.exists(f) for f in fs):
                for k, f in zip(grp, fs):
                    have[k] = read_wav(f)
                used['%s/%s' % (w, STYLE_NAME.get(name, name))] = m
                break
    for k in range(len(texts)):
        if k not in have:
            _borrow(have, k, texts, raw, sty, who, best[0])
    if not have:
        return None
    if used:
        print('  声が %d種類に分かれた（今日の枠では1種類に揃えられない）:'
              % len(set(used.values())))
        for name, m in used.items():
            print('    %-10s %s' % (STYLE_NAME.get(name, name), m))
    if len(have) < len(texts):
        n = len(texts) - len(have)
        print('  ※ %d行が埋まらなかった' % n)
        # 埋まらない行はそのまま無音になる。17/22行が無音の動画を
        # 書き出してしまったので、ここで止める。
        if n > len(texts) * 0.25 and os.environ.get('ALLOW_GAPS') != '1':
            raise SystemExit(
                '\n%d/%d行が無音になります。書き出しを止めました。'
                '\nGemini の枠が戻ってから、もう一度走らせてください。'
                '\n（穴あきのまま書き出すなら ALLOW_GAPS=1 を付ける）'
                % (n, len(texts)))
    print('  ※ 枠が戻った日にもう一度走らせると、1つのモデルに揃う')
    return {i: have.get(k, np.zeros(0)) for k, (i, _) in enumerate(ls)}


def shape(shots, audio):
    """読み方ごとに速さを変える。合成し直さずに付けられる差。

    キャッシュには素のままの音を残しておいて、ここで毎回かけ直す。
    加工した音を残すと、匙加減を変えるたびに録り直しになる。
    """
    n = 0
    for i, x in list(audio.items()):
        r = RATE.get(shots[i].get('voice'), 1.0)
        if r != 1.0 and len(x):
            audio[i] = stretch(x, r); n += 1
    if n:
        print('  %d行の速さを読み方に合わせて変えた' % n)
    return audio


def collect(shots, preset=DEFAULT):
    """各行の音を用意する。自分で録った声 > VOICEVOX > Gemini > Open JTalk。"""
    vv = from_voicevox(shots)
    if vv is not None:
        print('  声: VOICEVOX（voicevox/ の %d本）' % len(vv))
        return shape(shots, vv)
    g = from_gemini(shots)
    if g is not None:
        print('  声: Gemini の音声合成（%d行）' % len(g))
        return shape(shots, g)
    if not available():
        return {}
    if os.environ.get('ALLOW_ROBOT') != '1':
        # ここへ落ちたことに気づかずに書き出して、ロボット声のまま動画を
        # 出してしまった。合成できなかったら止める。どうしても仮の音で
        # 確認したいときだけ ALLOW_ROBOT=1 を付ける。
        raise SystemExit(
            '\n合成音声が1行も取れませんでした。'
            '\nGemini の枠が戻ってから、もう一度走らせてください。'
            '\n（仮のロボット声で書き出すなら ALLOW_ROBOT=1 を付ける）')
    print('  声: Open JTalk の合成（仮。ALLOW_ROBOT=1 が付いている）')
    out = {}
    for i, t in lines(shots):
        # ショットに voice='punch' と書いてあれば、その行だけ別の声色にする
        name = shots[i].get('voice', preset)
        out[i] = _synth(t, NATURAL, PRESETS.get(name, PRESETS[preset]))
    return shape(shots, out)


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
        need = _head(shots[i]) + len(x)/SR + _tail(shots[i])
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


# 読み方ごとの音量。1.8dB では足りなかった。実測で一番多い手（33/41本）が
# 「声が大きい」なので、ここを 3.7dB まで広げる。
# フリは地の文と同じ音量に置く。フリは語尾の上がりで、オチは音量と間で、
# それぞれ違う手を使って目立たせる。3つを同じ手で並べても段にならない。
LEVEL = {'punch': 0.92, 'ask': 0.60, None: 0.60}


def write(path, shots, audio, duration):
    """ショットの頭に貼って1本にまとめる。"""
    import sound
    track = np.zeros(int(SR * duration) + SR)
    for i, x in audio.items():
        if not len(x):
            continue
        m = np.abs(x).max()
        if m > 0:
            # 読み方に合わせて音量も段を付ける。全部同じだと、どこが山か
            # 耳で分からない。フリは結論の一段下に置いて、落差を作る。
            x = x * (LEVEL.get(shots[i].get('voice'), LEVEL[None]) / m)
        # 21本中20本が0秒から喋り始めていた。冒頭だけ head=0 にできる
        j = int(SR * (shots[i]['t'] + _head(shots[i])))
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
