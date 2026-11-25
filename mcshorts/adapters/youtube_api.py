"""YouTube Data API v3 の呼び出し（公開情報だけ。API キーで読める範囲）。

安全のための決まり：
- キーは環境変数 YOUTUBE_API_KEY からだけ読む。ファイルからは読まない・書かない
- キーは X-Goog-Api-Key ヘッダーで送る。URL・記録・例外のメッセージには入れない（入っていたら *** に置き換える）
- 400 / 401 / 403 / 404 は再試行せずに止める。5xx と通信エラーは最大4回まで、間隔を空けて再試行する
- videos.list は1回50本まで。一覧（playlistItems）は最後のページまで取る（本数で打ち切らない）
- 値が無い統計（非公開の高評価数・無効なコメント数）は 0 にせず None にする
"""
import gzip
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HOST = 'https://www.googleapis.com/youtube/v3/'
KEY_ENV = 'YOUTUBE_API_KEY'
MAX_IDS_PER_VIDEOS_CALL = 50
MAX_RESULTS_PER_PAGE = 50
UNIT_COST = {'channels': 1, 'playlistItems': 1, 'videos': 1}
RETRY_STATUSES = {500, 502, 503, 504}
RETRY_WAITS = (2, 4, 8, 16)          # 最大4回の再試行
STOP_STATUSES = {400, 401, 403, 404}
VIDEO_PARTS = 'snippet,contentDetails,statistics,status'
CHANNEL_PARTS = 'snippet,statistics,contentDetails'


def utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def read_key():
    """キーがあれば返す。値は表示しない。"""
    v = os.environ.get(KEY_ENV)
    return v if v else None


class ApiError(Exception):
    def __init__(self, endpoint, status, reason, message):
        self.endpoint, self.status, self.reason = endpoint, status, reason
        super().__init__(f'{endpoint}: HTTP {status} {reason} {message}'.strip())

    def record(self):
        return {'endpoint': self.endpoint, 'status': self.status, 'reason': self.reason,
                'message': str(self)}


class Redactor:
    def __init__(self, secret):
        self.secret = secret

    def __call__(self, text):
        text = str(text)
        if self.secret:
            text = text.replace(self.secret, '***')
            text = text.replace(urllib.parse.quote(self.secret, safe=''), '***')
        # 念のため、URL のクエリに key= が残っていれば消す（JSON の引用符・エスケープの手前で止める）
        return re.sub(r'([?&]key=)[^&\s"\'\\<>]+', r'\1***', text)


def urllib_transport(url, headers, timeout=60):
    """本物の通信。戻り値は (状態コード, 応答ヘッダー, 本文 bytes)。"""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers.items()), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()) if e.headers else {}, e.read()


def _reason(body):
    try:
        err = json.loads(body).get('error', {})
        errs = err.get('errors') or [{}]
        return errs[0].get('reason') or err.get('status') or '', err.get('message') or ''
    except Exception:
        return '', ''


class YouTubeClient:
    def __init__(self, key, transport=urllib_transport, sleep=time.sleep, clock=utcnow):
        if not key:
            raise ValueError(f'環境変数 {KEY_ENV} が設定されていない')
        self._key = key
        self.redact = Redactor(key)
        self.transport = transport
        self.sleep = sleep
        self.clock = clock
        self.calls = []   # 呼び出しの記録（キーを含まない）
        self.raw = []     # 応答そのもの（キーを含まない）

    @property
    def units(self):
        return sum(c['units'] for c in self.calls)

    def get(self, endpoint, **params):
        url = HOST + endpoint + '?' + urllib.parse.urlencode(params)
        headers = {'X-Goog-Api-Key': self._key, 'Accept': 'application/json'}
        attempt = 0
        while True:
            at = iso(self.clock())
            try:
                status, rh, body = self.transport(url, headers)
            except Exception as e:  # 通信エラー
                status, rh, body = None, {}, b''
                err_text = self.redact(f'{type(e).__name__}: {e}')
            else:
                err_text = ''
            rec = {'endpoint': endpoint, 'params': dict(params), 'at': at, 'status': status,
                   'server_date': (rh or {}).get('Date') or (rh or {}).get('date'),
                   'units': UNIT_COST.get(endpoint, 1), 'attempt': attempt + 1}
            self.calls.append(rec)
            if status == 200:
                data = json.loads(body)
                rec['items'] = len(data.get('items', []))
                self.raw.append({'endpoint': endpoint, 'params': dict(params), 'at': at, 'body': data})
                return data
            reason, message = _reason(body) if body else ('', '')
            rec['reason'] = reason or err_text or None
            retryable = status is None or status in RETRY_STATUSES
            if not retryable or attempt >= len(RETRY_WAITS):
                raise ApiError(endpoint, status, self.redact(reason or ''), self.redact(message or err_text))
            self.sleep(RETRY_WAITS[attempt])
            attempt += 1


# ------------------------------------------------------------------ 取得
def _int_or_none(v):
    return int(v) if v is not None and str(v).isdigit() else None


