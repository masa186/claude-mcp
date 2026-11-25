"""YouTube の動画を最初から最後まで Gemini に見せて、ナレーションを全部書き出させる。

    python3 tools/smp_full.py <ids.json> <書き出し先.json>

字幕（画面の文字）と声（音声）を別々に書かせる。字幕だけ・声だけのナレーションもあるため。
済んだものは飛ばすので、止まってもやり直せる。
"""
import os, sys, json, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smp_open

PROMPT = """これは日本語の YouTube ショート（海外マイクラ動画の和訳）です。**最初から最後まで**、映像の文字と音声を実際に確認して、次の JSON だけを返してください。
読めない・聞こえないものは "不明" とし、推測で埋めないこと。

ナレーション＝動画の状況を説明する地の文（例「〜するドクタードーナツ」「〜ですが」「〜します」）。登場人物の台詞の和訳や *アスタリスクの見出し* はナレーションではない。

{
 "top_title": "画面上部に常に出ている見出し（改行は／）",
 "narration_voice_lines": [{"t": 開始秒, "text": "日本語ナレーションの声で読まれた文（1文ずつ、聞こえたとおり）"}],
 "narration_subtitles": [{"t": 開始秒, "text": "ナレーションの字幕（1枚ずつ、そのまま）"}],
 "other_subtitles_count": 台詞・見出しの字幕のおおよその枚数,
 "last_subtitle": "最後に出る字幕（そのまま）",
 "summary": "動画で起きることを1〜2文で"
}"""


def call(model, vid):
    part = {'file_data': {'file_uri': 'https://www.youtube.com/watch?v=' + vid}}
    body = json.dumps({'contents': [{'parts': [part, {'text': PROMPT}]}],
                       'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 6000,
                                            'responseMimeType': 'application/json'}}).encode()
    r = urllib.request.Request(smp_open.HOST + '/v1beta/models/%s:generateContent' % model, data=body,
                               method='POST', headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'],
                                                       'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=600) as resp:
        j = json.loads(resp.read())
    out = json.loads(''.join(p.get('text', '') for p in j['candidates'][0]['content']['parts']))
    if isinstance(out, list):
        out = out[0] if out and isinstance(out[0], dict) else {'_raw': out}
    return out


smp_open.call = lambda m, vid, sec: call(m, vid)

if __name__ == '__main__':
    ids, dst = json.load(open(sys.argv[1])), sys.argv[2]
    done = json.load(open(dst)) if os.path.exists(dst) else {}
    for i, v in enumerate(ids):
        if v['id'] in done:
            continue
        print('%d/%d %s' % (i + 1, len(ids), v['id']), flush=True)
        o = smp_open.watch(v['id'], 0)
        if o is None:
            print('  諦めた', flush=True); continue
        done[v['id']] = o
        json.dump(done, open(dst, 'w'), ensure_ascii=False, indent=1)
    print('済 %d/%d' % (len(done), len(ids)), flush=True)
