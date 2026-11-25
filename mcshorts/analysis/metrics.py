"""再生数の基準・経過日数・相対再生・グループ分け（1チャンネルずつ）。

グループ：
  top / mid / bottom   比較の対象（API の観測あり・経過 min_age_days 以上・長さ max_duration_sec 以下）を相対再生で並べた上位・中間・下位
  young                経過 min_age_days 未満（伸びている途中。比較から外す）
  long                 長さ max_duration_sec 超（別枠）
  no_api               API の観測が無い（再生数の基準が無い。推測で補わない）
"""
from datetime import datetime

from .common import median


def _dt(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def api_obs(row):
    """取得日時の分かる API の観測のうち、最も新しいもの。無ければ None。"""
    obs = [o for o in row['views'] if o['source'].startswith('yt_') and o.get('observed_at')]
    return max(obs, key=lambda o: o['observed_at']) if obs else None


def _api_value(row, field, source):
    for o in row[field]:
        if o['source'] == source:
            return o['value']
    return None


def base_records(channel_data, cfg, channel, legacy_rel_source):
    """動画ごとの基本の値。API の観測が無い動画は値を None にし、group=no_api とする。"""
    out = []
    for vid, rec in sorted(channel_data.items()):
        row = rec['row']
        ob = api_obs(row)
        r = {'channel': channel, 'video_id': vid}
        legacy = rec['features'].get(legacy_rel_source, {}).get('fields', {}).get('rel')
        r['rel_legacy'] = float(legacy) if legacy not in (None, '') else None
        if ob is None:
            r.update(views=None, likes=None, comments=None, observed_at=None, views_source=None,
                     title=None, published_at=None, duration_sec=None, age_days=None,
                     like_rate=None, comment_rate=None, group='no_api')
            out.append(r)
            continue
        src = ob['source']
        pub = _api_value(row, 'published', src)
        r.update(views=ob['views'], likes=ob.get('likes'), comments=ob.get('comments'),
                 observed_at=ob['observed_at'], views_source=src,
                 title=_api_value(row, 'title', src), published_at=pub,
                 duration_sec=_api_value(row, 'duration_sec', src))
        r['age_days'] = round((_dt(ob['observed_at']) - _dt(pub)).total_seconds() / 86400, 2) if pub else None
        r['like_rate'] = (r['likes'] / r['views']) if r['likes'] is not None and r['views'] else None
        r['comment_rate'] = (r['comments'] / r['views']) if r['comments'] is not None and r['views'] else None
        out.append(r)
    return out


def add_relative(records, cfg, channel):
    """相対再生（投稿順で前後 N 本の中央値との比）。前後の動画は経過 min_age_days 以上のものだけ。"""
    import bisect
    n = cfg['neighbors'][channel]
    pool = sorted(((r['published_at'], r['video_id']), r['views']) for r in records
                  if r['views'] is not None and r['age_days'] is not None and r['age_days'] >= cfg['min_age_days'])
    keys = [k for k, _ in pool]
    for r in records:
        if r['views'] is None or r['published_at'] is None:
            r['rel_api'], r['n_neighbors'] = None, 0
            continue
        me = (r['published_at'], r['video_id'])
        lo = bisect.bisect_left(keys, me)                       # 自分より前の本数
        hi = lo + 1 if lo < len(keys) and keys[lo] == me else lo  # 自分が pool にいれば飛ばす
        nb = [v for _, v in pool[max(0, lo - n):lo]] + [v for _, v in pool[hi:hi + n]]
        m = median(nb)
        r['n_neighbors'] = len(nb)
        r['rel_api'] = round(r['views'] / m, 4) if m else None
    return records


def assign_groups(records, cfg):
    """top / mid / bottom / young / long / no_api。比較の対象だけを相対再生で並べる。"""
    for r in records:
        if r['views'] is None:
            r['group'] = 'no_api'
        elif r['age_days'] is None or r['age_days'] < cfg['min_age_days']:
            r['group'] = 'young'
        elif r['duration_sec'] is None or r['duration_sec'] > cfg['max_duration_sec']:
            r['group'] = 'long'
        else:
            r['group'] = 'eligible'
    elig = sorted((r for r in records if r['group'] == 'eligible' and r['rel_api'] is not None),
                  key=lambda r: (-r['rel_api'], r['video_id']))
    k_top = round(len(elig) * cfg['top_share'])
    k_bot = round(len(elig) * cfg['bottom_share'])
    for i, r in enumerate(elig):
        r['rank'] = i + 1
        r['group'] = 'top' if i < k_top else ('bottom' if i >= len(elig) - k_bot else 'mid')
    for r in records:
        r.setdefault('rank', None)
        if r['group'] == 'eligible':   # 相対再生が計算できなかったもの
            r['group'] = 'no_rel'
    return records


def build(channel_data, cfg, channel, legacy_rel_source):
    recs = base_records(channel_data, cfg, channel, legacy_rel_source)
    add_relative(recs, cfg, channel)
    return assign_groups(recs, cfg)
