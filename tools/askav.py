"""音や映像を Gemini に聞かせて、それが何かを答えさせる。

    python3 askav.py <ファイル> "<聞きたいこと>"

/root/yt-analysis は何度も巻き戻って消えるので、こちらはリポジトリに置く。
"""
import os, sys, json, time, mimetypes, urllib.request

HOST = 'https://generativelanguage.googleapis.com'
MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3-flash-preview')
ENVS = ('/root/yt-analysis/.env',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


def load_env():
    for p in ENVS:
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                k, _, v = line.strip().partition('=')
                if k and v:
                    os.environ.setdefault(k, v.strip())


def req(url, data=None, headers=None, method=None, timeout=300):
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.headers, resp.read()


def upload(path):
    key = os.environ['GEMINI_API_KEY']
    size = os.path.getsize(path)
    mime = mimetypes.guess_type(path)[0] or 'video/mp4'
    h, _ = req(HOST + '/upload/v1beta/files',
               data=json.dumps({'file': {'display_name': os.path.basename(path)}}).encode(),
               headers={'x-goog-api-key': key,
                        'X-Goog-Upload-Protocol': 'resumable',
                        'X-Goog-Upload-Command': 'start',
                        'X-Goog-Upload-Header-Content-Length': str(size),
                        'X-Goog-Upload-Header-Content-Type': mime,
                        'Content-Type': 'application/json'}, method='POST')
    up = h.get('X-Goog-Upload-URL')
    _, body = req(up, data=open(path, 'rb').read(),
                  headers={'Content-Length': str(size), 'X-Goog-Upload-Offset': '0',
                           'X-Goog-Upload-Command': 'upload, finalize'},
                  method='POST', timeout=600)
    f = json.loads(body)['file']
    for _ in range(60):
        if f.get('state') == 'ACTIVE':
            return f
        time.sleep(3)
        _, b = req(HOST + '/v1beta/' + f['name'],
                   headers={'x-goog-api-key': os.environ['GEMINI_API_KEY']})
        f = json.loads(b)
    raise SystemExit('取り込みが終わらない')


def ask(f, prompt, model=None):
    body = json.dumps({'contents': [{'parts': [
        {'file_data': {'mime_type': f.get('mimeType', 'video/mp4'), 'file_uri': f['uri']}},
        {'text': prompt}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 4000}}).encode()
    _, b = req(HOST + '/v1beta/models/%s:generateContent' % (model or MODEL),
               data=body, headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'],
                                   'Content-Type': 'application/json'}, method='POST')
    r = json.loads(b)
    try:
        return ''.join(p.get('text', '') for p in r['candidates'][0]['content']['parts'])
    except Exception:
        return json.dumps(r, ensure_ascii=False)[:1500]


if __name__ == '__main__':
    load_env()
    print(ask(upload(sys.argv[1]), sys.argv[2]))
