"""YouTube Data API で1チャンネル分を取得し、snapshots/youtube/<channel>/ に保存する。

    python3 mcshorts/fetch_youtube.py --channel dream --dry-run   # ネットワークを使わず、予定だけ表示
    python3 mcshorts/fetch_youtube.py --channel dream --live      # 実際に取得する

- 1回に1チャンネルだけ。--dry-run か --live のどちらかを必ず付ける（付けなければ何もしない）
- キーは環境変数 YOUTUBE_API_KEY から読む。値は表示しない
- data/ と reports/ には書かない。反映は `python3 mcshorts/integrate.py --apply` で行う
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from adapters import youtube_api as ya  # noqa: E402
from adapters import youtube_snapshots as ys  # noqa: E402
from adapters.common import load_json  # noqa: E402

SNAPSHOTS_DIR = os.path.join(HERE, 'snapshots', 'youtube')


def channel_cfg(slug):
    for c in load_json(os.path.join(HERE, 'config', 'channels.json'))['channels']:
        if c['slug'] == slug:
            return c
    raise SystemExit(f'対象外のチャンネル: {slug}')


def legacy_ids(slug, data_dir=None):
    """コミット済みの data/videos.jsonl にある、そのチャンネルの動画ID（読むだけ）。"""
    p = os.path.join(data_dir or os.path.join(HERE, 'data'), 'videos.jsonl')
    out = []
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            for line in f:
                r = json.loads(line)
                if r['channel'] == slug:
                    out.append(r['video_id'])
    return sorted(out)


def code_commit():
    try:
        r = subprocess.run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None
    except Exception:
        return None


def dry_run(slug, data_dir=None, base=SNAPSHOTS_DIR):
    cfg = channel_cfg(slug)
    known = legacy_ids(slug, data_dir)
    calls, units = ya.plan_calls(len(known))
    existing = ys.read_index(base, slug)
    return {
        'channel': slug,
        'channel_id': cfg['channel_id'],
        'api_key': '設定あり' if ya.read_key() else '設定なし（--live は実行できない）',
        'known_video_ids': len(known),
        'planned_calls': [{'endpoint': e, 'calls': n} for e, n in calls],
        'planned_units': units,
        'planned_units_note': '段階1の件数からの見込み。新しい投稿があればページと呼び出しが増える',
        'videos_list_max_ids_per_call': ya.MAX_IDS_PER_VIDEOS_CALL,
        'playlist_pages': '最後のページまで（本数で打ち切らない）',
        'parts': {'channels': ya.CHANNEL_PARTS, 'videos': ya.VIDEO_PARTS},
        'save_to': os.path.relpath(os.path.join(base, slug), ROOT),
        'existing_runs': len(existing),
        'network': '使っていない',
    }


def live(slug, transport=None, clock=None, sleep=None, base=SNAPSHOTS_DIR, data_dir=None):
    cfg = channel_cfg(slug)
    key = ya.read_key()
    if not key:
        raise SystemExit(f'環境変数 {ya.KEY_ENV} が設定されていない。接続しなかった')
    kw = {}
    if transport:
        kw['transport'] = transport
    if clock:
        kw['clock'] = clock
    if sleep:
        kw['sleep'] = sleep
    client = ya.YouTubeClient(key, **kw)
    started = ya.iso(client.clock())
    try:
        snap = ya.fetch_channel(client, cfg, extra_ids=legacy_ids(slug, data_dir))
    except Exception as e:
        rec = e.record() if isinstance(e, ya.ApiError) else {'error': client.redact(f'{type(e).__name__}: {e}')}
        ys.record_failure(base, slug, started, rec, client.calls, client.redact)
        return {'result': 'failed', 'error': rec, 'units_used': client.units}
    snap['code_commit'] = code_commit()
    entry = ys.save(base, snap, ya.raw_gzip_bytes(client), client.redact)
    return {'result': 'ok', **entry}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--channel', required=True, choices=['dream', 'smp'])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry-run', action='store_true')
    g.add_argument('--live', action='store_true')
    args = ap.parse_args(argv)
    if args.dry_run:
        print(json.dumps(dry_run(args.channel), ensure_ascii=False, indent=1))
        return 0
    r = live(args.channel)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r['result'] == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
