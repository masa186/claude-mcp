"""段階4b：Claude の分類（引用の照合・未確認の明記・チャンネルを混ぜない・Gemini を使わない・再現できる）。"""
import filecmp
import hashlib
import json
import os
import shutil
from collections import Counter

import pytest

from analysis import codings
from conftest import MCS

CB = codings.load_codebook()


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    before = {n: hashlib.sha256(open(os.path.join(MCS, 'data', n), 'rb').read()).hexdigest()
              for n in ('videos.jsonl', 'features.jsonl')}
    out = tmp_path_factory.mktemp('codings')
    res = codings.build(out_root=str(out))
    return {'res': res, 'out': out, 'before': before}


def test_counts_and_dimensions(built):
    d, s = built['res']['dream']['records'], built['res']['smp']['records']
    assert len({r['video_id'] for r in d}) == 58 and len(d) == 58 * 3
    assert Counter(r['dimension'] for r in d) == {'hook': 58, 'development': 58, 'payoff': 58}
    assert len(s) == 347 and {r['dimension'] for r in s} == {'hook'}   # SMP は展開・オチを分類しない
    assert sum(1 for r in s if r['code'] is None) == 48                   # 元の文が無いものは未分類


def test_all_records_are_unverified_with_source(built):
    for ch in ('dream', 'smp'):
        for r in built['res'][ch]['records']:
            assert r['status'] == 'UNVERIFIED' and r['channel'] == ch
            assert r['reason']
            if r['code'] is not None:
                assert r['source_file'] and r['source'] and r['original_file']


def test_quotes_match_source_files(built):
    """引用は元ファイルの1区間の文に、そのまま含まれる（SMP は全文一致）。"""
    n = 0
    for ch in ('dream', 'smp'):
        for r in built['res'][ch]['records']:
            if not r['quote']:
                continue
            doc = json.load(open(os.path.join(os.path.dirname(MCS), r['source_file']), encoding='utf-8'))
            texts = [(s.get('text') or '').strip() for t in doc['transcripts'] if t['source'] == r['source']
                     and (ch == 'smp' or t.get('lang') == r['source_lang']) for s in t['segments']]
            assert (r['quote'] in texts) if ch == 'smp' else any(r['quote'] in t for t in texts), r['video_id']
            n += 1
    assert n == 153 + 299


def test_codes_belong_to_codebook_and_dimension(built):
    for ch in ('dream', 'smp'):
        for r in built['res'][ch]['records']:
            if r['code'] is None:
                continue
            assert r['code'] in CB['dimensions'][r['dimension']]['codes']
            for a in r['also']:
                assert a in CB['dimensions'][r['dimension']]['codes']


def test_dream_uses_whisper_full_and_no_gemini(built):
    for r in built['res']['dream']['records']:
        assert r['source'] == 'dream_asr' and r['source_status'] == 'ok'
    for ch in ('dream', 'smp'):
        assert not any(r['source'] in ('dream_gemini', 'smp_open') for r in built['res'][ch]['records'])
    assert all(r['source'] in (None, 'smp_tn299') for r in built['res']['smp']['records'])


def test_channels_are_not_mixed(built):
    d = {r['video_id'] for r in built['res']['dream']['records']}
    s = {r['video_id'] for r in built['res']['smp']['records']}
    assert not d & s
    for ch in ('dream', 'smp'):
        lines = open(built['out'] / ch / 'claude_v1.jsonl', encoding='utf-8').read().splitlines()
        assert all(json.loads(l)['channel'] == ch for l in lines)


def test_review_sample_is_about_ten_percent_and_proportional(built):
    assert len(built['res']['dream']['sample']) == 6      # ceil(58 × 0.1)
    assert len(built['res']['smp']['sample']) == 30       # ceil(299 × 0.1)（元の文が無い48本は除く）
    assert codings.allocate({'a': 27, 'b': 7, 'c': 6, 'd': 5, 'e': 5, 'f': 4, 'g': 2, 'h': 1, 'i': 1}, 6)['a'] == 3
    q = codings.allocate({'a': 10, 'b': 10}, 3)
    assert sum(q.values()) == 3


def test_wrong_quote_stops_the_build(tmp_path):
    dec = tmp_path / 'dec'
    shutil.copytree(os.path.join(MCS, 'analysis', 'codings'), dec)
    p = dec / 'dream' / 'decisions_claude_v1.json'
    d = json.load(open(p, encoding='utf-8'))
    vid = sorted(d['videos'])[0]
    d['videos'][vid]['hook']['quote'] = 'この文は元ファイルに無い'
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    with pytest.raises(codings.QuoteNotFound):
        codings.build(out_root=str(tmp_path / 'out'), decisions_root=str(dec))


def test_data_is_read_only(built):
    for n, h in built['before'].items():
        assert hashlib.sha256(open(os.path.join(MCS, 'data', n), 'rb').read()).hexdigest() == h


def test_committed_outputs_are_reproducible(built):
    mine = os.path.join(MCS, 'analysis', 'codings')
    for ch in ('dream', 'smp'):
        for name in ('claude_v1.jsonl', 'review_sample.csv', 'summary.md'):
            a = os.path.join(mine, ch, name)
            if os.path.exists(a):
                assert filecmp.cmp(a, str(built['out'] / ch / name), shallow=False), f'{ch}/{name}'
