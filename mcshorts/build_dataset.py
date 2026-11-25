"""既存データと取り込みフォルダを読み、共通形式のデータとレポートを作る。

    python3 mcshorts/build_dataset.py            # mcshorts/data と mcshorts/reports に書く
    python3 mcshorts/build_dataset.py --out DIR  # 別の場所に書く（テスト用）

読むもの：config/sources.json に載っている既存ファイル（dream/ tools/）と imports/。
既存ファイルには書き込まない。ネットワークは使わない。
"""
import argparse
import csv
import glob
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from adapters import dream, smp, termux, whisper_cpp  # noqa: E402
from adapters.collector import ITEMS, ITEM_KEYS, Collector  # noqa: E402
from adapters.common import (CHANNELS, MISSING_CODES, Sources, load_json,  # noqa: E402
                             write_json, write_jsonl)

ROOT = os.path.dirname(HERE)

# 外部からは原理的に取れない／記録が無い項目（チャンネル共通）
NOT_ANALYZABLE = [
    ('視聴維持率・平均視聴時間', 'NOT_AVAILABLE', 'YouTube Analytics の数字はチャンネルの持ち主しか見られない'),
    ('インプレッション数・クリック率', 'NOT_AVAILABLE', '同上'),
    ('流入経路・視聴者の属性', 'NOT_AVAILABLE', '同上'),
    ('スワイプ率（Shorts フィードで見られた／スワイプされた割合）', 'NOT_AVAILABLE', '同上'),
    ('既存の再生数を取得した正確な日時', 'UNKNOWN', 'どの出どころにも記録なし。observed_before（コミット日時）が上限'),
    ('どの再生数が最新か', 'UNKNOWN', '取得日時が不明なので決めていない。段階2で取得日時付きで取り直す'),
]

DISPLAY_TITLE_ORDER = ['smp_api_1124', 'smp_api_0830', 'dream_api_five', 'dream_videos']


def build(root=ROOT, out=HERE, imports_dir=None):
    imports_dir = imports_dir or os.path.join(HERE, 'imports')
    sources = Sources(os.path.join(HERE, 'config', 'sources.json'))
    channels = load_json(os.path.join(HERE, 'config', 'channels.json'))['channels']
    assert [c['slug'] for c in channels] == list(CHANNELS)

    coll = Collector(sources)
    dream.load(root, sources, coll)
    smp.load(root, sources, coll)
    whisper_cpp.load(imports_dir, coll, {ch: coll.known_ids(ch) for ch in CHANNELS})
    termux.load(imports_dir, coll)

    videos = coll.build_videos()
    transcripts = coll.build_transcripts()
    coverage = coll.build_coverage()
    conflicts = coll.build_conflicts(videos)

    data_dir = os.path.join(out, 'data')
    rep_dir = os.path.join(out, 'reports')
    # 前回の生成物（書き起こし）を消してから書く。消すのは自分が作った data/transcripts の .json だけ
    for f in glob.glob(os.path.join(data_dir, 'transcripts', '*', '*.json')):
        os.remove(f)

    write_jsonl(os.path.join(data_dir, 'videos.jsonl'), videos)
    for (ch, vid), doc in transcripts.items():
        write_json(os.path.join(data_dir, 'transcripts', ch, f'{vid}.json'), doc)
    write_jsonl(os.path.join(data_dir, 'features.jsonl'),
                sorted(coll.features, key=lambda f: (f['channel'], f['video_id'], f['source'])))
    write_json(os.path.join(data_dir, 'imports.json'), coll.imports)

    os.makedirs(rep_dir, exist_ok=True)
    write_coverage_csv(os.path.join(rep_dir, 'coverage.csv'), coverage, videos)
    write_coverage_md(os.path.join(rep_dir, 'coverage.md'), coll, coverage, videos, transcripts,
                      sources, channels)
    write_conflicts_md(os.path.join(rep_dir, 'conflicts.md'), conflicts, coll.anomalies, videos)
    return {'videos': videos, 'transcripts': transcripts, 'coverage': coverage,
            'conflicts': conflicts, 'collector': coll}


# ---------------------------------------------------------------- 表示用
def cell_text(c):
    if 'status' in c:
        return c['status']
    return '欠損:' + c['missing']['code']


def display_title(v):
    for sid in DISPLAY_TITLE_ORDER:
        for o in v['title']:
            if o['source'] == sid:
                return o['value']
    return v['title'][0]['value'] if v['title'] else ''


