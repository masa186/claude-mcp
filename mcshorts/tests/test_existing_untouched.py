"""既存の dream/ tools/ docs/ clips/ が変わっていないこと（作業ツリーとインデックスの両方）。"""
import subprocess

from conftest import ROOT

PATHS = ['dream', 'tools', 'docs', 'clips']


def _git(*args):
    return subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True)


def test_no_changes_against_head(built):
    # built を先に作らせてから確かめる（組み立てが既存ファイルに書いていないこと）
    r = _git('diff', '--quiet', 'HEAD', '--', *PATHS)
    assert r.returncode == 0, _git('diff', '--stat', 'HEAD', '--', *PATHS).stdout


def test_no_untracked_files_in_existing_folders(built):
    r = _git('status', '--porcelain', '--untracked-files=all', '--ignored', '--', *PATHS)
    lines = [l for l in r.stdout.splitlines() if '__pycache__' not in l]
    assert lines == [], lines
