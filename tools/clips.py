"""切り抜きチャンネルを YouTube Data API で数える。

    python3 clips.py <チャンネルID> ...
    python3 clips.py --find <検索語>

/root/yt-analysis は何度か巻き戻って消えたので、こちらはリポジトリに置く。
playlistItems は50本で1ユニット、search は1回100ユニットなので、
チャンネルIDが分かっているものは search を使わない。
"""
import os, sys, json, re, urllib.request, urllib.parse

HOST = 'https://www.googleapis.com/youtube/v3/'
ENVS = ('/root/yt-analysis/.env',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


def load_env():
    for p in ENVS:
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                k, _, v = line.strip().partition('=')
                if k and v:
                    os.environ.setdefault(k, v.strip())


def key():
    for k in ('YOUTUBE_API_KEY', 'YT_API_KEY', 'GOOGLE_API_KEY'):
        if os.environ.get(k):
            return os.environ[k]
    raise SystemExit('YouTube の API キーが見つからない')


def get(ep, **p):
    p['key'] = key()
    with urllib.request.urlopen(HOST + ep + '?' + urllib.parse.urlencode(p),
                                timeout=60) as r:
        return json.loads(r.read())


def iso_sec(s):
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or '')
    if not m:
        return 0
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def find_channels(q, n=10):
    r = get('search', part='snippet', q=q, type='channel', maxResults=n)
    return [(i['snippet']['channelTitle'], i['id']['channelId'])
            for i in r.get('items', [])]


def channel(cid):
    r = get('channels', part='snippet,statistics,contentDetails', id=cid)
    if not r.get('items'):
        return None
    c = r['items'][0]
    return dict(name=c['snippet']['title'], cid=cid,
                subs=int(c['statistics'].get('subscriberCount', 0)),
                views=int(c['statistics'].get('viewCount', 0)),
                total=int(c['statistics'].get('videoCount', 0)),
                started=c['snippet']['publishedAt'],
                uploads=c['contentDetails']['relatedPlaylists']['uploads'])


def videos(uploads, cap=400):
    ids, tok = [], None
    while len(ids) < cap:
        r = get('playlistItems', part='contentDetails', playlistId=uploads,
                maxResults=50, **({'pageToken': tok} if tok else {}))
        ids += [i['contentDetails']['videoId'] for i in r.get('items', [])]
        tok = r.get('nextPageToken')
        if not tok:
            break
    out = []
    for i in range(0, len(ids), 50):
        r = get('videos', part='snippet,statistics,contentDetails',
                id=','.join(ids[i:i+50]))
        for v in r.get('items', []):
            out.append(dict(
                id=v['id'], title=v['snippet']['title'],
                at=v['snippet']['publishedAt'],
                sec=iso_sec(v['contentDetails'].get('duration')),
                views=int(v['statistics'].get('viewCount', 0)),
                likes=int(v['statistics'].get('likeCount', 0)),
                comments=int(v['statistics'].get('commentCount', 0))))
    return out


def fetch(cid):
    c = channel(cid)
    return dict(c=c, vs=videos(c['uploads'])) if c else None


if __name__ == '__main__':
    load_env()
    a = sys.argv[1:]
    if a and a[0] == '--find':
        for t, c in find_channels(' '.join(a[1:])):
            print(t, c)
    else:
        out = {}
        for cid in a:
            d = fetch(cid)
            if d:
                out[d['c']['name']] = d
                print(d['c']['name'], len(d['vs']), '本', file=sys.stderr)
        print(json.dumps(out, ensure_ascii=False))
