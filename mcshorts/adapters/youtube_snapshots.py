"""YouTube API の取得結果（スナップショット）の保存と読み込み。

保存先（チャンネルごとに分ける）：
  snapshots/youtube/<channel>/index.jsonl              取得の記録（追記だけ）
  snapshots/youtube/<channel>/snapshots/<run_id>.json  整えた取得結果（1回1ファイル。書き換えない）
  snapshots/youtube/<channel>/raw/<run_id>.json.gz     応答そのもの
  snapshots/youtube/<channel>/failed.jsonl             失敗の記録（キーは含まない）

data/ と reports/ には書かない。統合は build_dataset.py / integrate.py が行う。
"""
import hashlib
import json
import os

from .common import CHANNELS, load_json, sha256_file


def run_id_from(started_at):
    """'2026-11-26T03:10:00Z' → '20261126T031000Z'"""
    return started_at.replace('-', '').replace(':', '')


def _atomic_write_new(path, data_bytes):
    """新しいファイルとしてだけ書く。既にあれば止める。全部書けてから正式な名前にする。"""
    if os.path.exists(path):
        raise FileExistsError(f'既にある（上書きしない）: {path}')
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data_bytes)
        f.flush()
        os.fsync(f.fileno())
    if os.path.exists(path):
        os.remove(tmp)
        raise FileExistsError(f'既にある（上書きしない）: {path}')
    os.replace(tmp, path)


def _append_line(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + '\n')


def save(base, snapshot, raw_gz, redact):
    """取得結果を保存し、index.jsonl に1行足す。redact はキーを消す関数。"""
    ch = snapshot['channel']
    assert ch in CHANNELS, ch
    run_id = run_id_from(snapshot['started_at'])
    d = os.path.join(base, ch)
    os.makedirs(os.path.join(d, 'snapshots'), exist_ok=True)
    os.makedirs(os.path.join(d, 'raw'), exist_ok=True)
    snap_rel = f'snapshots/{run_id}.json'
    raw_rel = f'raw/{run_id}.json.gz'
    text = redact(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=1)) + '\n'
    snap_bytes = text.encode('utf-8')
    # 先に両方の名前が空いていることを確かめる（片方だけ書かれるのを防ぐ）
    for rel in (snap_rel, raw_rel):
        if os.path.exists(os.path.join(d, rel)):
            raise FileExistsError(f'既にある（上書きしない）: {os.path.join(d, rel)}')
    _atomic_write_new(os.path.join(d, raw_rel), raw_gz)
    _atomic_write_new(os.path.join(d, snap_rel), snap_bytes)
    entry = {
        'run_id': run_id, 'channel': ch, 'result': 'ok',
        'started_at': snapshot['started_at'], 'finished_at': snapshot['finished_at'],
        'snapshot': snap_rel, 'snapshot_sha256': hashlib.sha256(snap_bytes).hexdigest(),
        'raw': raw_rel, 'raw_sha256': hashlib.sha256(raw_gz).hexdigest(),
        'units_total': snapshot['units_total'], 'n_videos': len(snapshot['videos']),
        'n_not_returned': len(snapshot['not_returned']), 'n_foreign': len(snapshot['foreign']),
        'code_commit': snapshot.get('code_commit'),
    }
    _append_line(os.path.join(d, 'index.jsonl'), entry)
    return entry


def record_failure(base, channel, started_at, error_record, calls, redact):
    assert channel in CHANNELS, channel
    obj = {'run_id': run_id_from(started_at), 'channel': channel, 'result': 'failed',
           'started_at': started_at, 'error': error_record, 'calls': calls}
    obj = json.loads(redact(json.dumps(obj, ensure_ascii=False)))
    _append_line(os.path.join(base, channel, 'failed.jsonl'), obj)
    return obj


def read_index(base, channel):
    p = os.path.join(base, channel, 'index.jsonl')
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def verify_index(base, channel):
    """index.jsonl の SHA-256 と実際のファイルが一致するか。食い違いの一覧を返す（空なら問題なし）。"""
    problems = []
    for e in read_index(base, channel):
        for key in ('snapshot', 'raw'):
            p = os.path.join(base, channel, e[key])
            if not os.path.exists(p):
                problems.append(f'{channel}/{e[key]}: ファイルが無い')
            elif sha256_file(p) != e[key + '_sha256']:
                problems.append(f'{channel}/{e[key]}: SHA-256 が記録と違う（書き換えられた）')
    return problems


def load(base, sources, coll, known_channels):
    """取得結果を段階1の仕組みに読み込む。取得結果1回分を1つの出どころとして扱う。"""
    state = {}
    for ch in CHANNELS:
        entries = read_index(base, ch)
        problems = verify_index(base, ch)
        failed_p = os.path.join(base, ch, 'failed.jsonl')
        n_failed = sum(1 for l in open(failed_p, encoding='utf-8') if l.strip()) if os.path.exists(failed_p) else 0
        state[ch] = {'runs': [], 'problems': problems, 'n_failed': n_failed}
        if problems:
            # 書き換えられた取得結果は読まない
            continue
        cfg = known_channels[ch]
        for e in entries:
            snap = load_json(os.path.join(base, ch, e['snapshot']))
            sid = f"yt_{ch}_{e['run_id']}"
            sources.add({
                'id': sid, 'path': f"snapshots/youtube/{ch}/{e['snapshot']}", 'channel': ch,
                'kind': 'video_list', 'method': 'youtube_data_api',
                'observed_at': snap['finished_at'], 'observed_before': snap['finished_at'],
                'observed_at_note': '動画ごとの正確な取得日時は観測に付いている（videos.list の呼び出し時刻）',
                'status': 'ok',
            })
            if snap.get('channel_id') != cfg['channel_id']:
                coll.anomaly('snapshot_channel_mismatch', source=sid)
                continue
            for v in snap['videos']:
                vid = v['video_id']
                coll.video_obs(ch, vid, sid, title=v.get('title'), published=v.get('published_at'),
                               duration_sec=v.get('duration_sec'), views=v.get('views'),
                               likes=v.get('likes'), comments=v.get('comments'),
                               observed_at=v.get('fetched_at'))
                if v.get('in_uploads_playlist'):
                    coll.mark(ch, vid, 'list_api', 'ok', sid)
                coll.add_feature(ch, vid, sid, {
                    k: v.get(k) for k in ('description', 'tags', 'category_id', 'default_language',
                                          'default_audio_language', 'definition', 'caption_track',
                                          'privacy_status', 'made_for_kids', 'thumbnails',
                                          'fetched_at', 'missing')}, 'ok')
            for nr in snap['not_returned']:
                coll.api_not_returned.append({'channel': ch, 'source': sid, 'at': snap['finished_at'], **nr})
            for fr in snap['foreign']:
                coll.anomaly('foreign_channel_video', source=sid, **fr)
            state[ch]['runs'].append({
                'source': sid, 'started_at': snap['started_at'], 'finished_at': snap['finished_at'],
                'units_total': snap['units_total'], 'n_videos': len(snap['videos']),
                'uploads_count': snap['uploads_count'], 'playlist_pages': snap['playlist_pages'],
                'n_not_returned': len(snap['not_returned']),
                'channel_stats': snap['channel_stats'],
                'server_dates': sorted({c.get('server_date') for c in snap['calls'] if c.get('server_date')}),
            })
    coll.snapshots = state