def write_coverage_csv(path, coverage, videos):
    vmap = {(v['channel'], v['video_id']): v for v in videos}
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['channel', 'video_id', 'title_display', 'n_view_obs', 'views_min', 'views_max']
                   + ITEM_KEYS + ['missing_notes'])
        for r in coverage:
            v = vmap.get((r['channel'], r['video_id']), {'title': [], 'views': []})
            vs = [x['views'] for x in v['views'] if isinstance(x.get('views'), int)]
            notes = [f"{k}={c['missing']['code']}" + (f"({c['missing']['note']})" if c['missing'].get('note') else '')
                     for k, c in r['cells'].items() if 'missing' in c]
            w.writerow([r['channel'], r['video_id'], display_title(v), len(vs),
                        min(vs) if vs else '', max(vs) if vs else '']
                       + [cell_text(r['cells'][k]) for k in ITEM_KEYS] + [' / '.join(notes)])


def write_coverage_md(path, coll, coverage, videos, transcripts, sources, channels):
    L = []
    a = L.append
    a('# データの充足状況（段階1）')
    a('')
    a('`mcshorts/build_dataset.py` が自動で作るファイル。手で直さない。')
    a('')
    a('- **ok**：値があり、既存の記録で確かめられている')
    a('- **UNVERIFIED**：値はあるが確かめていない（Gemini の読み・ユーザー提供CSV・形式未確認の取り込みなど）')
    a('- **REJECTED**：値はあるが、実ファイルと合わず不採用と記録されている')
    a('- **欠損:コード**：値が無い。推測では埋めていない。コードの意味は下の表')
    a('')
    a('| コード | 意味 |')
    a('|---|---|')
    for k, v in MISSING_CODES.items():
        a(f'| `{k}` | {v} |')
    a('')

    by_ch = defaultdict(list)
    for r in coverage:
        by_ch[r['channel']].append(r)
    names = {c['slug']: f"{c['name']}（{c['name_ja']}）" for c in channels}

    a('## 1. 件数')
    a('')
    a('| チャンネル | 動画（どれかの出どころにある） | API一覧にある | 書き起こしファイル |')
    a('|---|---|---|---|')
    for ch in CHANNELS:
        rows = by_ch[ch]
        api = sum(1 for r in rows if r['cells']['list_api'].get('status') == 'ok')
        tr = sum(1 for (c, _) in transcripts if c == ch)
        a(f'| {names[ch]} | {len(rows)} | {api} | {tr} |')
    a('')
    for d in coll.list_diffs:
        a(f"- {names[d['channel']]}：{d['what']} **{d['count']}本**。{d['note']}")
        if d['video_ids']:
            a('  - ' + ', '.join(f'`{v}`' for v in d['video_ids']))
    a('')

    a('## 2. 項目ごとの充足')
    for ch in CHANNELS:
        rows = by_ch[ch]
        a('')
        a(f'### {names[ch]}（{len(rows)}本）')
        a('')
        a('| 項目 | ok | UNVERIFIED | REJECTED | 欠損（コード別） |')
        a('|---|---|---|---|---|')
        notes = {}
        for key, label in ITEMS:
            cnt = Counter()
            mis = Counter()
            for r in rows:
                c = r['cells'][key]
                if 'status' in c:
                    cnt[c['status']] += 1
                else:
                    mis[c['missing']['code']] += 1
                    if c['missing'].get('note'):
                        notes.setdefault((key, c['missing']['code']), c['missing']['note'])
            m = ', '.join(f'`{k}` {n}' for k, n in sorted(mis.items())) or '—'
            a(f"| {label} | {cnt['ok']} | {cnt['UNVERIFIED']} | {cnt['REJECTED']} | {m} |")
        if notes:
            a('')
            a('欠損の理由（記録されているもの）：')
            for (key, code), note in sorted(notes.items()):
                a(f'- {dict(ITEMS)[key]} `{code}`：{note}')

    a('')
    a('## 3. 分析できない項目（両チャンネル共通）')
    a('')
    a('| 項目 | コード | 理由 |')
    a('|---|---|---|')
    for item, code, why in NOT_ANALYZABLE:
        a(f'| {item} | `{code}` | {why} |')

    a('')
    a('## 4. 出どころと取得日時')
    a('')
    a('`observed_at`（実際の取得日時）はどの既存ファイルにも記録が無い。`observed_before` は取り込み元ブランチに初めてコミットされた日時で、取得日時の上限。')
    a('')
    a('| 出どころ | ファイル | 方法 | 状態 | observed_at | observed_before |')
    a('|---|---|---|---|---|---|')
    for s in sources.meta['sources']:
        a(f"| `{s['id']}` | `{s['path']}` | {s['method']} | {s['status']} | "
          f"{s.get('observed_at') or '不明'} | {s.get('observed_before') or '—'} |")

    a('')
    a('## 5. 文書としてだけ残っている資料（段階1では読み込んでいない）')
    a('')
    for d in sources.meta['docs_only']:
        a(f"- `{d['path']}`（{d['channel']}）：{d['what']}")

    a('')
    a('## 6. 取り込みフォルダ')
    a('')
    w = coll.imports.get('whisper_cpp', {'files': [], 'imported': 0})
    a(f"- `imports/whisper_cpp/`：ファイル {len(w['files'])} 件、取り込み {w['imported']} 件")
    for f in w['files']:
        if f.get('result') != 'IMPORTED':
            a(f"  - `{f['file']}`：**{f.get('result')}** {f.get('note', '')}")
    t = coll.imports.get('termux', {'files': []})
    a(f"- `imports/termux/`：ファイル {len(t['files'])} 件（すべて形式確認待ち。中身は読んでいない）")
    for f in t['files']:
        a(f"  - `{f['file']}`（{f['ext']}, {f['bytes']} bytes）")

    a('')
    a('## 7. 段階1で行っていないこと')
    a('')
    a('- 出どころが違う書き起こし（CSV・Whisper・Gemini）の文の照合。すべて残してあり、照合は段階4で行う')
    a('- 再生数の取り直し（段階2）、文字起こしの追加（段階3）')
    a('- 相対再生の計算し直し。既存の値（`rel`）を出どころ付きで `data/features.jsonl` に残しているだけ')
    a('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


def write_conflicts_md(path, conflicts, anomalies, videos):
    L = []
    a = L.append
    a('# 出どころによって値が食い違う項目（段階1）')
    a('')
    a('自動で作るファイル。どちらが正しいかは決めていない（両方の値を `data/videos.jsonl` に残している）。')
    a('')
    by_field = defaultdict(list)
    for c in conflicts:
        by_field[c['field']].append(c)
    a('| 項目 | 件数 |')
    a('|---|---|')
    for fld in ('title', 'published_date', 'duration_sec'):
        a(f'| {fld} | {len(by_field[fld])} |')
    for fld, rows in sorted(by_field.items()):
        a('')
        a(f'## {fld}')
        a('')
        if rows and rows[0].get('note'):
            a(f"注：{rows[0]['note']}")
            a('')
        a('| チャンネル | 動画ID | 値（出どころ） |')
        a('|---|---|---|')
        for c in rows:
            vals = ' / '.join(f"{str(v['value']).replace('|', '｜')}（{v['source']}）" for v in c['values'])
            a(f"| {c['channel']} | `{c['video_id']}` | {vals} |")

    a('')
    a('## 再生数（食い違いとしては扱わない）')
    a('')
    a('取得時点が違うので値が違うのは当然。取得日時が不明なため、どれが新しいかも決めていない。')
    a('')
    multi = [v for v in videos if len({x['views'] for x in v['views']}) > 1]
    a(f'- 再生数の観測が2つ以上あり、値が違う動画：{len(multi)} 本')
    a(f"- 観測が1つだけの動画：{sum(1 for v in videos if len(v['views']) == 1)} 本")
    a(f"- 観測が無い動画：{sum(1 for v in videos if not v['views'])} 本")

    a('')
    a('## 照合できなかったもの')
    a('')
    if not anomalies:
        a('なし')
    for x in anomalies:
        a('- ' + ', '.join(f'{k}={v}' for k, v in x.items()))
    a('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=HERE)
    ap.add_argument('--imports', default=None)
    args = ap.parse_args()
    r = build(out=args.out, imports_dir=args.imports)
    cnt = Counter(v['channel'] for v in r['videos'])
    print('videos:', dict(cnt), 'transcript files:', len(r['transcripts']),
          'features:', len(r['collector'].features), 'conflicts:', len(r['conflicts']),
          'anomalies:', len(r['collector'].anomalies))


if __name__ == '__main__':
    main()
