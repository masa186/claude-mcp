"""取得結果の保存・チャンネルの分離・段階1データとの統合（偽の API を使う）。"""
import json
import os
import shutil

import pytest

import build_dataset
import fetch_youtube
import integrate
from adapters import youtube_snapshots as ys
from adapters.collector import Collector
from adapters.common import sha256_file
from conftest import DREAM_ID, MCS
from fake_youtube import FAKE_KEY, FakeClock, FakeYouTube

DREAM_CID = 'UCDjrYZMZx4zUbLDcKZWnkYw'
SMP_CID = 'UCAuDKdTeZumLSuox_qmQrCQ'
NEW_ID = 'zzNEWvideo1'


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv('YOUTUBE_API_KEY', FAKE_KEY)


def dream_fake(**kw):
    legacy = fetch_youtube.legacy_ids('dream')
    assert len(legacy) == 58
    # 1本は一覧から外して「返ってこない」にし、1本は新しい動画として足す
    gone = legacy[-1]
    return FakeYouTube(DREAM_CID, [NEW_ID] + legacy[:-1], not_returned={gone}, **kw), gone


def run_live(base, fake, clock='2026-11-26T03:10:00Z', slug='dream'):
    return fetch_youtube.live(slug, transport=fake, clock=FakeClock(clock), sleep=lambda s: None, base=str(base))


def test_save_creates_files_and_index(tmp_path, key):
    fake, _ = dream_fake()
    r = run_live(tmp_path, fake)
    assert r['result'] == 'ok' and r['run_id'].startswith('20261126T0310') and r['run_id'].endswith('Z')
    d = tmp_path / 'dream'
    assert (d / r['snapshot']).exists() and (d / r['raw']).exists()
    assert sha256_file(str(d / r['snapshot'])) == r['snapshot_sha256']
    assert ys.verify_index(str(tmp_path), 'dream') == []
    snap = json.loads((d / r['snapshot']).read_text(encoding='utf-8'))
    assert snap['units_total'] == 5 and snap['channel_id'] == DREAM_CID
    assert snap['code_commit'] and len(snap['code_commit']) == 40


def test_never_overwrites(tmp_path, key):
    fake, _ = dream_fake()
    r = run_live(tmp_path, fake)
    before = sha256_file(str(tmp_path / 'dream' / r['snapshot']))
    fake2, _ = dream_fake()
    with pytest.raises(FileExistsError):
        run_live(tmp_path, fake2)       # 同じ時刻 → 同じ名前
    assert sha256_file(str(tmp_path / 'dream' / r['snapshot'])) == before
    assert len(ys.read_index(str(tmp_path), 'dream')) == 1
    assert not list((tmp_path / 'dream' / 'snapshots').glob('*.tmp'))


def test_failure_leaves_no_snapshot(tmp_path, key):
    fake, _ = dream_fake(errors={'videos': [403]})
    r = run_live(tmp_path, fake)
    assert r['result'] == 'failed' and r['error']['reason'] == 'quotaExceeded'
    d = tmp_path / 'dream'
    assert not (d / 'snapshots').exists() or not list((d / 'snapshots').iterdir())
    assert ys.read_index(str(tmp_path), 'dream') == []
    text = (d / 'failed.jsonl').read_text(encoding='utf-8')
    assert FAKE_KEY not in text and 'quotaExceeded' in text


def test_channels_are_isolated(tmp_path, key):
    smp_dir = tmp_path / 'smp'
    smp_dir.mkdir()
    (smp_dir / 'index.jsonl').write_text('')
    before = sha256_file(str(smp_dir / 'index.jsonl'))
    fake, _ = dream_fake()
    run_live(tmp_path, fake)
    assert sorted(p.name for p in smp_dir.iterdir()) == ['index.jsonl']
    assert sha256_file(str(smp_dir / 'index.jsonl')) == before


def test_tampered_snapshot_is_not_loaded(tmp_path, key):
    fake, _ = dream_fake()
    r = run_live(tmp_path / 'snap', fake)
    p = tmp_path / 'snap' / 'dream' / r['snapshot']
    p.write_text(p.read_text(encoding='utf-8').replace('"views": 1000', '"views": 1'), encoding='utf-8')
    assert ys.verify_index(str(tmp_path / 'snap'), 'dream')
    res = build_dataset.build(out=str(tmp_path / 'out'), imports_dir=str(tmp_path / 'imp'),
                              snapshots_dir=str(tmp_path / 'snap'))
    assert res['collector'].snapshots['dream']['runs'] == []
    assert '取得結果を読み込まなかった' in (tmp_path / 'out' / 'reports' / 'coverage.md').read_text(encoding='utf-8')


