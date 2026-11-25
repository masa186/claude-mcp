"""段階4b：Claude の分類（decisions_claude_v1.json）を検査し、出どころ付きの分類結果と確認対象の一覧を作る。

    python3 mcshorts/analysis/codings.py

- 引用（quote）が元ファイルの1区間の文に「そのまま」含まれるかを全件確かめる。1件でも無ければ止める
- Dream と SMP は別々のファイルに書く。混ぜない
- 状態はすべて UNVERIFIED
- Gemini の読み（dream_gemini・smp_open）は使わない
- data/ は読むだけ
"""
import csv
import json
import math
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
MCS = os.path.dirname(HERE)
sys.path.insert(0, MCS)

from analysis.common import DATA  # noqa: E402

CODINGS = os.path.join(HERE, 'codings')
STATUS = 'UNVERIFIED'
REVIEW_SHARE = 0.10
SEED = 20261125
FORBIDDEN_SOURCES = {'dream_gemini', 'smp_open'}
SOURCE_OF = {'dream': 'dream_asr', 'smp': 'smp_tn299'}
ORIGINAL_OF = {'smp': 'tools/tn_smp299.json'}


class QuoteNotFound(Exception):
    pass


def load_codebook():
    with open(os.path.join(HERE, 'codebook.json'), encoding='utf-8') as f:
        return json.load(f)


def _channel_ids(data_dir, ch):
    with open(os.path.join(data_dir, 'videos.jsonl'), encoding='utf-8') as f:
        return sorted(json.loads(l)['video_id'] for l in f if json.loads(l)['channel'] == ch)


def _transcript(data_dir, ch, vid):
    p = os.path.join(data_dir, 'transcripts', ch, f'{vid}.json')
    if not os.path.exists(p):
        return None, None
    with open(p, encoding='utf-8') as f:
        return json.load(f), os.path.relpath(p, os.path.dirname(MCS))


def _find(entry, quote, exact=False):
    for s in entry['segments']:
        t = (s.get('text') or '').strip()
        if (t == quote) if exact else (quote in t):
            return {'start': s.get('start'), 'end': s.get('end')}
    return None


def _record(ch, vid, dim, d, cb, src_file, entry, original, coder):
    code = d['code']
    codes = cb['dimensions'][dim]['codes']
    if code not in codes:
        raise ValueError(f'{ch}/{vid}/{dim}: codebook に無い分類 {code}')
    for a in d.get('also', []):
        if a not in codes:
            raise ValueError(f'{ch}/{vid}/{dim}: codebook に無い分類 {a}')
    r = {
        'channel': ch, 'video_id': vid, 'dimension': dim,
        'code': code, 'code_label': codes[code]['label'], 'also': d.get('also', []),
        'unclassifiable': code.endswith('X'),
        'status': STATUS, 'coder': coder, 'codebook_version': cb['version'],
        'source_file': src_file, 'source': entry['source'] if entry else None,
        'source_lang': d.get('lang') or (entry.get('lang') if entry else None),
        'source_status': entry.get('status') if entry else None,
        'original_file': original,
        'quote': d.get('quote'), 'quote_segment': None,
        'reason': d['reason'], 'flag': d.get('flag'),
    }
    if r['source'] in FORBIDDEN_SOURCES:
        raise ValueError(f'{ch}/{vid}: 使わない出どころ {r["source"]}')
    if d.get('quote'):
        seg = _find(entry, d['quote'], exact=(ch == 'smp'))
        if seg is None:
            raise QuoteNotFound(f'{ch}/{vid}/{dim}: 引用が元ファイルに見つからない: {d["quote"][:40]}')
        r['quote_segment'] = seg
    return r


def build_dream(cb, data_dir, decisions):
    recs = []
    ids = _channel_ids(data_dir, 'dream')
    if sorted(decisions['videos']) != ids:
        raise ValueError('Dream の分類が全58本とそろっていない')
    for vid in ids:
        doc, path = _transcript(data_dir, 'dream', vid)
        entries = {t['lang']: t for t in doc['transcripts'] if t['source'] == SOURCE_OF['dream'] and t['scope'] == 'full'}
        for dim in ('hook', 'development', 'payoff'):
            d = decisions['videos'][vid][dim]
            lang = d.get('lang') or 'ja'
            e = entries[lang]
            recs.append(_record('dream', vid, dim, d, cb, path, e, e.get('file'), decisions['coder']))
    return recs


