"""段階4c-2：文の役割と伏線の分類（Claude・UNVERIFIED）を検査し、出どころ付きの結果と確認対象を作る（Dream だけ）。

    mcshorts/.venv/bin/python mcshorts/analysis/narration/roles.py

- すべての部分（narration_list.md の字幕の行を区切ったもの）に分類が1つずつあるか
- 分類が codebook_roles.json にあるか、10秒の規則（R_REHOOK は10秒以降、予告は10秒より前）を守っているか
- 伏線の根拠の引用が、元データ（構成の表の内容・後のナレーション・Whisper）にそのまま含まれるか
  1つでも合わなければ止める
- 確認対象（約1割）を review_roles.csv に書く。記入済みの確認結果は引き継ぎ、元の分類は書き換えない
"""
import csv
import json
import math
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from analysis.codings import allocate  # noqa: E402

CODINGS = os.path.join(HERE, 'codings', 'dream')
TRACKS = os.path.join(HERE, 'tracks', 'dream')
PREVIEW = {'R_RESULT_PREVIEW', 'R_TWIST_PREVIEW'}
REHOOK = 'R_REHOOK'
REVIEW_SHARE = 0.10
SEED = 20261125
REVIEW_COLS = ['確認結果（正しい/違う）', '正しい分類', 'メモ']


class QuoteNotFound(Exception):
    pass


class ReviewWouldBeLost(Exception):
    pass


def load_codebook():
    with open(os.path.join(HERE, 'codebook_roles.json'), encoding='utf-8') as f:
        return json.load(f)


def load_tracks(tracks_dir=TRACKS):
    out = {}
    for name in sorted(os.listdir(tracks_dir)):
        if name.endswith('.json') and name != 'manifest.json':
            with open(os.path.join(tracks_dir, name), encoding='utf-8') as f:
                t = json.load(f)
            out[t['video_id']] = t
    return out


def _find_evidence(track, src, quote, after_row):
    if src == 'doc_structure':
        for i, r in enumerate(track['doc_individual']['structure']['rows']):
            if quote in r['content']:
                return {'source_file': track['doc_individual']['source'], 'structure_row': i,
                        'range_raw': r['range_raw'], 'status': 'DOC_OBSERVED'}
    elif src == 'doc_narration':
        for r in track['doc_narration']['rows']:
            if r['row_index'] > after_row and any(quote in p['text'] for p in r['parts']):
                return {'source_file': track['doc_narration']['source'], 'row': r['row_index'],
                        'start': r['start'], 'end': r['end'], 'status': 'DOC_OBSERVED'}
    elif src in ('whisper_en', 'whisper_ja'):
        for s in track[src]['segments']:
            if quote in s['text']:
                return {'source_file': track[src]['source'], 'segment_index': s['segment_index'],
                        'start': s['start'], 'end': s['end'], 'status': 'ok'}
    return None


def build_records(tracks, decisions, cb):
    roles_cb = cb['roles']
    parts_out, links_out = [], []
    if sorted(decisions['videos']) != sorted(tracks):
        raise ValueError('分類の動画とナレーションの動画がそろっていない')
    for vid, t in sorted(tracks.items()):
        dec = decisions['videos'][vid]
        want = {(r['row_index'], p['part_index']): (r, p) for r in t['doc_narration']['rows'] for p in r['parts']}
        got = {(d['row'], d['part']): d for d in dec['roles']}
        if set(want) != set(got) or len(got) != len(dec['roles']):
            raise ValueError(f'{vid}: 部分と分類の数・位置がそろっていない')
        for key in sorted(want):
            r, p = want[key]
            d = got[key]
            if d['role'] not in roles_cb or any(a not in roles_cb for a in d['also']):
                raise ValueError(f'{vid} {key}: codebook に無い分類')
            if d['role'] == REHOOK and r['start'] < 10:
                raise ValueError(f'{vid} {key}: R_REHOOK は10秒以降だけ')
            if d['role'] in PREVIEW and r['start'] >= 10:
                raise ValueError(f'{vid} {key}: 10秒以降の予告は R_REHOOK')
            parts_out.append({
                'channel': 'dream', 'video_id': vid, 'row': key[0], 'part': key[1],
                'start': r['start'], 'end': r['end'], 'time_note': '行（字幕の区間）の時刻。部分ごとの時刻は作らない',
                'quote': p['text'], 'quote_source': t['doc_narration']['source'], 'quote_status': 'DOC_OBSERVED',
                'role': d['role'], 'role_label': roles_cb[d['role']]['label'], 'also': d['also'],
                'reason': d['reason'], 'flag': d.get('flag'),
                'status': 'UNVERIFIED', 'coder': decisions['coder'], 'codebook_version': cb['version']})
        for fs in dec['foreshadow']:
            k = (fs['from']['row'], fs['from']['part'])
            if k not in got or (got[k]['role'] not in PREVIEW | {REHOOK}):
                raise ValueError(f'{vid} {k}: 伏線の起点が予告の部分ではない')
            r, p = want[k]
            ev = []
            for e in fs['evidence']:
                hit = _find_evidence(t, e['source'], e['quote'], k[0])
                if hit is None:
                    raise QuoteNotFound(f"{vid} {k}: 回収の根拠の引用が元データに無い: {e['quote'][:40]}")
                ev.append({'source': e['source'], 'quote': e['quote'], **hit})
            if fs['status'] == 'LINKED' and not ev:
                raise ValueError(f'{vid} {k}: LINKED なのに根拠が無い')
            links_out.append({
                'channel': 'dream', 'video_id': vid, 'from_row': k[0], 'from_part': k[1],
                'from_quote': p['text'], 'from_start': r['start'], 'from_role': got[k]['role'],
                'status': fs['status'], 'evidence': ev, 'note': fs.get('note'),
                'review_status': 'UNVERIFIED', 'coder': decisions['coder']})
    return parts_out, links_out