@pytest.fixture
def integrated(tmp_path_factory, monkeypatch):
    monkeypatch.setenv('YOUTUBE_API_KEY', FAKE_KEY)
    base = tmp_path_factory.mktemp('snap')
    fake, gone = dream_fake()
    run_live(base, fake, '2026-11-26T03:10:00Z')
    fake2, _ = dream_fake()
    fake2.views = {DREAM_ID: 900}           # 2回目は再生数が減った（直さずに記録されること）
    run_live(base, fake2, '2026-11-27T03:10:00Z')
    out = tmp_path_factory.mktemp('out')
    imp = tmp_path_factory.mktemp('imp')
    res = build_dataset.build(out=str(out), imports_dir=str(imp), snapshots_dir=str(base))
    return {'res': res, 'out': out, 'base': base, 'gone': gone, 'imp': imp}


def test_stage1_data_is_preserved(integrated):
    assert integrate.verify_preserved(os.path.join(MCS, 'data'), str(integrated['out'] / 'data')) == []


def test_exact_time_observations_are_added(integrated):
    rows = {(r['channel'], r['video_id']): r for r in integrated['res']['videos']}
    r = rows[('dream', DREAM_ID)]
    exact = [v for v in r['views'] if v['observed_at']]
    assert len(exact) == 2 and all(v['source'].startswith('yt_dream_') for v in exact)
    assert [v for v in r['views'] if v['observed_at'] is None]        # 段階1の観測も残る
    assert 'views_observed_at' not in r['missing']
    assert ('dream', NEW_ID) in rows                                  # 新しい動画が足される
    assert not any(k[0] == 'smp' and k[1] == NEW_ID for k in rows)


def test_reports_show_decrease_and_not_returned(integrated):
    conf = (integrated['out'] / 'reports' / 'conflicts.md').read_text(encoding='utf-8')
    assert '再生数の減少' in conf and DREAM_ID in conf
    assert 'API が返さなかった動画' in conf and integrated['gone'] in conf
    cov = (integrated['out'] / 'reports' / 'coverage.md').read_text(encoding='utf-8')
    assert '6-2. YouTube API の取得結果' in cov and '低評価数' in cov


def test_features_hold_description_and_tags(integrated):
    feats = [f for f in integrated['res']['collector'].features
             if f['video_id'] == DREAM_ID and f['source'].startswith('yt_dream_')]
    assert feats and feats[0]['fields']['description'] == '説明' and feats[0]['fields']['tags'] == ['minecraft']


def test_likes_zero_vs_null_is_reported_not_rewritten():
    rows = [{'channel': 'dream', 'video_id': 'a' * 11, 'views': [
        {'views': 5, 'likes': 0, 'source': 'old', 'observed_at': None},
        {'views': 6, 'likes': None, 'source': 'yt_x', 'observed_at': '2026-11-26T00:00:00Z'}]}]
    out = Collector.build_likes_zero_vs_null(rows)
    assert out == [{'channel': 'dream', 'video_id': 'a' * 11, 'zero_sources': ['old'], 'null_sources': ['yt_x']}]
    assert rows[0]['views'][0]['likes'] == 0


def test_integrate_applies_only_after_check(integrated, tmp_path):
    target = tmp_path / 'target'
    shutil.copytree(os.path.join(MCS, 'data'), target / 'data')
    shutil.copytree(os.path.join(MCS, 'reports'), target / 'reports')
    r = integrate.run(apply=False, target=str(target), imports_dir=str(integrated['imp']),
                      snapshots_dir=str(integrated['base']))
    assert r['problems'] == [] and r['applied'] is False and r['changed']['data']
    assert integrate.verify_preserved(os.path.join(MCS, 'data'), str(target / 'data')) == []
    assert filecmp_same(os.path.join(MCS, 'data'), str(target / 'data'))   # まだ変わっていない
    r = integrate.run(apply=True, target=str(target), imports_dir=str(integrated['imp']),
                      snapshots_dir=str(integrated['base']))
    assert r['applied'] is True
    assert integrate.verify_preserved(os.path.join(MCS, 'data'), str(target / 'data')) == []


def test_integrate_refuses_when_records_would_be_lost(integrated, tmp_path):
    target = tmp_path / 'target'
    shutil.copytree(os.path.join(MCS, 'data'), target / 'data')
    shutil.copytree(os.path.join(MCS, 'reports'), target / 'reports')
    vj = target / 'data' / 'videos.jsonl'
    lines = vj.read_text(encoding='utf-8').splitlines()
    row = json.loads(lines[0])
    row['views'].append({'views': 1, 'source': 'manual_only', 'observed_at': None, 'observed_before': None,
                         'observed_at_note': None, 'likes': None, 'comments': None})
    lines[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
    vj.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    before = sha256_file(str(vj))
    r = integrate.run(apply=True, target=str(target), imports_dir=str(integrated['imp']),
                      snapshots_dir=str(integrated['base']))
    assert r['problems'] and r['applied'] is False
    assert sha256_file(str(vj)) == before


def filecmp_same(a, b):
    import filecmp
    cmp = filecmp.dircmp(a, b)
    def same(c):
        _, mm, err = filecmp.cmpfiles(c.left, c.right, c.common_files, shallow=False)
        return not (c.left_only or c.right_only or mm or err) and all(same(s) for s in c.subdirs.values())
    return same(cmp)
