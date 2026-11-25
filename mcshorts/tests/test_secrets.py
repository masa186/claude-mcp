"""API キーが外に漏れないこと・--dry-run がネットワークを使わないこと（偽のキーで確かめる）。"""
import gzip
import json
import os
import urllib.request

import pytest

import build_dataset
import fetch_youtube
from adapters import youtube_api as ya
from fake_youtube import FAKE_KEY, FakeClock, FakeYouTube

DREAM_CID = 'UCDjrYZMZx4zUbLDcKZWnkYw'


def _all_bytes(root):
    for dirpath, _, names in os.walk(root):
        for n in names:
            p = os.path.join(dirpath, n)
            b = open(p, 'rb').read()
            yield p, (gzip.decompress(b) if n.endswith('.gz') else b)


def test_key_never_written_anywhere(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('YOUTUBE_API_KEY', FAKE_KEY)
    legacy = fetch_youtube.legacy_ids('dream')
    ok = fetch_youtube.live('dream', transport=FakeYouTube(DREAM_CID, legacy), clock=FakeClock(),
                            sleep=lambda s: None, base=str(tmp_path / 'snap'))
    # 失敗のとき（応答のメッセージにキーが入っていても）も残さない
    bad = fetch_youtube.live('dream', transport=FakeYouTube(DREAM_CID, legacy, errors={'videos': [403]}),
                             clock=FakeClock('2026-12-01T00:00:00Z'), sleep=lambda s: None,
                             base=str(tmp_path / 'snap'))
    conn = fetch_youtube.live('dream', transport=FakeYouTube(DREAM_CID, legacy, errors={'channels': ['conn'] * 5}),
                              clock=FakeClock('2026-12-02T00:00:00Z'), sleep=lambda s: None,
                              base=str(tmp_path / 'snap'))
    assert ok['result'] == 'ok' and bad['result'] == 'failed' and conn['result'] == 'failed'
    build_dataset.build(out=str(tmp_path / 'out'), imports_dir=str(tmp_path / 'imp'),
                        snapshots_dir=str(tmp_path / 'snap'))
    for p, b in _all_bytes(str(tmp_path)):
        assert FAKE_KEY.encode() not in b, p
    for r in (ok, bad, conn):
        assert FAKE_KEY not in json.dumps(r, ensure_ascii=False)
    out = capsys.readouterr()
    assert FAKE_KEY not in out.out + out.err


def _no_network(*a, **k):
    raise AssertionError('ネットワークに接続しようとした')


def test_dry_run_uses_no_network_and_hides_key(monkeypatch, capsys):
    monkeypatch.setenv('YOUTUBE_API_KEY', FAKE_KEY)
    monkeypatch.setattr(urllib.request, 'urlopen', _no_network)
    monkeypatch.setattr(ya, 'urllib_transport', _no_network)
    for ch in ('dream', 'smp'):
        assert fetch_youtube.main(['--channel', ch, '--dry-run']) == 0
    out = capsys.readouterr().out
    assert FAKE_KEY not in out and '設定あり' in out and '使っていない' in out


def test_mode_is_required():
    with pytest.raises(SystemExit):
        fetch_youtube.main(['--channel', 'dream'])
    with pytest.raises(SystemExit):
        fetch_youtube.main(['--channel', 'minkura', '--dry-run'])


def test_live_without_key_does_not_connect(monkeypatch, tmp_path):
    monkeypatch.delenv('YOUTUBE_API_KEY', raising=False)
    called = []
    with pytest.raises(SystemExit):
        fetch_youtube.live('dream', transport=lambda *a, **k: called.append(1), base=str(tmp_path))
    assert called == [] and not os.listdir(tmp_path)


def test_key_is_read_only_from_env(monkeypatch, tmp_path):
    """既存の tools/ のように .env ファイルを読まない。"""
    monkeypatch.delenv('YOUTUBE_API_KEY', raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / '.env').write_text('YOUTUBE_API_KEY=from-file')
    assert ya.read_key() is None


def test_redactor_handles_encoded_and_query_forms():
    r = ya.Redactor('a b/c')
    assert r('x a b/c y') == 'x *** y'
    assert r('x a%20b%2Fc y') == 'x *** y'
    assert r('https://h/p?id=1&key=zzz&x=2') == 'https://h/p?id=1&key=***&x=2'
    # JSON の中にあっても、引用符を壊さない
    s = json.dumps({'m': 'fetching https://h/p?a=1&key=zzz', 'n': 1})
    assert json.loads(r(s)) == {'m': 'fetching https://h/p?a=1&key=***', 'n': 1}
