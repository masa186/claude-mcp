"""whisper.cpp の各出力形式を読めるか（自作サンプルでの確認）。"""
import os

import pytest

from adapters import whisper_cpp
from conftest import FIXTURES

F = os.path.join(FIXTURES, 'whisper_cpp')
TWO = [(0.0, 2.1), (2.1, 4.56)]


@pytest.mark.parametrize('name', ['sample_oj.json', 'sample.srt', 'sample.vtt', 'sample.csv',
                                  'sample_console.log'])
def test_timed_formats(name):
    segs, _ = whisper_cpp.parse_file(os.path.join(F, name))
    assert [(s['start'], s['end']) for s in segs] == TWO
    assert segs[0]['text'] == 'テスト用の一文目です'
    assert segs[1]['text'].startswith('テスト用の')


def test_srt_multiline_text_is_joined():
    segs, _ = whisper_cpp.parse_file(os.path.join(F, 'sample.srt'))
    assert segs[1]['text'] == 'テスト用の 二文目です'


def test_json_meta_and_tokens():
    segs, meta = whisper_cpp.parse_file(os.path.join(F, 'sample_oj.json'))
    assert meta['model'] == 'base' and meta['language'] == 'ja' and meta['has_tokens'] is False
    segs, meta = whisper_cpp.parse_file(os.path.join(F, 'sample_ojf.json'))
    assert meta['has_tokens'] is True and segs[0]['n_tokens'] == 2
    assert meta['language'] == 'en'


def test_lrc_has_no_end_and_is_not_guessed():
    segs, meta = whisper_cpp.parse_file(os.path.join(F, 'sample.lrc'))
    assert [s['start'] for s in segs] == [0.0, 2.1]
    assert all(s['end'] is None for s in segs)   # 次の行の開始で埋めない
    assert meta.get('no_end') is True


def test_plain_txt_has_no_timestamps():
    segs, meta = whisper_cpp.parse_file(os.path.join(F, 'sample.txt'))
    assert meta['timed'] is False
    assert all(s['start'] is None and s['end'] is None for s in segs)
    assert len(segs) == 2


def test_unsupported_extension_raises(tmp_path):
    p = tmp_path / 'a.wts'
    p.write_text('x')
    with pytest.raises(ValueError):
        whisper_cpp.parse_file(str(p))
