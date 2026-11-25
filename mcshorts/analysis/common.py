"""段階4a の共通部分：既存データの読み込み（読み取り専用）と統計の道具。

読むもの：mcshorts/data/videos.jsonl・features.jsonl・transcripts/、tools/tn_feat.py（関数を借りるだけ）。
どれにも書き込まない。
"""
import json
import math
import os
import random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
MCS = os.path.dirname(HERE)
ROOT = os.path.dirname(MCS)
DATA = os.path.join(MCS, 'data')
CHANNELS = ('dream', 'smp')


def load_config(path=None):
    with open(path or os.path.join(HERE, 'config.json'), encoding='utf-8') as f:
        return json.load(f)


def load_tn_feat():
    """既存の tools/tn_feat.py を読み込む（ファイルは変更しない）。
    importlib の通常の読み込みは tools/__pycache__/ にキャッシュを書くので使わない。
    ソースを文字列として読み、その場で実行する（tools/ には何も書かない）。"""
    import types
    p = os.path.join(ROOT, 'tools', 'tn_feat.py')
    with open(p, encoding='utf-8') as f:
        src = f.read()
    mod = types.ModuleType('tn_feat_readonly')
    mod.__file__ = p
    exec(compile(src, p, 'exec'), mod.__dict__)
    return mod


def load_data(data_dir=DATA):
    """チャンネルごとに分けて返す。{channel: {video_id: record}}。チャンネルをまたいだ集計はしない。"""
    out = {ch: {} for ch in CHANNELS}
    with open(os.path.join(data_dir, 'videos.jsonl'), encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            out[r['channel']][r['video_id']] = {'row': r, 'features': {}, 'transcripts': []}
    with open(os.path.join(data_dir, 'features.jsonl'), encoding='utf-8') as f:
        for line in f:
            x = json.loads(line)
            rec = out[x['channel']].get(x['video_id'])
            if rec is not None:
                rec['features'][x['source']] = {'status': x['status'], 'fields': x['fields']}
    for ch in CHANNELS:
        d = os.path.join(data_dir, 'transcripts', ch)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            with open(os.path.join(d, name), encoding='utf-8') as f:
                doc = json.load(f)
            rec = out[ch].get(doc['video_id'])
            if rec is not None:
                rec['transcripts'] = doc['transcripts']
    return out


# ------------------------------------------------------------------ 統計
def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def cliffs_delta(a, b):
    """a が b より大きい傾向なら正。-1〜1。"""
    if not a or not b:
        return None
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def perm_test(a, b, stat, n_perm, seed):
    """両側の並べ替え検定。p = (|統計量| が観測値以上になった回数 + 1) / (n_perm + 1)。"""
    if not a or not b:
        return None
    obs = abs(stat(a, b))
    pool = list(a) + list(b)
    rng = random.Random(seed)
    k = len(a)
    hit = 0
    for _ in range(n_perm):
        rng.shuffle(pool)
        if abs(stat(pool[:k], pool[k:])) >= obs - 1e-12:
            hit += 1
    return (hit + 1) / (n_perm + 1)


def diff_median(a, b):
    return median(a) - median(b)


def diff_mean(a, b):
    return sum(a) / len(a) - sum(b) / len(b)


def bh_qvalues(pvals):
    """Benjamini-Hochberg。None はそのまま None。"""
    idx = [i for i, p in enumerate(pvals) if p is not None]
    m = len(idx)
    q = [None] * len(pvals)
    if not m:
        return q
    order = sorted(idx, key=lambda i: pvals[i])
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvals[i] * m / rank)
        q[i] = prev
    return q


def spearman(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 3:
        return None, len(pairs)

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return (num / den if den else None), len(pairs)


def group_by(items, key):
    g = defaultdict(list)
    for it in items:
        g[key(it)].append(it)
    return g