def read_reviews(path):
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            vals = {c: row.get(c, '') for c in REVIEW_COLS}
            if any(vals.values()):
                out[row['item_id']] = vals
    return out


def review_sample(parts, links):
    """部分と伏線のそれぞれ約1割。分類（状態）ごとの本数に比例（最大剰余法）・乱数の種は固定。"""
    def pick(items, key, k, salt):
        by = {}
        for it in items:
            by.setdefault(key(it), []).append(it)
        quota = allocate({c: len(v) for c, v in by.items()}, k)
        rng = random.Random(f'{SEED}-{salt}')
        out = []
        for c in sorted(by):
            pool = sorted(by[c], key=lambda x: (x['video_id'], x.get('row', x.get('from_row')), x.get('part', x.get('from_part'))))
            rng.shuffle(pool)
            out += pool[:quota[c]]
        return out
    ps = pick(parts, lambda x: x['role'], math.ceil(len(parts) * REVIEW_SHARE), 'parts')
    ls = pick(links, lambda x: x['status'], math.ceil(len(links) * REVIEW_SHARE), 'links')
    return ps, ls


def write(parts, links, ps, ls, out_dir=CODINGS, prev_dir=CODINGS):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'roles_claude_v1.jsonl'), 'w', encoding='utf-8') as f:
        for r in parts:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    with open(os.path.join(out_dir, 'foreshadow_claude_v1.jsonl'), 'w', encoding='utf-8') as f:
        for r in links:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    prev = read_reviews(os.path.join(prev_dir, 'review_roles.csv'))
    rows = []
    for r in sorted(ps, key=lambda x: (x['video_id'], x['row'], x['part'])):
        rows.append({'item_id': f"role:{r['video_id']}:{r['row']}:{r['part']}", 'kind': '文の役割',
                     'video_id': r['video_id'], 'seconds': f"{r['start']}〜{r['end']}", 'quote': r['quote'],
                     'classification': f"{r['role']}（{r['role_label']}）" + (f" 副：{' '.join(r['also'])}" if r['also'] else ''),
                     'reason': r['reason'], 'certainty': 'UNVERIFIED' + (f"・注意：{r['flag']}" if r['flag'] else ''),
                     'evidence': ''})
    for r in sorted(ls, key=lambda x: (x['video_id'], x['from_row'], x['from_part'])):
        ev = ' ／ '.join(f"{e['source']}：{e['quote']}" for e in r['evidence'])
        rows.append({'item_id': f"foreshadow:{r['video_id']}:{r['from_row']}:{r['from_part']}", 'kind': '伏線',
                     'video_id': r['video_id'], 'seconds': f"{r['from_start']}〜", 'quote': r['from_quote'],
                     'classification': r['status'], 'reason': r['note'] or '', 'certainty': 'UNVERIFIED',
                     'evidence': ev})
    lost = set(prev) - {x['item_id'] for x in rows}
    if lost:
        raise ReviewWouldBeLost(f'記入済みの確認結果が一覧から外れる: {sorted(lost)[:5]}')
    cols = ['item_id', 'kind', 'video_id', 'seconds', 'quote', 'classification', 'reason', 'certainty', 'evidence'] + REVIEW_COLS
    with open(os.path.join(out_dir, 'review_roles.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({**r, **prev.get(r['item_id'], {c: '' for c in REVIEW_COLS})})


def build(out_dir=CODINGS, tracks_dir=TRACKS, decisions_dir=CODINGS):
    cb = load_codebook()
    with open(os.path.join(decisions_dir, 'roles_claude_v1.json'), encoding='utf-8') as f:
        decisions = json.load(f)
    tracks = load_tracks(tracks_dir)
    parts, links = build_records(tracks, decisions, cb)
    ps, ls = review_sample(parts, links)
    write(parts, links, ps, ls, out_dir, decisions_dir)
    return {'parts': parts, 'links': links, 'review_parts': ps, 'review_links': ls}


if __name__ == '__main__':
    r = build()
    print('部分', len(r['parts']), Counter(p['role'] for p in r['parts']).most_common())
    print('伏線', len(r['links']), Counter(x['status'] for x in r['links']), '根拠の引用', sum(len(x['evidence']) for x in r['links']))
    print('確認対象 部分', len(r['review_parts']), '伏線', len(r['review_links']))
