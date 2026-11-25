"""伏線の補正レイヤー（v2）。v1 は読むだけで、有効データ51件とその履歴を一時フォルダに作って検査する。

    mcshorts/.venv/bin/python -m pytest mcshorts/tests/test_foreshadow_corrections.py
"""
import filecmp
import hashlib
import json
import os
import shutil
import subprocess
from collections import Counter

import pytest

from analysis.narration import foreshadow_corrections as F  # noqa: E402
from conftest import MCS, ROOT  # noqa: E402

COD = os.path.join(MCS, 'analysis', 'narration', 'codings', 'dream')
REL = 'mcshorts/analysis/narration/'
PROTECTED = [REL + p for p in (
    'codings/dream/foreshadow_claude_v1.jsonl', 'codings/dream/roles_claude_v1.jsonl', 'codings/dream/roles_claude_v1.json',
    'codings/dream/review_roles.csv', 'codebook_roles.json', 'codebook_foreshadow_v2.json',
    'codings/dream/foreshadow_decisions_v2.json', 'codings/dream/role_decisions_v2.json')]
INPUT_NAMES = ['foreshadow_claude_v1.jsonl', 'review_roles.csv', 'foreshadow_decisions_v2.json', 'role_decisions_v2.json']


def _sha(rel):
    with open(os.path.join(ROOT, rel), 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture(scope='module')
def v2(tmp_path_factory):
    before = {r: _sha(r) for r in PROTECTED}
    out = tmp_path_factory.mktemp('v2')
    r = F.build(out_dir=str(out))
    r.update(out=out, before=before, by={x['item_id']: x for x in r['records']},
             lab={x['label']: x for x in r['records'] if x['label']})
    return r


def _copy_inputs(tmp_path):
    for n in INPUT_NAMES:
        shutil.copy(os.path.join(COD, n), tmp_path / n)
    return json.load(open(tmp_path / 'foreshadow_decisions_v2.json', encoding='utf-8'))


def _save(tmp_path, name, data):
    with open(tmp_path / name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def test_all_51_links_in_v1_order(v2):
    v1 = F.load_v1()
    assert [x['item_id'] for x in v2['records']] == [F.item_id(r) for r, _ in v1]
    assert [x['v1_sha256'] for x in v2['records']] == [s for _, s in v1]
    assert len(v2['records']) == 51


def test_counts(v2):
    recs = v2['records']
    assert Counter(x['status'] for x in recs) == {'LINKED': 37, 'HOLD': 7, 'NOT_FOUND_IN_TEXT': 4, 'PARTIAL': 3}
    assert Counter(x['decision_status'] for x in recs) == {'V1_UNCHANGED': 28, 'USER_CONFIRMED': 11, 'RULE': 8, 'USER_DIRECTED': 4}
    assert Counter(x['status'] for x in recs if x['confirmed']) == {'LINKED': 10, 'PARTIAL': 3, 'HOLD': 2}
    assert Counter(x['hold_reason'] for x in recs if x['status'] == 'HOLD') == {'NEEDS_REVIEW': 5, 'ROLE_HOLD': 2}


def test_confirmed_only_for_user_decisions(v2):
    for x in v2['records']:
        assert x['confirmed'] == (x['decision_status'] in ('USER_CONFIRMED', 'USER_DIRECTED')), x['item_id']
    assert sum(x['confirmed'] for x in v2['records']) == 15
    f38 = v2['lab']['F38']
    assert f38['decision_status'] == 'RULE' and f38['confirmed'] is False and f38['status'] == 'HOLD'
    b = f38['basis_user_decision']
    assert b['role_item_id'] == 'role:p4osmEVx7hY:1:0' and b['source'] == 'review_roles.csv'
    assert v2['lab']['F22']['basis_user_decision']['source'] == 'role_decisions_v2.json'
    assert all(x['basis_user_decision'] is None for x in v2['records'] if x['hold_reason'] != 'ROLE_HOLD')


def test_labels_match_the_review_list(v2):
    lab = v2['lab']
    assert lab['F01']['item_id'] == 'foreshadow:1U5Pu0pVtvM:0:0'
    assert lab['F02']['item_id'] == 'foreshadow:1U5Pu0pVtvM:1:1'
    assert lab['F22']['item_id'] == 'foreshadow:TWUEJTjUPmY:1:0'
    assert lab['F45']['item_id'] == 'foreshadow:wYRkhfRSjDs:0:0'
    assert sum(x['label'] is None for x in v2['records']) == 6 == sum(x['reviewed_in_csv'] for x in v2['records'])


def test_rule_b_only_after_the_preview_row(v2):
    for x in v2['records']:
        for e in x['evidence']:
            assert e['timing'] in ('after', 'unknown')
            if e['time_known']:
                assert e['start'] >= x['from_row_end']
        for e in x['concurrent']:
            assert e['timing'] in ('before', 'overlap') and e['start'] < x['from_row_end']
    assert {x['label'] for x in v2['records'] if x['decision_status'] == 'RULE' and x['hold_reason'] == 'NEEDS_REVIEW'} == {'F05', 'F17', 'F24', 'F31'}


def test_rule_a_fact_line_has_no_time(v2):
    unknown = [(x['label'], e) for x in v2['records'] for e in x['evidence'] if not e['time_known']]
    assert [lab for lab, _ in unknown] == ['F20']
    e = unknown[0][1]
    assert e['source'] == 'doc_fact_line' and e['start'] is None and e['timing'] == 'unknown'
    assert e['status'] == 'DOC_OBSERVED' and '画面' in e['tags'] and '考察' not in e['tags']


def test_rule_c_role_hold(v2):
    rh = {x['label'] for x in v2['records'] if x['hold_reason'] == 'ROLE_HOLD'}
    assert rh == {'F22', 'F38'}
    assert v2['lab']['F22']['decision_status'] == 'USER_DIRECTED' and v2['lab']['F38']['decision_status'] == 'RULE'
    assert all(x['from_role_effective'] == 'HOLD' for x in v2['records'] if x['hold_reason'] == 'ROLE_HOLD')


def test_status_fields_are_consistent(v2):
    for x in v2['records']:
        if x['status'] == 'LINKED':
            assert x['evidence'] and not x['not_confirmed']
        elif x['status'] == 'PARTIAL':
            assert x['evidence'] and x['not_confirmed']
        else:
            assert not x['evidence']
        assert (x['status'] == 'HOLD') == (x['hold_reason'] is not None)


def test_not_found_keeps_reference_apart(v2):
    nf = {x['label']: x for x in v2['records'] if x['status'] == 'NOT_FOUND_IN_TEXT'}
    assert set(nf) == {'F01', 'F04', 'F37', 'F41'}
    assert nf['F01']['reference'] == []
    for k in ('F04', 'F37', 'F41'):
        assert nf[k]['evidence'] == [] and [e['kind'] for e in nf[k]['reference']] == ['reference_nearest']
        assert nf[k]['confirmed'] is False


def test_user_decisions(v2):
    lab, by = v2['lab'], v2['by']
    f02 = lab['F02']
    assert [e['range_raw'] for e in f02['evidence']] == ['21.6'] and f02['status'] == 'PARTIAL'
    assert [(e['kind'], e['range_raw']) for e in f02['reference']] == [('before_state', '3〜8')]
    assert f02['not_confirmed'][0]['reason'].startswith('凡ミスの内容')
    lz = by['foreshadow:lzD1xJ46ZC4:2:1']
    assert lz['status'] == 'HOLD' and lz['hold_reason'] == 'NEEDS_REVIEW' and lz['confirmed']
    assert [e['range_raw'] for e in lz['concurrent']] == ['27〜42']
    assert [e['kind'] for e in lz['reference']] == ['past_confirmed_evidence']
    log = {l['item_id']: l for l in v2['logs']}[lz['item_id']]
    assert any(s['kind'] == 'user_review_csv' and '27〜42' in s['memo'] for s in log['steps'])   # 過去の確認は履歴に残る
    assert [e['range_raw'] for e in lab['F34']['evidence']] == ['8〜13']
    assert [e['range_raw'] for e in lab['F34']['concurrent']] == ['3.8〜8']
    for k in ('BwGk9qgSqfU:1:1', 'MzpvoTEXweE:0:1', 'loiMd64_c6Q:0:0', 'wYRkhfRSjDs:1:1'):
        assert by['foreshadow:' + k]['status'] == 'LINKED' and by['foreshadow:' + k]['decision_status'] == 'USER_CONFIRMED'


def test_ai_proposals_are_not_mixed_in(v2):
    assert len(v2['proposals']) == 15 and all(p['confirmed'] is False for p in v2['proposals'])
    lab = v2['lab']
    assert all('ai' not in k for x in v2['records'] for k in x)
    assert lab['F24']['status'] == 'HOLD' and lab['F31']['status'] == 'HOLD'          # AI案（PARTIAL）は使わない
    assert lab['F17']['evidence'] == [] and lab['F05']['status'] == 'HOLD'
    assert '42.6〜49' not in [e['range_raw'] for e in lab['F15']['evidence']]
    assert '15〜25' not in [e['range_raw'] for e in lab['F34']['evidence']]
    v1 = {F.item_id(r): r for r, _ in F.load_v1()}
    for k in ('F15', 'F21', 'F26', 'F32', 'F33', 'F36', 'F39', 'F40', 'F44'):
        x = lab[k]
        assert x['decision_status'] == 'V1_UNCHANGED' and x['confirmed'] is False
        assert [e['quote'] for e in x['evidence']] == [e['quote'] for e in v1[x['item_id']]['evidence']]


def test_quotes_match_the_source_documents(v2):
    n = 0
    for x in v2['records']:
        for e in x['evidence'] + x['concurrent'] + x['reference']:
            with open(os.path.join(ROOT, e['source_file']), encoding='utf-8') as f:
                assert e['quote'] in f.read().splitlines()[e['source_line'] - 1]
            n += 1
    assert n > 51


def test_history_is_kept(v2):
    logs = {l['item_id']: l for l in v2['logs']}
    assert len(logs) == 23
    for x in v2['records']:
        if x['decision_status'] != 'V1_UNCHANGED':
            steps = logs[x['item_id']]['steps']
            assert steps[0]['kind'] == 'v1' and steps[-1]['kind'] == 'effective_v2'


def test_time_word_notes_are_only_notes(v2):
    f11 = v2['lab']['F11']
    note = [n for n in f11['notes'] if n['kind'] == 'time_word'][0]
    assert note['words'] == ['数秒後'] and note['gap_seconds'] == 13.8 and '判定には使わない' in note['text']


def test_outputs_are_reproducible(v2):
    for name in (F.OUT_EFFECTIVE, F.OUT_LOG):
        mine = os.path.join(COD, name)
        if os.path.exists(mine):
            assert filecmp.cmp(mine, str(v2['out'] / name), shallow=False), name


def test_protected_files_unchanged(v2):
    assert {r: _sha(r) for r in PROTECTED} == v2['before']
    out = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=all', '--',
                          'dream', 'tools', 'docs', 'clips', 'mcshorts/data', 'mcshorts/reports', 'mcshorts/snapshots'],
                         capture_output=True, text=True).stdout
    assert out.strip() == ''


