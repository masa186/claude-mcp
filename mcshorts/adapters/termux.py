"""imports/termux/ に置かれたファイルの目録を作る（中身は読まない）。

Termux に何が残っているか（形式・ファイル名の付け方）がまだ分からないので、
段階1では「何が置かれたか」だけを記録し、すべて「形式確認待ち」として報告する。
whisper.cpp の出力は imports/whisper_cpp/ に置けば、そちらで読み込まれる。
"""
import os

from .common import sha256_file

SKIP_NAMES = {'README.md', '.gitkeep'}


def load(imports_dir, coll):
    folder = os.path.join(imports_dir, 'termux')
    files = []
    if os.path.isdir(folder):
        for dirpath, _, names in os.walk(folder):
            for name in sorted(names):
                if name in SKIP_NAMES:
                    continue
                full = os.path.join(dirpath, name)
                files.append({
                    'file': os.path.relpath(full, folder),
                    'ext': os.path.splitext(name)[1].lower() or '(なし)',
                    'bytes': os.path.getsize(full),
                    'sha256': sha256_file(full),
                    'result': 'PENDING_FORMAT_CHECK',
                })
    files.sort(key=lambda x: x['file'])
    coll.imports['termux'] = {'folder': 'imports/termux', 'files': files}