def build_smp(cb, data_dir, decisions):
    recs = []
    ids = _channel_ids(data_dir, 'smp')
    extra = set(decisions['videos']) - set(ids)
    if extra:
        raise ValueError(f'SMP の分類に一覧外の動画がある: {sorted(extra)[:5]}')
    for vid in ids:
        doc, path = _transcript(data_dir, 'smp', vid)
        entry = None
        if doc:
            es = [t for t in doc['transcripts'] if t['source'] == SOURCE_OF['smp']]
            entry = es[0] if es else None
        if vid not in decisions['videos']:
            if entry is not None:
                raise ValueError(f'SMP {vid}: 冒頭ナレーションがあるのに分類されていない')
            recs.append({
                'channel': 'smp', 'video_id': vid, 'dimension': 'hook', 'code': None, 'code_label': None,
                'also': [], 'unclassifiable': True, 'status': STATUS, 'coder': None,
                'codebook_version': cb['version'], 'source_file': path, 'source': None, 'source_lang': None,
                'source_status': None, 'original_file': None, 'quote': None, 'quote_segment': None,
                'reason': cb['unclassified_reasons']['NO_TEXT'], 'unclassified_reason': 'NO_TEXT', 'flag': None,
            })
            continue
        d = decisions['videos'][vid]['hook']
        r = _record('smp', vid, 'hook', d, cb, path, entry, ORIGINAL_OF['smp'], decisions['coder'])
        r['draft_code'] = d.get('draft_code')
        r['overridden'] = d.get('overridden')
        recs.append(r)
    return recs


def allocate(counts, k):
    """最大剰余法：本数に比例して k 本を割り当てる。端数が同じなら本数の多い分類を優先。"""
    n = sum(counts.values())
    exact = {c: counts[c] * k / n for c in counts}
    quota = {c: math.floor(v) for c, v in exact.items()}
    order = sorted(counts, key=lambda c: (-(exact[c] - quota[c]), -counts[c], c))
    for c in order[:k - sum(quota.values())]:
        quota[c] += 1
    return quota


def review_sample(recs, ch):
    """約1割を、主分類（フック）ごとの本数に比例させて選ぶ（最大剰余法）。乱数の種は固定。
    分類の数が確認対象の本数より多いと、本数の少ない分類は選ばれないことがある（flag 付きは別に全件を一覧にする）。"""
    hooks = [r for r in recs if r['dimension'] == 'hook' and r['code'] is not None]
    k = math.ceil(len(hooks) * REVIEW_SHARE)
    by = {}
    for r in sorted(hooks, key=lambda r: r['video_id']):
        by.setdefault(r['code'], []).append(r)
    codes = sorted(by)
    quota = allocate({c: len(by[c]) for c in codes}, k)
    rng = random.Random(f'{SEED}-{ch}')
    picked = []
    for c in codes:
        pool = list(by[c])
        rng.shuffle(pool)
        picked += [r['video_id'] for r in pool[:quota[c]]]
    return sorted(picked)


REVIEW_COLS = ['確認結果（正しい/違う）', '正しい分類', 'メモ']


class ReviewWouldBeLost(Exception):
    pass


def read_reviews(path):
    """既に記入された確認結果（記入のある行だけ）。{(video_id, dimension): {列: 値}}"""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            vals = {c: row.get(c, '') for c in REVIEW_COLS}
            if any(vals.values()):
                out[(row['video_id'], row['dimension'])] = vals
    return out


def write_outputs(ch, recs, sample, cb, out_root, prev_reviews=None):
    d = os.path.join(out_root, ch)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'claude_v1.jsonl'), 'w', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    sset = set(sample)
    prev = dict(prev_reviews or {})
    keys = {(r['video_id'], r['dimension']) for r in recs if r['video_id'] in sset}
    lost = sorted(set(prev) - keys)
    if lost:
        # 記入済みの確認結果が一覧から外れるなら、上書きせずに止める
        raise ReviewWouldBeLost(f'{ch}: 記入済みの確認結果が一覧から外れる: {lost[:5]}')
    with open(os.path.join(d, 'review_sample.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['video_id', 'dimension', 'code', 'code_label', 'also', 'quote', 'source_file', 'source_lang',
                    'quote_start_sec', 'reason', 'flag'] + REVIEW_COLS)
        for r in recs:
            if r['video_id'] in sset:
                seg = r['quote_segment'] or {}
                rv = prev.get((r['video_id'], r['dimension']), {})
                w.writerow([r['video_id'], r['dimension'], r['code'], r['code_label'], ' '.join(r['also']),
                            r['quote'] or '', r['source_file'], r['source_lang'] or '', seg.get('start', ''),
                            r['reason'], r.get('flag') or ''] + [rv.get(c, '') for c in REVIEW_COLS])
    write_summary(os.path.join(d, 'summary.md'), ch, recs, sample, cb)


NAMES = {'dream': 'Dream Clips（ドリームクリップ）', 'smp': 'SMP Clips（SMPクリップ）'}