def test_wrong_quote_stops(tmp_path):
    d = _copy_inputs(tmp_path)
    d['decisions'][0]['evidence'][0]['quote'] = '元データに無い文'
    _save(tmp_path, 'foreshadow_decisions_v2.json', d)
    with pytest.raises(F.QuoteNotFound):
        F.build(out_dir=str(tmp_path), codings_dir=str(tmp_path))


def test_rule_b_violation_stops(tmp_path):
    d = _copy_inputs(tmp_path)
    f02 = [x for x in d['decisions'] if x.get('label') == 'F02'][0]
    f02['evidence'].append({'source': 'doc_structure', 'range_raw': '3〜8', 'quote': 'スコア「1-2」→「1-3」', 'relation': 'result'})
    _save(tmp_path, 'foreshadow_decisions_v2.json', d)
    with pytest.raises(F.RuleViolation):
        F.build(out_dir=str(tmp_path), codings_dir=str(tmp_path))


def test_partial_needs_not_confirmed(tmp_path):
    d = _copy_inputs(tmp_path)
    [x for x in d['decisions'] if x.get('label') == 'F14'][0]['not_confirmed'] = []
    _save(tmp_path, 'foreshadow_decisions_v2.json', d)
    with pytest.raises(F.RuleViolation):
        F.build(out_dir=str(tmp_path), codings_dir=str(tmp_path))


def test_role_hold_must_be_recorded(tmp_path):
    _copy_inputs(tmp_path)
    rd = json.load(open(tmp_path / 'role_decisions_v2.json', encoding='utf-8'))
    rd['decisions'] = []
    _save(tmp_path, 'role_decisions_v2.json', rd)
    with pytest.raises(F.RuleViolation):        # F22 の ROLE_HOLD に、役割の保留の記録が無い
        F.build(out_dir=str(tmp_path), codings_dir=str(tmp_path))
