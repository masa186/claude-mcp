"""YouTube API の呼び出し（偽の API を使う。ネットワークには接続しない）。"""
import json

import pytest

from adapters import youtube_api as ya
from fake_youtube import FAKE_KEY, FakeClock, FakeYouTube, fake_ids

CFG = {'slug': 'dream', 'channel_id': 'UCfakechannel0000000000a'}


def client(fake, sleeps=None):
    return ya.YouTubeClient(FAKE_KEY, transport=fake, clock=FakeClock(),
                            sleep=(sleeps.append if sleeps is not None else (lambda s: None)))


def test_key_is_sent_in_header_not_url():
    fake = FakeYouTube(CFG['channel_id'], fake_ids(3))
    c = client(fake)
    snap = ya.fetch_channel(c, CFG)
    assert all('key' not in p for _, p, _ in fake.requests)
    assert all(h['X-Goog-Api-Key'] == FAKE_KEY for _, _, h in fake.requests)
    assert FAKE_KEY not in json.dumps(snap, ensure_ascii=False)


def test_all_pages_and_videos_list_max_50():
    ids = fake_ids(120)
    fake = FakeYouTube(CFG['channel_id'], ids)
    snap = ya.fetch_channel(client(fake), CFG)
    assert snap['playlist_pages'] == 3 and snap['uploads_count'] == 120
    vcalls = fake.calls('videos')
    assert len(vcalls) == 3 and all(len(p['id'].split(',')) <= 50 for p in vcalls)
    assert len(snap['videos']) == 120
    assert all(p['maxResults'] == '50' for p in fake.calls('playlistItems'))


def test_no_cap_on_number_of_videos():
    """既存の clips.py は400本で打ち切っていた。こちらは最後のページまで取る。"""
    ids = fake_ids(450)
    fake = FakeYouTube(CFG['channel_id'], ids)
    snap = ya.fetch_channel(client(fake), CFG)
    assert snap['playlist_pages'] == 9 and len(snap['videos']) == 450
    assert len(fake.calls('videos')) == 9


def test_extra_ids_and_not_returned_are_recorded():
    ids = fake_ids(5)
    fake = FakeYouTube(CFG['channel_id'], ids, not_returned={ids[1]}, extra_existing={'xold0000001'})
    snap = ya.fetch_channel(client(fake), CFG, extra_ids=['xold0000001', 'xgone000001', ids[0]])
    assert snap['extra_ids_requested'] == ['xold0000001', 'xgone000001']   # 一覧にあるものは足さない
    got = {v['video_id']: v for v in snap['videos']}
    assert got['xold0000001']['in_uploads_playlist'] is False
    nr = {x['video_id']: x for x in snap['not_returned']}
    assert set(nr) == {ids[1], 'xgone000001'}
    assert nr[ids[1]]['in_uploads_playlist'] is True and nr['xgone000001']['in_uploads_playlist'] is False


def test_hidden_stats_are_none_not_zero():
    ids = fake_ids(3)
    fake = FakeYouTube(CFG['channel_id'], ids, hidden_likes={ids[0]}, no_comments={ids[0]})
    snap = ya.fetch_channel(client(fake), CFG)
    v = {x['video_id']: x for x in snap['videos']}[ids[0]]
    assert v['likes'] is None and v['comments'] is None
    assert v['missing']['likes']['code'] == 'NOT_AVAILABLE'
    assert v['missing']['tags']['code'] == 'NOT_COLLECTED'       # 先頭の動画は tags なし
    other = {x['video_id']: x for x in snap['videos']}[ids[1]]
    assert other['likes'] == 10 and other['tags'] == ['minecraft'] and other['duration_sec'] == 45


def test_foreign_channel_videos_are_excluded():
    ids = fake_ids(4)
    fake = FakeYouTube(CFG['channel_id'], ids, foreign={ids[2]})
    snap = ya.fetch_channel(client(fake), CFG)
    assert ids[2] not in {v['video_id'] for v in snap['videos']}
    assert snap['foreign'] == [{'video_id': ids[2], 'channel_id': 'UCother000000000000000000'}]


def test_each_video_has_fetch_time():
    fake = FakeYouTube(CFG['channel_id'], fake_ids(60))
    snap = ya.fetch_channel(client(fake), CFG)
    times = {v['fetched_at'] for v in snap['videos']}
    assert len(times) == 2      # videos.list 2回分
    assert all(t.endswith('Z') for t in times)
    assert snap['started_at'] < snap['finished_at']


def test_retry_on_5xx_then_success():
    sleeps = []
    fake = FakeYouTube(CFG['channel_id'], fake_ids(3), errors={'videos': [503, 500]})
    snap = ya.fetch_channel(client(fake, sleeps), CFG)
    assert sleeps == [2, 4] and len(snap['videos']) == 3


def test_retry_on_connection_error_and_redact():
    sleeps = []
    fake = FakeYouTube(CFG['channel_id'], fake_ids(3), errors={'channels': ['conn']})
    c = client(fake, sleeps)
    ya.fetch_channel(c, CFG)
    assert sleeps == [2]
    assert FAKE_KEY not in json.dumps(c.calls, ensure_ascii=False)


@pytest.mark.parametrize('status', [403, 400])
def test_stop_without_retry_on_quota_or_bad_request(status):
    sleeps = []
    fake = FakeYouTube(CFG['channel_id'], fake_ids(3), errors={'channels': [status]})
    with pytest.raises(ya.ApiError) as ei:
        ya.fetch_channel(client(fake, sleeps), CFG)
    assert sleeps == [] and len(fake.calls('channels')) == 1
    assert FAKE_KEY not in str(ei.value)
    assert ei.value.reason in ('quotaExceeded', 'keyInvalid')


def test_retry_gives_up_after_four_retries():
    sleeps = []
    fake = FakeYouTube(CFG['channel_id'], fake_ids(3), errors={'playlistItems': [503] * 5})
    with pytest.raises(ya.ApiError):
        ya.fetch_channel(client(fake, sleeps), CFG)
    assert sleeps == [2, 4, 8, 16] and len(fake.calls('playlistItems')) == 5


def test_channel_not_found_stops():
    fake = FakeYouTube('UCsomeoneelse0000000000a', fake_ids(3))
    with pytest.raises(ya.ApiError):
        ya.fetch_channel(client(fake), CFG)


def test_client_requires_key():
    with pytest.raises(ValueError):
        ya.YouTubeClient(None)


@pytest.mark.parametrize('s,sec', [('PT45S', 45), ('PT1M2S', 62), ('PT1H', 3600), ('P1DT1S', 86401), ('', None), (None, None)])
def test_iso_duration(s, sec):
    assert ya.iso_duration_sec(s) == sec


def test_plan_calls():
    assert ya.plan_calls(58)[1] == 5       # channels 1 + 一覧 2 + videos 2
    calls, units = ya.plan_calls(347)
    assert dict(calls) == {'channels.list': 1, 'playlistItems.list': 7, 'videos.list': 7} and units == 15


def test_raw_gzip_is_deterministic_and_redacted():
    import gzip
    fake = FakeYouTube(CFG['channel_id'], fake_ids(3))
    c = client(fake)
    ya.fetch_channel(c, CFG)
    c.raw.append({'note': f'x {FAKE_KEY} y'})
    a, b = ya.raw_gzip_bytes(c), ya.raw_gzip_bytes(c)
    assert a == b
    assert FAKE_KEY.encode() not in gzip.decompress(a)
