"""段階4a：規則に基づく分析（チャンネルを混ぜない・推測で埋めない・読み取り専用・再現できる）。"""
import csv
import filecmp
import hashlib
import json
import os

import pytest

from analysis import common, compare, metrics, run_4a, title_features
from conftest import MCS

CFG = {'neighbors': {'dream': 2, 'smp': 2}, 'min_age_days': 30, 'max_duration_sec': 180,
       'top_share': 0.2, 'bottom_share': 0.2, 'permutations': 200, 'seed': 1, 'min_n': 5,
       'q_threshold': 0.1, 'effect_threshold_numeric': 0.3, 'effect_threshold_share': 0.2}


def _rec(i, views, age=100, dur=40):
    return {'video_id': f'v{i:010d}', 'views': views, 'published_at': f'2026-01-{i + 1:02d}T00:00:00Z',
            'age_days': age, 'duration_sec': dur, 'group': None}


def test_relative_views_excludes_self_and_young_neighbors():
    recs = [_rec(0, 100), _rec(1, 200), _rec(2, 1000), _rec(3, 300), _rec(4, 400), _rec(5, 9999, age=5)]
    metrics.add_relative(recs, CFG, 'dream')
    by = {r['video_id']: r for r in recs}
    # v2 の前後2本：100, 200, 300, 400 → 中央値 250。若い v5 は前後に入れない
    assert by['v0000000002']['n_neighbors'] == 4 and by['v0000000002']['rel_api'] == 4.0
    # 端：v0 は後ろの2本だけ（200, 1000）→ 中央値 600
    assert by['v0000000000']['n_neighbors'] == 2 and by['v0000000000']['rel_api'] == round(100 / 600, 4)
    # 若い動画も相対再生は計算する（前後は v3, v4）
    assert by['v0000000005']['n_neighbors'] == 2


def test_groups_top_bottom_and_separate_frames():
    recs = [_rec(i, 100 + i) for i in range(10)] + [_rec(10, 50, age=10), _rec(11, 50, dur=200)]
    recs.append({'video_id': 'vnoapi00000', 'views': None, 'published_at': None, 'age_days': None,
                 'duration_sec': None, 'group': None})
    metrics.add_relative(recs, CFG, 'dream')
    metrics.assign_groups(recs, CFG)
    g = {r['video_id']: r['group'] for r in recs}
    assert sum(v == 'top' for v in g.values()) == 2 and sum(v == 'bottom' for v in g.values()) == 2
    assert g['v0000000010'] == 'young' and g['v0000000011'] == 'long' and g['vnoapi00000'] == 'no_api'


def test_title_features():
    tn = common.load_tn_feat()
    f = title_features.title_features('この男は道徳の授業を受けたことがありません。#shorts #マイクラ', tn)
    assert f['t_core'] == 'この男は道徳の授業を受けたことがありません。' and f['t_hashtags'] == 2
    assert f['t_demonstrative_start'] is True and f['t_has_question'] is False
    g = title_features.title_features('ところでこの怪物の名前知っている方いますか？', tn)
    assert g['t_has_question'] is True and g['t_ending'] == '問いかけ'
    assert title_features.title_features(None, tn) == {'t_status': None}     # 値が無ければ埋めない


def test_stats_helpers():
    assert common.cliffs_delta([3, 4], [1, 2]) == 1.0 and common.cliffs_delta([1], [1]) == 0.0
    assert common.bh_qvalues([0.01, 0.04, None, 0.03]) == [0.03, 0.04, None, 0.04]
    p1 = common.perm_test([1, 2, 3, 9, 9], [1, 1, 2, 2, 1], common.diff_median, 300, 7)
    assert p1 == common.perm_test([1, 2, 3, 9, 9], [1, 1, 2, 2, 1], common.diff_median, 300, 7)
    rho, n = common.spearman([1, 2, 3, 4], [10, 20, 30, 40])
    assert rho == pytest.approx(1.0) and n == 4


def test_small_groups_are_held():
    recs = [dict(_rec(i, 100 + i), group='top' if i < 3 else 'bottom', rel_api=1.0, duration_sec=10 + i,
                 like_rate=None, comment_rate=None, t_status=None) for i in range(6)]
    rows = compare.compare(recs, dict(CFG, min_n=5), 'smp')
    dur = [r for r in rows if r['feature'] == 'duration_sec'][0]
    assert dur['verdict'] == '判断保留（件数不足）' and dur['p'] is None


