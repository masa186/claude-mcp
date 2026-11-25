"""素材の候補（YouTube のマイクラ短尺）を Gemini に見せて、みんくらの型で使えるかを書き出させる。

    python3 tools/cand_watch.py <ids.txt> <書き出し先.json>

ids.txt は1行1つの動画ID。済んだものは飛ばす。Gemini の無料枠が切れていれば、戻るまで待つ（最大75分）。
"""
import os, sys, json, time, urllib.request, urllib.error
HOST = 'https://generativelanguage.googleapis.com'
MODELS = os.environ.get('GEMINI_MODELS', 'gemini-3-flash-preview,gemini-3.5-flash,gemini-3.6-flash,gemini-3.8-flash,'
                        'gemini-flash-lite-latest,gemini-3.5-flash-lite').split(',')
PROMPT = """これは海外のマインクラフトの短い動画です。最初から最後まで、映像と音を実際に確かめて、次の JSON だけを返してください。
分からないことは "不明" と書き、推測で埋めないこと。

{
 "summary": "何が起きる動画か（日本語で1〜2文）",
 "ordinary": "誰でも知っている物・状況は何か（例：宝箱、階段、子供部屋）",
 "extreme": "その物・状況に対して、何が極端・ありえないのか",
 "payoff": "一番の見せ場（オチ）は何か",
 "payoff_sec": 見せ場が始まる秒（数字）,
 "duration_sec": 動画の長さ（秒）,
 "timeline": [{"t": 秒, "what": "その秒に起きること"}],
 "speech": "話している言葉（英語ならそのまま。無ければ なし）",
 "on_screen_text": "画面の文字（そのまま）",
 "needs_context": 元ネタや人物を知らないと分からないなら true,
 "one_image": 見せ場が1枚の画で分かるなら true,
 "is_ad": 商品の宣伝に見えるなら true,
 "music": "BGMや音の特徴"
}"""


def call(model, vid):
    part = {'file_data': {'file_uri': 'https://www.youtube.com/watch?v=' + vid}}
    body = json.dumps({'contents': [{'parts': [part, {'text': PROMPT}]}],
                       'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 4000,
                                            'responseMimeType': 'application/json'}}).encode()
    r = urllib.request.Request(HOST + '/v1beta/models/%s:generateContent' % model, data=body, method='POST',
                               headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=600) as resp:
        j = json.loads(resp.read())
    out = json.loads(''.join(p.get('text', '') for p in j['candidates'][0]['content']['parts']))
    if isinstance(out, list):
        out = out[0] if out and isinstance(out[0], dict) else {'_raw': out}
    return out


def watch(vid, deadline):
    while time.time() < deadline:
        dead = 0
        for m in MODELS:
            try:
                o = call(m, vid); o['_model'] = m
                return o
            except urllib.error.HTTPError as e:
                dead += e.code in (403, 404, 429)
                print('  %s %s' % (m, e.code), flush=True)
            except Exception as e:
                print(('  %s %r' % (m, e))[:200], flush=True)
        time.sleep(60 if dead == len(MODELS) else 20)
    return None


if __name__ == '__main__':
    ids = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    dst = sys.argv[2]
    done = json.load(open(dst)) if os.path.exists(dst) else {}
    deadline = time.time() + 75 * 60
    for i, vid in enumerate(ids):
        if vid in done:
            continue
        print('%d/%d %s' % (i + 1, len(ids), vid), flush=True)
        o = watch(vid, deadline)
        if o is None:
            print('  諦めた', flush=True); break
        done[vid] = o
        json.dump(done, open(dst, 'w'), ensure_ascii=False, indent=1)
    print('済 %d/%d' % (len(done), len(ids)), flush=True)
