"""共通の形式・欠損の記録・出どころの記録。

原則：値が無いときは推測で埋めず、None にして必ず欠損理由のコードを付ける。
"""
import hashlib
import json
import os
import re
import unicodedata

# 欠損理由のコード（schema.md と同じ）
MISSING_CODES = {
    'NOT_COLLECTED': 'まだ取得していない',
    'SOURCE_LOST': '元データが失われた',
    'QUOTA_LIMIT': '無料枠の上限で取得できなかった',
    'NO_MEDIA': '動画ファイルがない',
    'UNVERIFIED': '確かめていない',
    'REJECTED': '実ファイルと合わず不採用',
    'NOT_AVAILABLE': '外部からは原理的に取得できない',
    'UNMATCHED': '動画IDを特定できない',
    'UNKNOWN': '記録がなく不明',
}

# データの状態（値がある場合）
STATUSES = ('ok', 'UNVERIFIED', 'REJECTED')

CHANNELS = ('dream', 'smp')

# YouTube の動画IDは11文字
VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')


def missing(code, note=None):
    if code not in MISSING_CODES:
        raise ValueError(f'unknown missing code: {code}')
    m = {'code': code}
    if note:
        m['note'] = note
    return m


def is_video_id(s):
    return isinstance(s, str) and bool(VIDEO_ID_RE.match(s))


def norm_title(t):
    """比較用。ハッシュタグ・空白・記号の揺れを落とす（保存する値には使わない）。"""
    t = unicodedata.normalize('NFKC', t or '')
    t = re.sub(r'#\S+', '', t)
    return re.sub(r'[\s　]+', '', t).strip().lower()


def date_part(s):
    """'2026-04-18T11:29:54Z' / '20260418' / '2026-04-18' → '2026-04-18'。読めなければ None。"""
    if not s:
        return None
    s = str(s)
    m = re.match(r'^(\d{4})-?(\d{2})-?(\d{2})', s)
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')


class Sources:
    """config/sources.json（既存データの台帳）を読む。"""

    def __init__(self, path):
        self.meta = load_json(path)
        self.by_id = {s['id']: s for s in self.meta['sources']}

    def __getitem__(self, sid):
        return self.by_id[sid]

    def provenance(self, sid):
        """観測1件に付ける出どころ（取得日時を含む）。"""
        s = self.by_id[sid]
        return {
            'source': sid,
            'observed_at': s.get('observed_at'),
            'observed_before': s.get('observed_before'),
            'observed_at_note': s.get('observed_at_note'),
        }