@pytest.fixture(scope='module')
def ran(tmp_path_factory):
    before = {n: hashlib.sha256(open(os.path.join(MCS, 'data', n), 'rb').read()).hexdigest()
              for n in ('videos.jsonl', 'features.jsonl')}
    out = tmp_path_factory.mktemp('a4')
    res = run_4a.run(str(out))
    return {'res': res, 'out': out, 'before': before}


def test_data_is_read_only(ran):
    for n, h in ran['before'].items():
        assert hashlib.sha256(open(os.path.join(MCS, 'data', n), 'rb').read()).hexdigest() == h


def test_no_files_written_into_tools(ran):
    """tools/tn_feat.py を読み込んでも、tools/ にキャッシュ（__pycache__）などを作らないこと。"""
    import subprocess
    from conftest import ROOT
    common.load_tn_feat()
    r = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=all', '--ignored', '--', 'tools'],
                       capture_output=True, text=True)
    assert r.stdout.strip() == '', r.stdout


def test_channels_are_not_mixed(ran):
    ids = {}
    for ch in ('dream', 'smp'):
        rows = list(csv.DictReader(open(ran['out'] / ch / 'videos.csv', encoding='utf-8')))
        ids[ch] = {r['video_id'] for r in rows}
        with open(os.path.join(MCS, 'data', 'videos.jsonl'), encoding='utf-8') as f:
            truth = {json.loads(l)['video_id'] for l in f if json.loads(l)['channel'] == ch}
        assert ids[ch] == truth
    assert not ids['dream'] & ids['smp']
    assert len(ids['dream']) == 58 and len(ids['smp']) == 347


def test_groups_follow_settings(ran):
    from collections import Counter
    d = Counter(r['group'] for r in ran['res']['dream']['records'])
    s = Counter(r['group'] for r in ran['res']['smp']['records'])
    assert d['top'] == d['bottom'] == round(58 * 0.2)
    assert s['young'] == 20 and s['long'] == 1 and s['no_api'] == 7
    n_elig = s['top'] + s['mid'] + s['bottom']
    assert s['top'] == s['bottom'] == round(n_elig * 0.2)
    for r in ran['res']['smp']['records']:
        if r['group'] in ('top', 'mid', 'bottom'):
            assert r['age_days'] >= 30 and r['duration_sec'] <= 180


def test_missing_values_are_not_filled(ran):
    recs = {r['video_id']: r for r in ran['res']['smp']['records']}
    noapi = [r for r in recs.values() if r['group'] == 'no_api']
    assert all(r['views'] is None and r['rel_api'] is None for r in noapi)
    nonarr = [r for r in recs.values() if r.get('nc_status') is None]
    assert nonarr and all(r.get('nc_ja_chars') is None for r in nonarr)
    rows = {r['video_id']: r for r in csv.DictReader(open(ran['out'] / 'smp' / 'features.csv', encoding='utf-8'))}
    for r in nonarr:
        assert rows[r['video_id']]['nc_ja_chars'] == ''        # 空欄のまま（0 にしない）
    # SMP には Whisper・実測の特徴を作らない
    assert not any(k.startswith(('nw_', 'm_')) for r in recs.values() for k in r)


def test_unverified_basis_is_labeled(ran):
    for r in ran['res']['smp']['compare']:
        if r['feature'].startswith('nc_'):
            assert r['basis'] == 'UNVERIFIED'
    labels = [r['label'] for r in ran['res']['smp']['compare']]
    assert any('［確認済みのみ］' in x for x in labels) and any('［確認済み＋未確認］' in x for x in labels)


def test_committed_outputs_are_reproducible(ran):
    """mcshorts/analysis/out が、今のコードと data/ から作り直したものと同じであること。"""
    mine = os.path.join(MCS, 'analysis', 'out')
    if not os.path.isdir(mine):
        pytest.skip('analysis/out はまだ作られていない')
    cmp = filecmp.dircmp(mine, str(ran['out']))

    def same(c):
        _, mm, err = filecmp.cmpfiles(c.left, c.right, c.common_files, shallow=False)
        assert not (c.left_only or c.right_only or mm or err), (c.left_only, c.right_only, mm)
        for s in c.subdirs.values():
            same(s)
    same(cmp)
