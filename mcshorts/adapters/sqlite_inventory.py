"""imports/sqlite/ に置かれた SQLite の目録を作る（表・列・型・行数だけ。中身は取り込まない）。

- 読み取り専用で開く（URI の mode=ro と immutable=1）。書き込みはできない
- 開く前と後で SHA-256 を比べ、ファイルが変わっていないことを確かめる
- mapping.json があっても、段階2では取り込まない（「対応表あり・未取り込み」と記録するだけ）
"""
import os
import sqlite3
import urllib.parse

from .common import sha256_file

SKIP_NAMES = {'README.md', '.gitkeep', 'mapping.json', 'mapping.example.json'}
SQLITE_HEADER = b'SQLite format 3\x00'


def open_readonly(path):
    uri = 'file:' + urllib.parse.quote(os.path.abspath(path)) + '?mode=ro&immutable=1'
    return sqlite3.connect(uri, uri=True)


def _qi(name):
    return '"' + name.replace('"', '""') + '"'


def inventory_file(path):
    info = {'bytes': os.path.getsize(path)}
    with open(path, 'rb') as f:
        head = f.read(16)
    if head != SQLITE_HEADER:
        info['result'] = 'NOT_SQLITE'
        return info
    before = sha256_file(path)
    mtime_before = os.stat(path).st_mtime_ns
    info['sha256'] = before
    info['has_wal'] = os.path.exists(path + '-wal')
    if info['has_wal']:
        info['wal_note'] = '-wal ファイルがある。immutable で開くため、WAL に残る未反映の変更は目録に含まれない'
    tables = []
    con = open_readonly(path)
    try:
        rows = con.execute("SELECT type, name FROM sqlite_master "
                           "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        for typ, name in rows:
            cols = [{'name': c[1], 'type': c[2], 'notnull': bool(c[3]), 'pk': bool(c[5])}
                    for c in con.execute(f'PRAGMA table_info({_qi(name)})').fetchall()]
            try:
                n = con.execute(f'SELECT COUNT(*) FROM {_qi(name)}').fetchone()[0]
            except sqlite3.Error as e:
                n = None
                cols.append({'error': f'{type(e).__name__}: {e}'})
            tables.append({'name': name, 'type': typ, 'columns': cols, 'rows': n})
    finally:
        con.close()
    after = sha256_file(path)
    info['tables'] = tables
    info['unchanged'] = (before == after and os.stat(path).st_mtime_ns == mtime_before)
    info['result'] = 'INVENTORIED' if info['unchanged'] else 'CHANGED_DURING_READ'
    return info


def load(imports_dir, coll):
    folder = os.path.join(imports_dir, 'sqlite')
    files = []
    if os.path.isdir(folder):
        mapping = os.path.exists(os.path.join(folder, 'mapping.json'))
        for dirpath, _, names in os.walk(folder):
            for name in sorted(names):
                if name in SKIP_NAMES or name.endswith(('-wal', '-shm', '-journal')):
                    continue
                full = os.path.join(dirpath, name)
                info = {'file': os.path.relpath(full, folder)}
                try:
                    info.update(inventory_file(full))
                except sqlite3.Error as e:
                    info.update(result='READ_ERROR', note=f'{type(e).__name__}: {e}')
                info['imported'] = False
                info['mapping'] = ('あり（段階2では取り込まない）' if mapping else 'なし（取り込まない）')
                files.append(info)
    files.sort(key=lambda x: x['file'])
    # 何も置かれていないときは記録しない（段階1と同じ出力にするため）
    if files:
        coll.imports['sqlite'] = {'folder': 'imports/sqlite', 'files': files}