def iso_duration_sec(s):
    m = re.fullmatch(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or '')
    if not m or not s:
        return None
    d, h, mi, se = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def normalize_video(v, fetched_at):
    sn, cd, st, ss = v.get('snippet', {}), v.get('contentDetails', {}), v.get('statistics', {}), v.get('status', {})
    out = {
        'video_id': v['id'],
        'fetched_at': fetched_at,
        'channel_id': sn.get('channelId'),
        'title': sn.get('title'),
        'description': sn.get('description'),
        'tags': sn.get('tags'),
        'published_at': sn.get('publishedAt'),
        'category_id': sn.get('categoryId'),
        'default_language': sn.get('defaultLanguage'),
        'default_audio_language': sn.get('defaultAudioLanguage'),
        'thumbnails': {k: t.get('url') for k, t in sorted((sn.get('thumbnails') or {}).items())},
        'duration_iso': cd.get('duration'),
        'duration_sec': iso_duration_sec(cd.get('duration')),
        'definition': cd.get('definition'),
        'caption_track': {'true': True, 'false': False}.get(cd.get('caption')),
        'views': _int_or_none(st.get('viewCount')),
        'likes': _int_or_none(st.get('likeCount')),
        'comments': _int_or_none(st.get('commentCount')),
        'privacy_status': ss.get('privacyStatus'),
        'made_for_kids': ss.get('madeForKids'),
        'missing': {},
    }
    if out['tags'] is None:
        out['missing']['tags'] = {'code': 'NOT_COLLECTED',
                                  'note': 'API の応答に tags が無い（API はタグが無い動画では項目自体を返さない）'}
    if out['views'] is None:
        out['missing']['views'] = {'code': 'NOT_AVAILABLE', 'note': 'API の応答に viewCount が無い'}
    if out['likes'] is None:
        out['missing']['likes'] = {'code': 'NOT_AVAILABLE', 'note': '高評価数が非公開か、応答に無い'}
    if out['comments'] is None:
        out['missing']['comments'] = {'code': 'NOT_AVAILABLE', 'note': 'コメントが無効か、応答に無い'}
    return out


def plan_calls(n_known, n_extra=0):
    """ネットワークを使わない見込み（段階1の件数から）。"""
    pages = max(1, math.ceil(n_known / MAX_RESULTS_PER_PAGE))
    vcalls = max(1, math.ceil((n_known + n_extra) / MAX_IDS_PER_VIDEOS_CALL))
    calls = [('channels.list', 1), ('playlistItems.list', pages), ('videos.list', vcalls)]
    return calls, sum(n * UNIT_COST[e.split('.')[0]] for e, n in calls)


def fetch_channel(client, channel_cfg, extra_ids=()):
    """1チャンネル分を取る。extra_ids：既存データにあるが一覧に出てこないかもしれない動画（状態を確かめる）。"""
    cid = channel_cfg['channel_id']
    started = iso(client.clock())
    ch = client.get('channels', part=CHANNEL_PARTS, id=cid)
    items = ch.get('items') or []
    if len(items) != 1 or items[0].get('id') != cid:
        raise ApiError('channels', 200, 'channelNotFound', f'チャンネル {cid} が返ってこない')
    c = items[0]
    cst = c.get('statistics', {})
    channel = {
        'channel_id': cid,
        'fetched_at': client.calls[-1]['at'],
        'title': c.get('snippet', {}).get('title'),
        'published_at': c.get('snippet', {}).get('publishedAt'),
        'subscribers': None if cst.get('hiddenSubscriberCount') else _int_or_none(cst.get('subscriberCount')),
        'subscribers_note': 'API 側で上3桁に丸められた値' if not cst.get('hiddenSubscriberCount') else '非公開',
        'view_count': _int_or_none(cst.get('viewCount')),
        'video_count': _int_or_none(cst.get('videoCount')),
        'uploads_playlist': c.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads'),
    }

    ids, pages, tok = [], 0, None
    while True:
        p = dict(part='contentDetails', playlistId=channel['uploads_playlist'], maxResults=MAX_RESULTS_PER_PAGE)
        if tok:
            p['pageToken'] = tok
        r = client.get('playlistItems', **p)
        pages += 1
        for it in r.get('items', []):
            vid = (it.get('contentDetails') or {}).get('videoId')
            if vid and vid not in ids:
                ids.append(vid)
        tok = r.get('nextPageToken')
        if not tok:
            break

    extra = [v for v in extra_ids if v not in ids]
    lookup = ids + extra
    videos, foreign, returned = [], [], set()
    for i in range(0, len(lookup), MAX_IDS_PER_VIDEOS_CALL):
        chunk = lookup[i:i + MAX_IDS_PER_VIDEOS_CALL]
        assert len(chunk) <= MAX_IDS_PER_VIDEOS_CALL
        r = client.get('videos', part=VIDEO_PARTS, id=','.join(chunk))
        at = client.calls[-1]['at']
        for v in r.get('items', []):
            returned.add(v['id'])
            nv = normalize_video(v, at)
            nv['in_uploads_playlist'] = v['id'] in ids
            if nv['channel_id'] != cid:
                foreign.append({'video_id': v['id'], 'channel_id': nv['channel_id']})
                continue
            videos.append(nv)

    not_returned = [{'video_id': v, 'in_uploads_playlist': v in ids,
                     'note': 'API が返さなかった。削除・非公開などの区別はできない'}
                    for v in lookup if v not in returned]
    return {
        'schema_version': 1,
        'channel': channel_cfg['slug'],
        'channel_id': cid,
        'started_at': started,
        'finished_at': iso(client.clock()),
        'channel_stats': channel,
        'uploads_count': len(ids),
        'playlist_pages': pages,
        'extra_ids_requested': extra,
        'videos': sorted(videos, key=lambda v: v['video_id']),
        'not_returned': not_returned,
        'foreign': foreign,
        'calls': client.calls,
        'units_total': client.units,
    }


def raw_gzip_bytes(client):
    """応答をそのまま gzip にする（ヘッダーの時刻は 0 にして、同じ中身なら同じバイト列にする）。
    応答にキーは含まれないが、念のため *** に置き換えてから圧縮する。"""
    text = client.redact(json.dumps(client.raw, ensure_ascii=False, sort_keys=True))
    return gzip.compress(text.encode('utf-8'), mtime=0)
