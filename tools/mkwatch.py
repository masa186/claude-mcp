"""チャンネルの全動画を Gemini に1本ずつ見せて、中身を同じ項目で書き出す。

    python3 mkwatch.py <clips.py の出力JSON> <チャンネル名> <書き出し先.json>

途中で止まっても、書き出し先に済んだ分が残るので、もう一度走らせれば続きから。
Gemini は混雑で 503 を返すことが多いので、モデルを替えながら待って取り直す。
"""
import os, sys, json, time, urllib.request, urllib.error

HOST = 'https://generativelanguage.googleapis.com'
MODELS = os.environ.get('GEMINI_MODELS',
    'gemini-3.6-flash,gemini-3.5-flash-lite,gemini-flash-lite-latest,'
    'gemini-3-flash-preview,gemini-3.8-flash,gemini-3.5-flash').split(',')

PROMPT = """これは日本語の YouTube ショート（マイクラの切り抜き）です。実際に映像と音を見て、次の JSON だけを返してください。推測には "?" を付けること。

{
 "source": "素材の元の配信者・クリエイター名（分かる範囲。不明なら\\"不明\\"）",
 "lang": "元の音声の言語（英語/日本語/音声なし 等）",
 "drdonut": "DrDonut または DonutSMP 関係者が映る/話題か（true/false）",
 "kind": "次から1つ: 建築・作品 / 技・プレイスキル / 検証・豆知識 / 事件・ハプニング / 感動・懐かし / ネタ・ミーム / トラップ・いたずら / リアクション / その他",
 "f0_2_visual": "0〜2秒に映っているもの",
 "f0_2_text": "0〜2秒に出ている文字（そのまま）",
 "hook": "冒頭で視聴者に約束している『この先に何が起きるか』を1文で",
 "payoff": "最後に何が起きるか、オチを1文で",
 "payoff_sec": "オチが起きる秒数（数字）",
 "narration": "読み上げ音声の有無と声の種類（例: 合成音声の女性/なし）",
 "subtitles": "字幕の量（なし/少ない/多い）と色の使い方",
 "music": "BGM や効果音の特徴",
 "loop": "最後から最初へ自然につながるループ構成か（true/false）",
 "needs_context": "DrDonut などの人物を知らないと面白さが分からないか（true/false）",
 "why": "この動画が知らない人にも刺さる/刺さらない理由を1文で"
}"""


def call(model, vid):
    body = json.dumps({
        'contents': [{'parts': [
            {'file_data': {'file_uri': 'https://www.youtube.com/watch?v=' + vid}},
            {'text': PROMPT}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 3000,
                             'responseMimeType': 'application/json'}}).encode()
    r = urllib.request.Request(
        HOST + '/v1beta/models/%s:generateContent' % model, data=body, method='POST',
        headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'],
                 'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=300) as resp:
        j = json.loads(resp.read())
    txt = ''.join(p.get('text', '') for p in j['candidates'][0]['content']['parts'])
    return json.loads(txt)


def watch(vid, rounds=8):
    dead = set()
    for rnd in range(rounds):
        for m in MODELS:
            if m in dead:
                continue
            try:
                out = call(m, vid)
                out['_model'] = m
                return out
            except urllib.error.HTTPError as e:
                if e.code in (403, 404):
                    dead.add(m)          # このモデルは鍵で使えない
                elif e.code == 429:
                    dead.add(m)          # 無料枠を使い切った
                print('  %s %s' % (m, e.code), file=sys.stderr, flush=True)
            except Exception as e:
                print('  %s %r' % (m, e)[:200], file=sys.stderr, flush=True)
        if len(dead) == len(MODELS):
            return None
        time.sleep(min(30 * (rnd + 1), 180))
    return None


if __name__ == '__main__':
    src, name, dst = sys.argv[1:4]
    vs = json.load(open(src))[name]['vs']
    done = json.load(open(dst)) if os.path.exists(dst) else {}
    for i, v in enumerate(vs):
        if v['id'] in done:
            continue
        print('%d/%d %s %s' % (i + 1, len(vs), v['id'], v['title']), file=sys.stderr, flush=True)
        out = watch(v['id'])
        if out is None:
            print('  諦めた', file=sys.stderr, flush=True)
            continue
        done[v['id']] = out
        json.dump(done, open(dst, 'w'), ensure_ascii=False, indent=1)
    print('済 %d/%d' % (len(done), len(vs)), file=sys.stderr)
