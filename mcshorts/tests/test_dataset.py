"""既存データからの組み立て：件数・出どころ・欠損の記録・推測で埋めていないこと。"""
import filecmp
import json
import os
from collections import Counter

import build_dataset
from adapters.collector import ITEM_KEYS
from adapters.common import MISSING_CODES, STATUSES
from conftest import DREAM_ID, MCS


def test_channels_and_counts(built):
    cnt = Counter(v['channel'] for v in built['videos'])
    assert set(cnt) == {'dream', 'smp'}
    assert cnt['dream'] == 58
    assert cnt['smp'] == 347          # smp_api_1124 の340本＋8/30の一覧にだけある7本


def test_every_cell_has_status_or_missing_code(built):
    for r in built['coverage']:
        assert set(r['cells']) == set(ITEM_KEYS)
        for c in r['cells'].values():
            if 'status' in c:
                assert c['status'] in STATUSES
            else:
                assert c['missing']['code'] in MISSING_CODES


def test_views_keep_source_and_time(built):
    """段階1の出どころ（config/sources.json の既存データ）の観測は取得日時が null。
    YouTube API の取得結果（出どころ yt_<channel>_<run_id>）の観測は、取得時刻（UTC）を持つ。"""
    import re
    stage1 = {s['id'] for s in json.load(open(os.path.join(MCS, 'config', 'sources.json'), encoding='utf-8'))['sources']}
    utc = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
    for v in built['videos']:
        for o in v['views']:
            assert o['source'] and 'observed_at' in o and 'observed_before' in o
            if o['source'] in stage1:
                assert o['observed_at'] is None        # 既存データには取得日時の記録が無い
            else:
                assert re.match(rf"^yt_{v['channel']}_\d{{8}}T\d{{6}}Z$", o['source']), o['source']
                assert utc.match(o['observed_at']), o['observed_at']
        if v['views'] and all(o['source'] in stage1 for o in v['views']):
            assert v['missing']['views_observed_at']['code'] == 'UNKNOWN'
        elif v['views']:
            assert 'views_observed_at' not in v['missing']


def test_no_single_value_is_chosen(built):
    """出どころが違う値は全部残す。'latest' のような代表値は作らない。"""
    for v in built['videos']:
        assert 'views_latest' not in v
        assert isinstance(v['title'], list)


def test_status_of_known_sources(built):
    cov = {(r['channel'], r['video_id']): r['cells'] for r in built['coverage']}
    dream = [c for (ch, _), c in cov.items() if ch == 'dream']
    assert sum(c['gemini_av'].get('status') == 'UNVERIFIED' for c in dream) == 14
    assert sum(c['gemini_av'].get('missing', {}).get('code') == 'QUOTA_LIMIT' for c in dream) == 44
    assert all(c['transcript_full']['status'] == 'ok' for c in dream)
    smp = [c for (ch, _), c in cov.items() if ch == 'smp']
    full = Counter(c['transcript_full'].get('status') or c['transcript_full']['missing']['code'] for c in smp)
    assert 'ok' not in full                     # SMP の全編は不採用か未取得だけ
    assert full['REJECTED'] > 0


def test_rejected_transcripts_are_labeled(built):
    for (ch, _), doc in built['transcripts'].items():
        for t in doc['transcripts']:
            assert t['status'] in STATUSES
            if t['source'] in ('smp_full', 'smp_voice'):
                assert t['status'] == 'REJECTED'
            if t['source'] in ('smp_open', 'dream_gemini', 'smp_tn299', 'dream_tn58'):
                assert t['status'] == 'UNVERIFIED'


def test_timestamps_not_invented(built):
    """CSV 由来の文には秒が無い。0 などで埋めていないこと。"""
    for doc in built['transcripts'].values():
        for t in doc['transcripts']:
            if t['source'] in ('smp_tn299', 'dream_tn58'):
                assert all(s['start'] is None and s['end'] is None for s in t['segments'])
                assert t['missing']['timestamps']['code'] == 'NOT_COLLECTED'


