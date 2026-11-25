"""imports/whisper_cpp と imports/termux の受け入れ（動画IDの対応付けは推測しない）。"""
import json
import os
import shutil

import pytest

import build_dataset
from conftest import DREAM_ID, FIXTURES, SMP_ID

F = os.path.join(FIXTURES, 'whisper_cpp')


@pytest.fixture(scope='module')
def imported(tmp_path_factory):
    imp = tmp_path_factory.mktemp('imports')
    w = imp / 'whisper_cpp'
    t = imp / 'termux'
    w.mkdir()
    t.mkdir()
    shutil.copy(os.path.join(F, 'sample_oj.json'), w / f'{DREAM_ID}.wav.json')        # ファイル名で対応
    shutil.copy(os.path.join(F, 'sample.srt'), w / f'Some title [{SMP_ID}].srt')     # yt-dlp 風の名前
    shutil.copy(os.path.join(F, 'sample.txt'), w / 'no_id_here.txt')                 # IDなし
    shutil.copy(os.path.join(F, 'sample.vtt'), w / f'{DREAM_ID}_{SMP_ID}.vtt')       # IDが2つ
    shutil.copy(os.path.join(F, 'sample.csv'), w / 'renamed.csv')                    # manifest で対応
    shutil.copy(os.path.join(F, 'sample.lrc'), w / 'other.lrc')                      # 対象外チャンネル
    (w / 'karaoke.wts').write_text('x')                                               # 未対応形式
    (w / 'manifest.csv').write_text(
        'file,video_id,channel,model,language,scope,run_date,note\n'
        f'renamed.csv,{SMP_ID},smp,ggml-small,ja,full,2026-11-20,テスト\n'
        'other.lrc,AAAAAAAAAAA,minkura,,,,,\n', encoding='utf-8')
    (t / 'something.info.json').write_text('{"id": "x"}')
    out = tmp_path_factory.mktemp('out')
    r = build_dataset.build(out=str(out), imports_dir=str(imp))
    r['out'] = str(out)
    return r


def _results(r):
    return {f['file']: f for f in r['collector'].imports['whisper_cpp']['files']}


def test_matched_by_filename(imported):
    res = _results(imported)
    assert res[f'{DREAM_ID}.wav.json']['result'] == 'IMPORTED'
    assert res[f'{DREAM_ID}.wav.json']['matched_by'] == 'filename'
    assert res[f'Some title [{SMP_ID}].srt']['channel'] == 'smp'


def test_not_guessed(imported):
    res = _results(imported)
    assert res['no_id_here.txt']['result'] == 'UNMATCHED'
    assert res[f'{DREAM_ID}_{SMP_ID}.vtt']['result'] == 'UNMATCHED'   # 2つあるので決めない
    assert res['karaoke.wts']['result'] == 'UNSUPPORTED'
    assert res['other.lrc']['result'] == 'OUT_OF_SCOPE'


def test_manifest_and_provenance(imported):
    res = _results(imported)
    assert res['renamed.csv']['matched_by'] == 'manifest'
    doc = imported['transcripts'][('smp', SMP_ID)]
    e = [t for t in doc['transcripts'] if t['source'] == 'whisper_cpp' and t['format'] == 'csv'][0]
    assert e['run_date'] == '2026-11-20' and e['tool'] == 'ggml-small'
    assert e['status'] == 'UNVERIFIED' and len(e['sha256']) == 64
    assert 'run_date' not in e['missing']


def test_missing_run_date_is_reported(imported):
    doc = imported['transcripts'][('dream', DREAM_ID)]
    e = [t for t in doc['transcripts'] if t['source'] == 'whisper_cpp'][0]
    assert e['missing']['run_date']['code'] == 'UNKNOWN'
    assert e['tool'] == 'base'   # JSON の中に書かれていたモデル名


def test_coverage_marks(imported):
    cov = {(r['channel'], r['video_id']): r['cells'] for r in imported['coverage']}
    assert cov[('dream', DREAM_ID)]['whisper_cpp']['status'] == 'UNVERIFIED'
    assert cov[('smp', SMP_ID)]['transcript_full']['status'] == 'UNVERIFIED'   # REJECTED より上
    assert not any(k[0] not in ('dream', 'smp') for k in cov)


def test_termux_is_inventory_only(imported):
    t = imported['collector'].imports['termux']['files']
    assert [f['result'] for f in t] == ['PENDING_FORMAT_CHECK']
    assert not any(tr.get('source') == 'termux'
                   for doc in imported['transcripts'].values() for tr in doc['transcripts'])


def test_imports_json_has_no_absolute_paths(imported):
    s = open(os.path.join(imported['out'], 'data', 'imports.json'), encoding='utf-8').read()
    assert '/tmp/' not in s and '/home/' not in s
    json.loads(s)
