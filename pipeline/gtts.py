"""Gemini の音声合成でナレーションを作る。

VOICEVOX はこの環境から取れない（配布元も web API も組織ポリシーで 403）。
Open JTalk は動くが、合成くさくて「キャラが喋っている」感じにならない。
Gemini の TTS は同じキーで叩けて、声の指示も日本語で書ける。

  python3 gtts.py --demo        声の候補を並べた聞き比べを書き出す
  python3 gtts.py --voices      使える声の名前を出す

台本側からは voice.py 経由で呼ばれる。
"""
import os, sys, json, wave, time, base64, hashlib, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '.ttscache')
HOST = 'https://generativelanguage.googleapis.com'
MODEL = os.environ.get('GEMINI_TTS_MODEL', 'gemini-3.1-flash-tts-preview')
# 無料枠は「モデルごとに1日いくつ」。1つ尽きても声の名前（Charon）は
# どのモデルにも入っているので、同じ声のまま次のモデルで続けられる。
MODELS = [MODEL] + [m for m in ('gemini-2.5-flash-preview-tts',
                                'gemini-2.5-pro-preview-tts') if m != MODEL]
SR = 24000                      # このモデルが返すのは 24kHz モノラル PCM

# 低めの男声を中心に。gtts.py --demo で聞き比べて選ぶ
VOICES = ['Charon', 'Orus', 'Algenib', 'Rasalgethi', 'Iapetus', 'Sadaltager']
VOICE = os.environ.get('GEMINI_VOICE', 'Charon')

# 声の演技指示。ここが VOICEVOX に無い利点で、行ごとに口調を変えられる
STYLE = ('落ち着いた低い声で、関西弁まじりのタメ口。'
         '友達に教えるように、断言して言い切る。早口すぎない。')
STYLE_PUNCH = ('低い声で、少し前のめりに。決め台詞なので強く言い切る。')


def key():
    """.env はリポジトリの外（~/yt-analysis）に置いてある。"""
    if os.environ.get('GEMINI_API_KEY'):
        return os.environ['GEMINI_API_KEY']
    for p in (os.path.expanduser('~/yt-analysis/.env'),
              os.path.join(HERE, '.env')):
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                k, _, v = line.strip().partition('=')
                if k == 'GEMINI_API_KEY' and v:
                    os.environ['GEMINI_API_KEY'] = v.strip()
                    return v.strip()
    return None


def available():
    return bool(key())


def _post(body, model, timeout=420):
    r = urllib.request.Request(
        HOST + '/v1beta/models/%s:generateContent' % model,
        data=json.dumps(body).encode(), method='POST',
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key()})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.load(resp)


def voiced_seconds(x, sr=None):
    """実際に声が出ている秒数。末尾の長い無音に騙されないため。"""
    sr = sr or SR
    w = int(sr * 0.05)
    n = len(x) // w
    if not n:
        return 0.0
    rms = np.array([np.sqrt(np.mean(x[i*w:(i+1)*w] ** 2)) for i in range(n)])
    if rms.max() <= 0:
        return 0.0
    return float((rms > rms.max() * 0.12).sum()) * 0.05


