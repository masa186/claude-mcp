"""段階4c-1・4c-2（Dream のナレーション分析）。fugashi が無い環境（システムの Python）では飛ばす。

    mcshorts/.venv/bin/python -m pytest mcshorts/tests/test_narration_4c.py
"""
import csv
import filecmp
import hashlib
import json
import os
import shutil
import subprocess

import pytest

pytest.importorskip('fugashi')

from analysis.narration import build_tracks, nlp, per_video, roles  # noqa: E402
from analysis.narration import sources as S  # noqa: E402
from conftest import MCS, ROOT  # noqa: E402

NARR = os.path.join(MCS, 'analysis', 'narration')
INPUTS = ['dream/narration_list.md', 'dream/data/videos.json', 'mcshorts/data/features.jsonl',
          'mcshorts/analysis/codings/dream/claude_v1.jsonl', 'mcshorts/analysis/codings/dream/review_sample.csv']


def _sha(rel):
    return hashlib.sha256(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    before = {r: _sha(r) for r in INPUTS}
    tdir = tmp_path_factory.mktemp('tracks')
    tracks = build_tracks.build(str(tdir))
    rdir = tmp_path_factory.mktemp('roles')
    shutil.copy(os.path.join(NARR, 'codings', 'dream', 'roles_claude_v1.json'), rdir / 'roles_claude_v1.json')
    # 記入済みの確認結果も引き継いで作り直す（段階4bと同じ。確認結果は分類の記録とは別のファイル）
    rv = os.path.join(NARR, 'codings', 'dream', 'review_roles.csv')
    if os.path.exists(rv):
        shutil.copy(rv, rdir / 'review_roles.csv')
    rres = roles.build(out_dir=str(rdir), tracks_dir=str(tdir), decisions_dir=str(rdir))
    pdir = tmp_path_factory.mktemp('per_video')
    pres = per_video.build(out_dir=str(pdir), tracks_dir=str(tdir))
    return {'tracks': tracks, 'tdir': tdir, 'roles': rres, 'rdir': rdir, 'per': pres, 'pdir': pdir, 'before': before}


def test_counts(built):
    assert len(built['tracks']) == 58
    assert sum(len(t['doc_narration']['rows']) for t in built['tracks'].values()) == 102
    assert len(built['roles']['parts']) == 129
    assert len(built['per']) == 58


def test_doc_and_whisper_times_are_kept_separate(built):
    for t in built['tracks'].values():
        for r in t['doc_narration']['rows']:
            assert set(r) == {'row_index', 'start', 'end', 'text', 'parts', 'status', 'source'}
            assert all(set(p) == {'part_index', 'text'} for p in r['parts'])   # 部分ごとの時刻は作らない
        for s in t['whisper_ja']['segments']:
            # Whisper の単語の時刻は元のまま。字幕とは「時間が重なるか」だけを持つ
            assert all(set(w) == {'start', 'end', 'word'} for w in s['words'])


def test_whisper_text_is_unchanged(built):
    """聞き間違い・表記の違いを直していない（元ファイルの文と同じ）。"""
    for vid, t in built['tracks'].items():
        raw = json.load(open(os.path.join(ROOT, 'dream', 'data', 'asr', f'{vid}.json'), encoding='utf-8'))
        assert [s['text'] for s in t['whisper_ja']['segments']] == [s['text'] for s in raw['ja']['segs']]
        assert [s['text'] for s in t['whisper_en']['segments']] == [s['text'] for s in raw['en']['segs']]


def test_discrepancies_are_kept_not_resolved(built):
    for t in built['tracks'].values():
        assert len(t['discrepancies']) == len(t['doc_narration']['rows'])
    md = open(built['tdir'] / 'discrepancies.md', encoding='utf-8').read()
    assert 'キツジとやって' in md and '羊とやって' in md       # 字幕と Whisper の両方が残る


def test_status_labels(built):
    t = built['tracks']['cUbDNWd0j24']
    assert t['doc_narration']['status'] == 'DOC_OBSERVED' and t['whisper_ja']['status'] == 'ok'
    assert t['csv_tn58']['status'] == 'UNVERIFIED'
    assert t['doc_individual']['interpretation_lines']['status'] == 'DOC_INTERPRETATION'
    assert all(r['stage_label_status'] == 'DOC_INTERPRETATION' for r in t['doc_individual']['structure']['rows'])
    assert all('考察' not in l['tags'] and 'Gemini' not in l['tags'] for l in t['doc_individual']['fact_lines']['lines'])
    assert sum(x['doc_individual']['gemini_lines_excluded'] for x in built['tracks'].values()) == 2


def test_4b_corrections_are_overlaid_not_overwritten(built):
    c = built['tracks']['d2PlYjZcRo0']['codes_4b']['codes']['hook']
    assert c['code'] == 'H_RESULT' and c['effective_code'] == 'HX' and c['review']['result'] == '違う'


def test_roles_quotes_and_rules(built):
    for p in built['roles']['parts']:
        t = built['tracks'][p['video_id']]
        row = t['doc_narration']['rows'][p['row']]
        assert p['quote'] == row['parts'][p['part']]['text'] and p['status'] == 'UNVERIFIED'
        if p['role'] == 'R_REHOOK':
            assert p['start'] >= 10
    assert sum(len(x['evidence']) for x in built['roles']['links']) == 52


def test_wrong_evidence_quote_stops(built, tmp_path):
    d = json.load(open(built['rdir'] / 'roles_claude_v1.json', encoding='utf-8'))
    d['videos']['cUbDNWd0j24']['foreshadow'][0]['evidence'][0]['quote'] = '元データに無い文'
    json.dump(d, open(tmp_path / 'roles_claude_v1.json', 'w', encoding='utf-8'), ensure_ascii=False)
    with pytest.raises(roles.QuoteNotFound):
        roles.build(out_dir=str(tmp_path), tracks_dir=str(built['tdir']), decisions_dir=str(tmp_path))


def test_rehook_rule_is_enforced(built, tmp_path):
    d = json.load(open(built['rdir'] / 'roles_claude_v1.json', encoding='utf-8'))
    d['videos']['cUbDNWd0j24']['roles'][0]['role'] = 'R_REHOOK'      # 0.0秒の行
    json.dump(d, open(tmp_path / 'roles_claude_v1.json', 'w', encoding='utf-8'), ensure_ascii=False)
    with pytest.raises(ValueError):
        roles.build(out_dir=str(tmp_path), tracks_dir=str(built['tdir']), decisions_dir=str(tmp_path))


def test_review_sample_and_preservation(built, tmp_path):
    rows = list(csv.DictReader(open(built['rdir'] / 'review_roles.csv', encoding='utf-8')))
    assert sum(r['kind'] == '文の役割' for r in rows) == 13 and sum(r['kind'] == '伏線' for r in rows) == 6
    shutil.copy(built['rdir'] / 'roles_claude_v1.json', tmp_path / 'roles_claude_v1.json')
    rows[0]['メモ'] = 'テスト'
    with open(tmp_path / 'review_roles.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    roles.build(out_dir=str(tmp_path), tracks_dir=str(built['tdir']), decisions_dir=str(tmp_path))
    again = list(csv.DictReader(open(tmp_path / 'review_roles.csv', encoding='utf-8')))
    assert again[0]['メモ'] == 'テスト'


def test_tool_versions_are_recorded(built):
    for a in built['per'].values():
        assert a['tool']['fugashi'] and a['tool']['unidic_lite'] and a['tool']['dictionary_info'][0]['version']


def test_fuseji_is_not_a_number():
    tn = __import__('analysis.common', fromlist=['load_tn_feat']).load_tn_feat()
    toks = nlp.tokens('〇されることになります')
    f = nlp.flags('〇されることになります', toks, tn)
    assert f['fuseji'] is True and f['number'] is False
    assert nlp.flags('500人を罠にはめる', nlp.tokens('500人を罠にはめる'), tn)['number'] is True


def test_measured_and_interpretation_are_separated(built):
    for a in built['per'].values():
        d = a['items']['8_development']
        assert d['measured']['status'] == 'ok' and d['interpretation']['status'] == 'INTERPRETATION'
        assert '断定しない' in d['interpretation']['rule'] and '断定しない' in d['interpretation']['note']
        assert set(a['items']) == {'1_roles', '2_words', '3_opening_windows', '4_hook', '5_length_speed_pause',
                                   '6_sentence_flags', '7_order_foreshadow', '8_development', '9_ending', '10_timing'}


def test_windows_do_not_split_doc_rows(built):
    w = built['per']['cUbDNWd0j24']['items']['3_opening_windows']['0-1s']
    row = w['doc_subtitle']['rows_starting_in_window'][0]
    assert row['fully_inside'] is False and 'chars' not in row      # 窓をまたぐ行の文字を配分しない


def test_only_dream_is_built():
    assert not os.path.exists(os.path.join(NARR, 'tracks', 'smp'))
    assert not os.path.exists(os.path.join(NARR, 'per_video', 'smp'))
    assert not os.path.exists(os.path.join(NARR, 'tracks', 'minkura'))


def test_inputs_are_read_only(built):
    for r, h in built['before'].items():
        assert _sha(r) == h
    out = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=all', '--',
                          'dream', 'tools', 'docs', 'clips', 'mcshorts/data', 'mcshorts/reports', 'mcshorts/snapshots'],
                         capture_output=True, text=True).stdout
    assert out.strip() == ''


def test_outputs_are_reproducible(built):
    for sub, tmp in (('tracks/dream', built['tdir']), ('per_video/dream', built['pdir'])):
        mine = os.path.join(NARR, sub)
        if not os.path.isdir(mine):
            continue
        c = filecmp.dircmp(mine, str(tmp))
        _, mm, err = filecmp.cmpfiles(c.left, c.right, c.common_files, shallow=False)
        assert not (c.left_only or c.right_only or mm or err), (sub, c.left_only, c.right_only, mm)
    for name in ('roles_claude_v1.jsonl', 'foreshadow_claude_v1.jsonl', 'review_roles.csv'):
        a = os.path.join(NARR, 'codings', 'dream', name)
        if os.path.exists(a):
            assert filecmp.cmp(a, str(built['rdir'] / name), shallow=False), name