def write_summary(path, ch, recs, sample, cb):
    L = []
    a = L.append
    a(f'# 段階4b 分類結果：{NAMES[ch]}')
    a('')
    a('`mcshorts/analysis/codings.py` が自動で作るファイル。分類の中身は `decisions_claude_v1.json`（Claude が付けたもの）。')
    a('')
    a('- **状態はすべて UNVERIFIED（未確認）**。Claude が文字起こし・ナレーションの「文」だけを読んで付けた。映像は見ていない')
    a('- すべての分類に、元ファイル名・引用（元の文そのまま）・分類の理由を付けている。引用は元ファイルと照合済み')
    a('- このチャンネルだけの結果で、もう一方のチャンネルとは混ぜていない。Gemini の読みは使っていない')
    a('')
    vids = sorted({r['video_id'] for r in recs})
    quotes = [r for r in recs if r['quote']]
    a('## 1. 件数と照合')
    a('')
    a(f'- 動画：{len(vids)}本 ／ 分類の記録：{len(recs)}件')
    a(f'- 引用の照合：{len(quotes)}件すべてが元ファイルの文に含まれていた（1件でも無ければこのファイルは作られない）')
    if ch == 'dream':
        a(f"- 元データ：`mcshorts/data/transcripts/dream/<動画ID>.json` の Whisper 全編（確認済み。元は `dream/data/asr/<動画ID>.json`）")
    else:
        a("- 元データ：`mcshorts/data/transcripts/smp/<動画ID>.json` の冒頭ナレーション（ユーザー提供CSV由来・未確認。元は `tools/tn_smp299.json`）")
        a('- **展開・オチは分類していない**（冒頭ナレーションしか元データが無いため。推測しない）')
        ov = [r for r in recs if r.get('overridden')]
        a(f'- 分類の方法：規則で下書きを作り、Claude が全件を読んで確認・修正（下書きから変えたもの {len(ov)}本）')
    a('')
    dims = ['hook', 'development', 'payoff'] if ch == 'dream' else ['hook']
    for dim in dims:
        dd = cb['dimensions'][dim]
        rs = [r for r in recs if r['dimension'] == dim]
        cnt = Counter(r['code'] for r in rs)
        a(f"## {dd['label']}")
        a('')
        a('| 分類 | 名前 | 本数 |')
        a('|---|---|---|')
        for code, v in sorted(dd['codes'].items(), key=lambda x: x[1]['priority']):
            if cnt.get(code):
                a(f"| `{code}` | {v['label']} | {cnt[code]} |")
        if cnt.get(None):
            a(f"| — | 未分類（{cb['unclassified_reasons']['NO_TEXT']}） | {cnt[None]} |")
        unc = sum(1 for r in rs if r['unclassifiable'])
        a('')
        a(f'未分類・判断不能：**{unc}本**（判断不能 {sum(1 for r in rs if r["code"] and r["code"].endswith("X"))}本、元の文なし {cnt.get(None, 0)}本）')
        a('')
    flagged = [r for r in recs if r.get('flag')]
    a('## 確信が低いもの（flag あり）')
    a('')
    if not flagged:
        a('なし')
    for r in flagged:
        a(f"- `{r['video_id']}` {r['dimension']} `{r['code']}`：{r['flag']}")
    a('')
    a(f'## 確認対象（約{int(REVIEW_SHARE*100)}%・{len(sample)}本）')
    a('')
    a('フックの分類ごとの本数に比例させて選んだ（最大剰余法・乱数の種は固定）。本数の少ない分類は選ばれないことがあるので、上の「確信が低いもの」もあわせて確認してほしい。'
      '`review_sample.csv` の「確認結果」「正しい分類」「メモ」の列に記入してもらう想定。')
    alloc = Counter(r['code'] for r in recs if r['dimension'] == 'hook' and r['video_id'] in set(sample))
    a('')
    a('割り当て：' + '、'.join(f'`{c}` {n}本' for c, n in sorted(alloc.items())))
    a('')
    a('| 動画ID | 次元 | 分類 | 引用 |')
    a('|---|---|---|---|')
    for r in recs:
        if r['video_id'] in set(sample):
            q = (r['quote'] or '（引用なし）').replace('|', '｜')
            a(f"| `{r['video_id']}` | {r['dimension']} | `{r['code']}` {r['code_label']} | {q} |")
    a('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


def build(out_root=CODINGS, data_dir=DATA, decisions_root=CODINGS):
    cb = load_codebook()
    result = {}
    for ch, fn in (('dream', build_dream), ('smp', build_smp)):
        with open(os.path.join(decisions_root, ch, 'decisions_claude_v1.json'), encoding='utf-8') as f:
            decisions = json.load(f)
        recs = fn(cb, data_dir, decisions)
        assert all(r['channel'] == ch and r['status'] == STATUS for r in recs)
        sample = review_sample(recs, ch)
        # 確認結果は decisions と同じ場所（既定では mcshorts/analysis/codings）の review_sample.csv から引き継ぐ
        prev = read_reviews(os.path.join(decisions_root, ch, 'review_sample.csv'))
        write_outputs(ch, recs, sample, cb, out_root, prev)
        result[ch] = {'records': recs, 'sample': sample}
    return result


def main():
    res = build()
    for ch, r in res.items():
        recs = r['records']
        print(ch, '記録', len(recs), '引用照合', sum(1 for x in recs if x['quote']), '未分類・判断不能',
              Counter(x['dimension'] for x in recs if x['unclassifiable']), '確認対象', len(r['sample']))


if __name__ == '__main__':
    main()