def say(text, voice=None, style=None, expect=None):
    """1行を合成して float 配列（44.1kHz換算前の 24kHz）で返す。

    同じ台本で何度もレンダリングするので、結果はディスクに残す。
    毎回APIを叩くと遅いし、無料枠もすぐ尽きる。
    """
    voice = voice or VOICE
    style = style or STYLE
    os.makedirs(CACHE, exist_ok=True)
    # expect … だいたい何秒返るはずか。これを外れた音はキャッシュしない。
    # 実際に「6行ぶん頼んだのに3秒だけ喋って215秒の無音」という応答が返り、
    # それがキャッシュに残って、作り直しても同じ壊れた音が出続けた。
    h = hashlib.sha1(('%s|%s|%s|%s' % (MODEL, voice, style, text)).encode()).hexdigest()[:16]
    p = os.path.join(CACHE, h + '.wav')
    if os.path.exists(p):
        with wave.open(p) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype='<i2') / 32768

    body = {'contents': [{'parts': [{'text': style + '\n\n' + text}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {'voiceConfig': {
                    'prebuiltVoiceConfig': {'voiceName': voice}}}}}
    pcm = None
    for mi, model in enumerate(MODELS):
        for attempt in range(3):
            try:
                d = _post(body, model)
            except Exception as e:
                code = getattr(e, 'code', None)
                if code == 429:
                    print('    %s は今日の枠切れ → 次のモデルへ' % model)
                    break
                if attempt == 2 or (code and code not in (500, 503)):
                    print('    TTS失敗(%s): %s' % (model, e))
                    break
                time.sleep(5 * (attempt + 1))
                continue
            try:
                part = d['candidates'][0]['content']['parts'][0]
                blob = part.get('inlineData') or part.get('inline_data')
                pcm = base64.b64decode(blob['data'])
            except (KeyError, IndexError, TypeError):
                pcm = None
            break
        if pcm:
            if mi:
                print('    声: %s で合成（%s は枠切れ）' % (model, MODELS[0]))
            break
    if not pcm:
        return np.zeros(0)
    x = np.frombuffer(pcm, dtype='<i2') / 32768
    if expect and voiced_seconds(x) < expect * 0.45:
        print('    応答が短すぎる（声 %.1f秒 / 期待 %.1f秒）。捨てて作り直す'
              % (voiced_seconds(x), expect))
        return np.zeros(0)              # キャッシュしない
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm)
    return np.frombuffer(pcm, dtype='<i2') / 32768


def say_script(texts, voice=None, style=None, gap='。……………。', batch=7):
    """台本を数回に分けて合成し、無音で切り分ける。

    以前は台本ぜんぶを1リクエストで投げていた。無料枠が1日10回しかないので
    回数を最小にしたかったからだが、20行を1回で投げると切れ目が19か所になり、
    「行間の無音が、行の中の句点の無音より必ず長い」という前提が崩れる。
    実際に1か所ずれて、「飛行機の翼も、」のショットに次の行の
    「これと全く同じ」が乗っていた。

    7行ずつに分けると切れ目は6か所で済み、外しにくい。外しても被害は
    そのまとまりの中だけに収まる。3リクエストなら枠にも収まる。
    """
    out = []
    i = 0
    while i < len(texts):
        n = batch
        segs = None
        # うまくいかなければ、まとまりを小さくして測り直す。
        # 以前は1つでも失敗すると全部を捨てて合成音声に落ちていたが、
        # それだと成功した分まで無駄になり、声が丸ごと別物になってしまう。
        while n >= 1:
            part = texts[i:i+n]
            joined = ('\n' + gap + '\n').join(part)
            x = say(joined, voice=voice, style=style, expect=_expect(part))
            if len(x):
                segs = split_silence(x, len(part)) if len(part) > 1 else [x]
            # 切れたつもりでも、行の長さと釣り合っていなければ外している。
            # 失敗（None）だけを見ていた頃は、ここをすり抜けて動画に乗った。
            if segs is not None and not balanced(part, segs):
                print('    %d〜%d行目の切れ目がずれている' % (i+1, i+len(part)))
                segs = None
            if segs is not None:
                break
            print('    %d〜%d行目がうまく切れない。%d行ずつに縮めて試す'
                  % (i+1, i+len(part), max(1, n // 2)))
            n = n // 2
        if segs is None:
            return None
        out += segs
        i += len(segs)
    return out


def balanced(texts, segs, sr=None):
    """各行の「音の秒数 ÷ 文字数」が揃っているか。1行なら常に真。

    切れ目を1つ外すと、片方が伸びて隣が縮む。比を見れば分かる。
    """
    if len(texts) < 2:
        return True
    sr = sr or SR
    r = [len(x) / sr / max(len(t), 1) for t, x in zip(texts, segs)]
    med = sorted(r)[len(r) // 2]
    if med <= 0:
        return False
    return all(0.5 * med <= v <= 1.9 * med for v in r)


def _expect(part):
    """この行たちなら、だいたい何秒の音が返るはずか。"""
    return sum(len(t) for t in part) * 0.17


def check(texts, segs, sr=None):
    """行の長さと音の長さが釣り合っているかを見る。

    切り分けを外すと、ある行が異様に長く、隣が短くなる。
    黙って書き出すと、そのまま動画に乗ってしまうので、ここで気づけるようにする。
    """
    sr = sr or SR
    r = [len(x) / sr / max(len(t), 1) for t, x in zip(texts, segs)]
    med = sorted(r)[len(r) // 2]
    bad = [(i, texts[i], r[i] / med) for i in range(len(r))
           if r[i] > med * 2.0 or r[i] < med * 0.45]
    for i, t, k in bad:
        print('    %d行目「%s」が中央値の%.1f倍。切り分けを外している疑い'
              % (i + 1, t[:18], k))
    return not bad


def split_silence(x, want, min_gap=0.22):
    """無音の位置で want 個に切る。

    しきい値だけで選ぶと、読点の小さい間まで拾ってしまい数が合わない。
    候補を全部出してから「長い順に want-1 本」を採る。
    行間には「……」を入れて合成しているので、そこが一番長い無音になる。
    """
    win = int(SR * 0.02)
    n = len(x) // win
    rms = np.array([np.sqrt(np.mean(x[i*win:(i+1)*win] ** 2)) for i in range(n)])
    if not n or rms.max() <= 0:
        return None
    loud = rms[rms > rms.max() * 0.02]
    if not len(loud):
        return None
    thr = np.percentile(loud, 12)
    quiet = rms < thr
    need = max(2, int(min_gap / 0.02))

    runs, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if j - i >= need and i > 0 and j < n:
                runs.append((j - i, (i + j) // 2))
            i = j
        else:
            i += 1
    if len(runs) < want - 1:
        return None
    # 長い無音から順に want-1 本。そのあと時間順に並べ直す
    picked = sorted(r[1] for r in sorted(runs, reverse=True)[:want - 1])
    bounds = [0] + [c * win for c in picked] + [len(x)]
    segs = [x[bounds[k]:bounds[k+1]] for k in range(want)]
    # 全部に声が入っているか確認。空の区間があれば失敗扱いにする
    if any(np.abs(sg).max() < 0.01 for sg in segs):
        return None
    return segs


def demo(path=None):
    path = path or os.path.join(HERE, 'voice_demo.wav')
    txt = '飛行機は、翼の形で飛んでるんちゃう。空気を下に殴って飛んでる。'
    gap = np.zeros(int(SR * 0.7))
    parts = []
    for v in VOICES:
        x = say(txt, voice=v)
        if len(x):
            parts += [x, gap]
            print('  %-12s %.1f秒' % (v, len(x) / SR))
    out = np.concatenate(parts) if parts else np.zeros(SR)
    pcm = (np.clip(out, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print('→ %s（%s の順）' % (path, ' / '.join(VOICES)))


if __name__ == '__main__':
    if not available():
        raise SystemExit('GEMINI_API_KEY が見つかりません（~/yt-analysis/.env）')
    if '--voices' in sys.argv:
        print('\n'.join(VOICES))
    else:
        demo()
