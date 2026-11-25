"""SMPクリップのナレーションを「日本語の声」で見分けて、全編書き出す。

    python3 tools/smp_voice.py <ids.json> <書き出し先.json>

元の動画は英語なので、**日本語で話している声＝ナレーション**、と決められる。
声（日本語・英語を分ける）と、画面の字幕（全部）を、時刻つきで別々に書かせる。
字幕は0.3〜0.8秒で切り替わるので、fps 4 で見せる。済んだものは飛ばす。
"""
import os, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smp_open

PROMPT = """これは日本語の YouTube ショートです。元は英語のマイクラ動画で、日本語の字幕と、日本語のナレーションの声が足されています。
**最初から最後まで**音声を聞き、画面を見て、次の JSON だけを返してください。聞こえない・読めないものは "不明" と書き、推測で埋めないこと。

{
 "japanese_voice": [{"t": 開始秒, "end": 終了秒, "text": "日本語で話されている声（聞こえたとおり全文。1文ずつ）"}],
 "japanese_voice_kind": "日本語の声の種類（合成音声／人の声／無し）",
 "english_voice_seconds": "英語の声が聞こえる区間のおおよそ（例 3-58）",
 "subtitles": [{"t": 出た秒, "text": "画面下・中央の字幕（1枚ずつ全部、そのまま）", "color": "文字の色"}],
 "top_title": "画面上部の固定の見出し（改行は／）",
 "ending": "最後の3秒で起きること"
}"""


def call(model, vid):
    part = {'file_data': {'file_uri': 'https://www.youtube.com/watch?v=' + vid}, 'videoMetadata': {'fps': 4}}
    body = json.dumps({'contents': [{'parts': [part, {'text': PROMPT}]}],
                       'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 16000,
                                            'responseMimeType': 'application/json'}}).encode()
    r = urllib.request.Request(smp_open.HOST + '/v1beta/models/%s:generateContent' % model, data=body,
                               method='POST', headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'],
                                                       'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=900) as resp:
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