def test_dream_transcript_shape(built):
    doc = built['transcripts'][('dream', DREAM_ID)]
    srcs = Counter(t['source'] for t in doc['transcripts'])
    assert srcs['dream_asr'] == 2 and srcs['dream_asr_edges'] == 2 and srcs['dream_gemini'] == 1


def test_build_is_deterministic(built, tmp_path):
    imports = tmp_path / 'imports'
    (imports / 'whisper_cpp').mkdir(parents=True)
    (imports / 'termux').mkdir()
    out2 = tmp_path / 'out2'
    build_dataset.build(out=str(out2), imports_dir=str(imports))
    cmp = filecmp.dircmp(built['out'], str(out2))
    _assert_same(cmp)


def _assert_same(cmp):
    assert not cmp.left_only and not cmp.right_only, (cmp.left_only, cmp.right_only)
    _, mismatch, errors = filecmp.cmpfiles(cmp.left, cmp.right, cmp.common_files, shallow=False)
    assert not mismatch and not errors, mismatch
    for sub in cmp.subdirs.values():
        _assert_same(sub)


def _snapshot_sources_in(data_dir):
    """data/videos.jsonl に入っている API 取得結果の出どころ（yt_<channel>_<run_id>）。"""
    out = set()
    with open(os.path.join(data_dir, 'videos.jsonl'), encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            out |= {s for s in r['in_sources'] if s.startswith('yt_')}
    return out


def _copy_snapshots(src, dst, wanted):
    """wanted に含まれる取得結果だけを、index.jsonl の行ごと写す。"""
    import shutil
    from adapters import youtube_snapshots as ys
    for ch in ('dream', 'smp'):
        for e in ys.read_index(src, ch):
            if f"yt_{ch}_{e['run_id']}" not in wanted:
                continue
            for key in ('snapshot', 'raw'):
                p = os.path.join(dst, ch, e[key])
                os.makedirs(os.path.dirname(p), exist_ok=True)
                shutil.copyfile(os.path.join(src, ch, e[key]), p)
            with open(os.path.join(dst, ch, 'index.jsonl'), 'a', encoding='utf-8') as f:
                f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + '\n')


def test_committed_outputs_are_up_to_date(tmp_path):
    """mcshorts/data と mcshorts/reports が、それを作ったときの入力から再現できること。
    入力＝既存データ＋「data/ に既に入っている API 取得結果」だけ（imports は空）。
    まだ反映していない取得結果があっても、ここでは失敗にしない（integrate.py が「変わるファイル」として示す）。"""
    snap = tmp_path / 'snap'
    _copy_snapshots(build_dataset.SNAPSHOTS_DIR, str(snap), _snapshot_sources_in(os.path.join(MCS, 'data')))
    imports = tmp_path / 'imports'
    (imports / 'whisper_cpp').mkdir(parents=True)
    (imports / 'termux').mkdir()
    out = tmp_path / 'out'
    build_dataset.build(out=str(out), imports_dir=str(imports), snapshots_dir=str(snap))
    for sub in ('data', 'reports'):
        mine = os.path.join(MCS, sub)
        if not os.path.isdir(mine):
            continue
        _assert_same(filecmp.dircmp(mine, str(out / sub)))


def test_committed_snapshots_are_intact():
    """置いてある取得結果が index.jsonl の SHA-256 と一致すること（書き換えられていない）。"""
    from adapters import youtube_snapshots as ys
    for ch in ('dream', 'smp'):
        assert ys.verify_index(build_dataset.SNAPSHOTS_DIR, ch) == []


def test_jsonl_is_valid(built):
    for name in ('videos.jsonl', 'features.jsonl'):
        with open(os.path.join(built['out'], 'data', name), encoding='utf-8') as f:
            for line in f:
                json.loads(line)
