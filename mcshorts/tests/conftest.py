import os
import sys

import pytest

MCS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(MCS)
sys.path.insert(0, MCS)

FIXTURES = os.path.join(MCS, 'tests', 'fixtures')

DREAM_ID = 'cUbDNWd0j24'   # dream/data/videos.json の #01
SMP_ID = 'ichRl_cub_U'     # tools/smp_1124.json にある動画


@pytest.fixture(scope='session')
def built(tmp_path_factory):
    """取り込みフォルダが空の状態で、一時フォルダに組み立てる。"""
    import build_dataset
    out = tmp_path_factory.mktemp('out')
    imports = tmp_path_factory.mktemp('imports')
    (imports / 'whisper_cpp').mkdir()
    (imports / 'termux').mkdir()
    r = build_dataset.build(out=str(out), imports_dir=str(imports))
    r['out'] = str(out)
    return r
