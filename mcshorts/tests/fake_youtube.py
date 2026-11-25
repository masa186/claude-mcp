"""テスト用の偽の YouTube API（ネットワークは使わない）。

応答の形は YouTube Data API v3 の公開仕様に合わせて作ったもので、本物の応答ではない。
"""
import json
import urllib.parse
from datetime import datetime, timedelta, timezone

FAKE_KEY = 'FAKE-TEST-KEY-not-real-0123456789'


class FakeClock:
    def __init__(self, start='2026-11-26T03:10:00Z'):
        self.t = datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


class FakeYouTube:
    def __init__(self, channel_id, video_ids, *, hidden_likes=(), no_comments=(), not_returned=(),
                 foreign=(), extra_existing=(), errors=None, title_prefix='動画'):
        self.channel_id = channel_id
        self.video_ids = list(video_ids)          # アップロード一覧に出るもの
        self.extra_existing = set(extra_existing)  # 一覧には無いが videos.list で返すもの
        self.hidden_likes = set(hidden_likes)
        self.no_comments = set(no_comments)
        self.not_returned = set(not_returned)
        self.foreign = set(foreign)
        self.errors = errors or {}                # endpoint -> [status, ...]（先頭から順に返す）
        self.title_prefix = title_prefix
        self.requests = []                        # (endpoint, params, headers)
        self.views = {}

    # transport(url, headers) -> (status, headers, body)
    def __call__(self, url, headers, timeout=60):
        u = urllib.parse.urlparse(url)
        ep = u.path.rsplit('/', 1)[-1]
        params = dict(urllib.parse.parse_qsl(u.query))
        self.requests.append((ep, params, dict(headers)))
        if 'key' in params:
            raise AssertionError('キーが URL に入っている')
        if headers.get('X-Goog-Api-Key') != FAKE_KEY:
            return self._err(403, 'forbidden')
        script = self.errors.get(ep)
        if script:
            st = script.pop(0)
            if st == 'conn':
                raise ConnectionError(f'connection reset while fetching {url}&key={FAKE_KEY}')
            return self._err(st, {403: 'quotaExceeded', 400: 'keyInvalid'}.get(st, 'backendError'))
        if ep == 'channels':
            return self._ok({'items': [{
                'id': self.channel_id,
                'snippet': {'title': 'テストチャンネル', 'publishedAt': '2026-01-01T00:00:00Z'},
                'statistics': {'subscriberCount': '123000', 'viewCount': '999', 'videoCount': str(len(self.video_ids)),
                               'hiddenSubscriberCount': False},
                'contentDetails': {'relatedPlaylists': {'uploads': 'UU' + self.channel_id[2:]}},
            }]} if params.get('id') == self.channel_id else {'items': []})
        if ep == 'playlistItems':
            n = int(params.get('maxResults', 5))
            start = int(params.get('pageToken', '0'))
            chunk = self.video_ids[start:start + n]
            body = {'items': [{'contentDetails': {'videoId': v}} for v in chunk]}
            if start + n < len(self.video_ids):
                body['nextPageToken'] = str(start + n)
            return self._ok(body)
        if ep == 'videos':
            ids = params['id'].split(',')
            if len(ids) > 50:
                return self._err(400, 'tooManyIds')
            items = []
            for v in ids:
                if v in self.not_returned or (v not in self.video_ids and v not in self.extra_existing):
                    continue
                st = {'viewCount': str(self.views.get(v, 1000))}
                if v not in self.hidden_likes:
                    st['likeCount'] = '10'
                if v not in self.no_comments:
                    st['commentCount'] = '2'
                sn = {'channelId': 'UCother000000000000000000' if v in self.foreign else self.channel_id,
                      'title': f'{self.title_prefix} {v} #shorts', 'description': '説明', 'publishedAt': '2026-02-01T00:00:00Z',
                      'categoryId': '20', 'thumbnails': {'default': {'url': f'https://i.ytimg.com/vi/{v}/default.jpg'}}}
                if v != self.video_ids[0]:
                    sn['tags'] = ['minecraft']
                items.append({'id': v, 'snippet': sn,
                              'contentDetails': {'duration': 'PT45S', 'definition': 'hd', 'caption': 'false'},
                              'statistics': st, 'status': {'privacyStatus': 'public', 'madeForKids': False}})
            return self._ok({'items': items})
        return self._err(404, 'notFound')

    @staticmethod
    def _ok(body):
        return 200, {'Date': 'Wed, 26 Nov 2026 03:10:00 GMT'}, json.dumps(body).encode()

    @staticmethod
    def _err(status, reason):
        body = {'error': {'code': status, 'message': f'{reason} (key={FAKE_KEY})', 'errors': [{'reason': reason}]}}
        return status, {}, json.dumps(body).encode()

    def calls(self, ep):
        return [p for e, p, _ in self.requests if e == ep]


def fake_ids(n, prefix='v'):
    """11文字の偽の動画ID。"""
    return [f'{prefix}{i:010d}'[:11] for i in range(n)]
