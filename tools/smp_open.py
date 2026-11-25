"""YouTube の動画の最初の数秒だけを Gemini に見せて、冒頭のナレーション字幕と上部タイトルを書き出させる。

    python3 tools/smp_open.py <ids.json> <書き出し先.json> [秒数=8]

ids.json は [{"id":..., ...}, ...]。済んだものは飛ばすので、止まってもやり直せる。
"""
import os, sys, json, time, urllib.request, urllib.error

HOST = 'https://generativelanguage.googleapis.com'
MODELS = os.environ.get('GEMINI_MODELS', 'gemini-3-flash-preview,gemini-3.5-flash,gemini-3.6-flash,'
                        'gemini-3.8-flash,gemini-flash-lite-latest,gemini-3.5-flash-lite').split(',')
PROMPT = """これは日本語の YouTube ショート（海外マイクラ動画の和訳）の最初の %d 秒です。映像の文字と音声を実際に確認して、次の JSON だけを返してください。読めない・聞こえないものは "不明" とし、推測で埋めないこと。

{
 "top_title": "画面上部の黒い帯などに常に出ている見出しの文字（そのまま。改行は／）",
 "top_title_color": "見出しの文字の色（行ごと）",
 "narration_lines": [{"t": 開始秒(小数1桁), "text": "画面下などに出るナレーションの字幕（1枚ずつ、そのまま）", "color": "文字の色"}],
 "narration_voice": "ナレーションの声があるか、合成音声か",
 "first_frame": "0秒の画面に映っているもの"
}"""


def call(model, vid, sec):
    part = {'file_data': {'file_uri': 'https://www.youtube.com/watch?v=' + vid},
            'videoMetadata': {'startOffset': '0s', 'endOffset': '%ds' % sec, 'fps': 4}}
    body = json.dumps({'contents': [{'parts': [part, {'text': PROMPT % sec}]}],
                       'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 3000,
                                            'responseMimeType': 'application/json'}}).encode()
    r = urllib.request.Request(HOST + '/v1beta/models/%s:generateContent' % model, data=body, method='POST',
                               headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'],
                                        'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=300) as resp:
        j = json.loads(resp.read())
    out = json.loads(''.join(p.get('text', '') for p in j['candidates'][0]['content']['parts']))
    if isinstance(out, list):
        out = out[0] if out and isinstance(out[0], dict) else {'_raw': out}
    return out


def watch(vid, sec, rounds=8):
    dead = set()
    for rnd in range(rounds):
        for m in MODELS:
            if m in dead:
                continue
            try:
                o = call(m, vid, sec); o['_model'] = m
                return o
            except urllib.error.HTTPError as e:
                if e.code in (403, 404, 429):
                    dead.add(m)
                print('  %s %s' % (m, e.code), flush=True)
            except Exception as e:
                print(('  %s %r' % (m, e))[:200], flush=True)
        if len(dead) == len(MODELS):
            return None
        time.sleep(min(30 * (rnd + 1), 180))
    return None


if __name__ == '__main__':
    ids, dst = json.load(open(sys.argv[1])), sys.argv[2]
    sec = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    done = json.load(open(dst)) if os.path.exists(dst) else {}
    for i, v in enumerate(ids):
        if v['id'] in done:
            continue
        print('%d/%d %s' % (i + 1, len(ids), v['id']), flush=True)
        o = watch(v['id'], sec)
        if o is None:
            print('  諦めた', flush=True); continue
        done[v['id']] = o
        json.dump(done, open(dst, 'w'), ensure_ascii=False, indent=1)
    print('済 %d/%d' % (len(done), len(ids)), flush=True)
