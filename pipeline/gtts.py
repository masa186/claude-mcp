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


def _post(body, timeout=240):
    r = urllib.request.Request(
        HOST + '/v1beta/models/%s:generateContent' % MODEL,
        data=json.dumps(body).encode(), method='POST',
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key()})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.load(resp)


def say(text, voice=None, style=None):
    """1行を合成して float 配列（44.1kHz換算前の 24kHz）で返す。

    同じ台本で何度もレンダリングするので、結果はディスクに残す。
    毎回APIを叩くと遅いし、無料枠もすぐ尽きる。
    """
    voice = voice or VOICE
    style = style or STYLE
    os.makedirs(CACHE, exist_ok=True)
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
    for attempt in range(5):
        try:
            d = _post(body)
            break
        except Exception as e:
            code = getattr(e, 'code', None)
            if attempt == 4 or (code and code not in (429, 500, 503)):
                print('    TTS失敗: %s' % e)
                return np.zeros(0)
            time.sleep(5 * (attempt + 1))
    try:
        part = d['candidates'][0]['content']['parts'][0]
        blob = part.get('inlineData') or part.get('inline_data')
        pcm = base64.b64decode(blob['data'])
    except (KeyError, IndexError, TypeError):
        return np.zeros(0)
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm)
    return np.frombuffer(pcm, dtype='<i2') / 32768


def say_script(texts, voice=None, style=None, gap='。……。'):
    """台本ぜんぶを1回で合成して、無音で切り分ける。

    無料枠はこのモデルで1日10リクエストしかない。1行1リクエストだと
    20行の台本で即座に尽きる。まとめて投げて、あとで切る。
    行間に「……」を入れておくと、そこに分かりやすい間ができる。
    """
    joined = ('\n' + gap + '\n').join(texts)
    x = say(joined, voice=voice, style=style)
    if not len(x):
        return None
    segs = split_silence(x, len(texts))
    if segs is None:
        print('    切り分け失敗（%d行に分けられなかった）' % len(texts))
        return None
    return segs


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
