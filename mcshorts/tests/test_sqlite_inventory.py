"""SQLite の目録（読み取り専用）。テスト用の DB はその場で作り、コミットしない。"""
import json
import os
import sqlite3

import pytest

import build_dataset
from adapters import sqlite_inventory as si
from adapters.common import sha256_file


def make_db(path):
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE videos (video_id TEXT PRIMARY KEY, channel TEXT, views INTEGER, fetched_at TEXT)')
    con.execute('CREATE TABLE "odd ""name""" (x INTEGER)')     # 引用符を含む表名
    con.execute('CREATE VIEW top AS SELECT * FROM videos WHERE views > 10')
    con.execute("INSERT INTO videos VALUES ('cUbDNWd0j24','dream',100,'2026-11-01'), "
                "('ichRl_cub_U','smp',5,'2026-11-01')")
    con.commit()
    con.close()


@pytest.fixture
def imp(tmp_path):
    d = tmp_path / 'imports'
    (d / 'sqlite').mkdir(parents=True)
    (d / 'whisper_cpp').mkdir()
    (d / 'termux').mkdir()
    make_db(str(d / 'sqlite' / 'analysis.db'))
    return d


def test_inventory_lists_tables_without_changing_file(imp):
    p = str(imp / 'sqlite' / 'analysis.db')
    before, mt = sha256_file(p), os.stat(p).st_mtime_ns
    info = si.inventory_file(p)
    assert info['result'] == 'INVENTORIED' and info['unchanged'] is True
    t = {x['name']: x for x in info['tables']}
    assert t['videos']['rows'] == 2 and t['videos']['type'] == 'table'
    assert [c['name'] for c in t['videos']['columns']] == ['video_id', 'channel', 'views', 'fetched_at']
    assert t['top']['type'] == 'view' and t['top']['rows'] == 1
    assert t['odd "name"']['rows'] == 0
    assert sha256_file(p) == before and os.stat(p).st_mtime_ns == mt


def test_connection_is_read_only(imp):
    con = si.open_readonly(str(imp / 'sqlite' / 'analysis.db'))
    with pytest.raises(sqlite3.OperationalError):
        con.execute("INSERT INTO videos VALUES ('x','dream',1,'t')")
    con.close()


def test_build_does_not_import_contents(imp, tmp_path):
    (imp / 'sqlite' / 'mapping.json').write_text('{"videos": {"video_id": "video_id"}}')
    (imp / 'sqlite' / 'notes.txt').write_text('not a db')
    (imp / 'sqlite' / 'analysis.db-wal').write_bytes(b'')
    p = str(imp / 'sqlite' / 'analysis.db')
    before = sha256_file(p)
    res = build_dataset.build(out=str(tmp_path / 'out'), imports_dir=str(imp),
                              snapshots_dir=str(tmp_path / 'nosnap'))
    files = {f['file']: f for f in res['collector'].imports['sqlite']['files']}
    assert files['analysis.db']['imported'] is False
    assert files['analysis.db']['mapping'].startswith('あり')
    assert files['analysis.db']['has_wal'] is True
    assert files['notes.txt']['result'] == 'NOT_SQLITE'
    assert 'analysis.db-wal' not in files and 'mapping.json' not in files
    # 中身は書き起こし・分析結果・観測のどこにも入っていない
    assert not any(t['source'].startswith('sqlite') for d in res['transcripts'].values() for t in d['transcripts'])
    assert not any(f['source'].startswith('sqlite') for f in res['collector'].features)
    assert not any(o['source'].startswith('sqlite') for v in res['videos'] for o in v['views'])
    assert sha256_file(p) == before
    cov = (tmp_path / 'out' / 'reports' / 'coverage.md').read_text(encoding='utf-8')
    assert '中身は取り込んでいない' in cov and 'videos' in cov
    js = json.loads((tmp_path / 'out' / 'data' / 'imports.json').read_text(encoding='utf-8'))
    assert 'sqlite' in js


def test_empty_folder_keeps_stage1_output(tmp_path):
    d = tmp_path / 'imports'
    for sub in ('sqlite', 'whisper_cpp', 'termux'):
        (d / sub).mkdir(parents=True)
    (d / 'sqlite' / 'README.md').write_text('x')
    res = build_dataset.build(out=str(tmp_path / 'out'), imports_dir=str(d), snapshots_dir=str(tmp_path / 'nosnap'))
    assert 'sqlite' not in res['collector'].imports
