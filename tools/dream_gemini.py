"""動画ファイルを Gemini に1本ずつ見せて、音（BGM・効果音・声）と動き（ズーム等）を秒付きで答えさせる。

    python3 tools/dream_gemini.py <videos.json> <書き出し先ディレクトリ>

こちら（Claude）は音を直接聞けないので、音まわりはここの答えを「Gemini判定」として使う。
字幕の文字やカットの秒は、こちらがコマと ffmpeg で確かめたものを優先する。

済んだ動画は書き出し先に <id>.json が残るので、止まってもやり直せば続きから。
混雑（503）は、モデルを替えながら待って取り直す。
"""
import os, sys, json, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import askav

MODELS = os.environ.get('GEMINI_MODELS',
    'gemini-3.6-flash,gemini-3.8-flash,gemini-3-flash-preview,gemini-3.5-flash,'
    'gemini-flash-lite-latest,gemini-3.5-flash-lite,gemini-3.1-pro-preview').split(',')

PROMPT = """これは日本語の YouTube ショート（海外マイクラ配信の和訳切り抜き）です。映像と音を実際に確認して、次の JSON だけを返してください。
- 秒は動画の先頭からの秒数（小数1桁まで）。
- 聞き取れない・見えないものは書かずに "不明" とする。推測で埋めない。推測を含む場合は文末に「(推測)」と付ける。

{
 "narration_voice": "日本語ナレーションの声の種類（合成音声か人の声か、性別、声の特徴、速さ）",
 "narration_lines": [{"t": 開始秒, "text": "ナレーションの文"}],
 "original_voice": "元の配信者の英語音声が聞こえるか、どの程度の音量か",
 "bgm": [{"t": 開始秒, "desc": "BGMの雰囲気・曲調・変化"}],
 "sfx": [{"t": 秒, "desc": "効果音の種類（例: ドン、ピロン、笑い声、警告音）"}],
 "visual_edits": [{"t": 秒, "desc": "ズーム、揺れ、スロー、停止、フラッシュ、モザイク、画像や絵文字の挿入、字幕の色変え 等"}],
 "top_text": [{"t": 秒, "text": "画面上部のタイトル文字（変わったら全部）"}],
 "players": "映っている配信者・プレイヤーの名前（画面上の名前表示や字幕から分かるものだけ）",
 "beats": [{"t": 秒, "what": "その時点で起きていること（状況説明→事件→展開→クライマックス→オチ）"}],
 "ending": "最後の3秒に映っているもの、聞こえる音、最後の字幕",
 "loop": "最後から最初に自然につながる作りか（true/false と理由）"
}"""


def call(model, f):
    body = json.dumps({'contents': [{'parts': [
        {'file_data': {'mime_type': f.get('mimeType', 'video/mp4'), 'file_uri': f['uri']}},
        {'text': PROMPT}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 6000,
                             'responseMimeType': 'application/json'}}).encode()
    _, b = askav.req(askav.HOST + '/v1beta/models/%s:generateContent' % model, data=body,
                     headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'],
                              'Content-Type': 'application/json'}, method='POST', timeout=300)
    j = json.loads(b)
    txt = ''.join(p.get('text', '') for p in j['candidates'][0]['content']['parts'])
    out = json.loads(txt)
    if isinstance(out, list):
        out = out[0] if out and isinstance(out[0], dict) else {'_raw': out}
    return out


def watch(f, rounds=10):
    dead = set()
    for rnd in range(rounds):
        for m in MODELS:
            if m in dead:
                continue
            try:
                out = call(m, f)
                out['_model'] = m
                return out
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
    askav.load_env()
    vids = json.load(open(sys.argv[1]))
    dst = sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for v in vids:
        p = os.path.join(dst, v['id'] + '.json')
        if os.path.exists(p):
            continue
        print('%s %s %s' % (v['no'], v['id'], v['title'][:30]), flush=True)
        try:
            f = askav.upload(v['path'])
        except Exception as e:
            print('  upload失敗 %r' % e, flush=True)
            continue
        out = watch(f)
        if out is None:
            print('  諦めた', flush=True)
            continue
        json.dump(out, open(p, 'w'), ensure_ascii=False, indent=1)
    print('済', flush=True)
