"""段階4a：規則に基づく数値・タイトル・テキスト分析（Dream と SMP を別々に）。

    python3 mcshorts/analysis/run_4a.py              # mcshorts/analysis/out/ に書く
    python3 mcshorts/analysis/run_4a.py --out DIR    # 別の場所に書く（テスト用）

既存の data/ と tools/tn_feat.py は読むだけ。ネットワークは使わない。
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from analysis import compare as cmp  # noqa: E402
from analysis import metrics, text_features, title_features  # noqa: E402
from analysis.common import CHANNELS, DATA, load_config, load_data, load_tn_feat, spearman  # noqa: E402

LEGACY_REL = {'dream': 'dream_tn58', 'smp': 'smp_tn299'}
NAMES = {'dream': 'Dream Clips（ドリームクリップ）', 'smp': 'SMP Clips（SMPクリップ）'}
GROUP_JA = {'top': '上位20%', 'mid': '中間', 'bottom': '下位20%', 'young': '投稿30日未満（別枠）',
            'long': '180秒超（別枠）', 'no_api': 'API の観測なし（別枠）', 'no_rel': '相対再生を計算できない'}


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def analyze_channel(channel, channel_data, cfg, tn):
    recs = metrics.build(channel_data, cfg, channel, LEGACY_REL[channel])
    for r in recs:
        rec = channel_data[r['video_id']]
        r.update(title_features.title_features(r['title'], tn))
        r.update(title_features.top_title_features(channel, rec['features'], tn))
        if channel == 'dream':
            r.update(text_features.dream_features(rec, tn))
        else:
            r.update(text_features.smp_features(rec, tn))
    rows = cmp.compare(recs, cfg, channel)
    return recs, rows


VIDEO_COLS = ['video_id', 'group', 'rank', 'rel_api', 'rel_legacy', 'n_neighbors', 'views', 'likes', 'comments',
              'like_rate', 'comment_rate', 'observed_at', 'views_source', 'published_at', 'age_days', 'duration_sec',
              'title']
COMPARE_COLS = ['label', 'feature', 'kind', 'category', 'basis', 'n_top', 'n_bottom', 'n_all', 'top_value',
                'bottom_value', 'effect', 'p', 'q', 'verdict', 'rel_true', 'n_true', 'rel_false', 'n_false']


def _fmt(v):
    if v is None:
        return ''
    if isinstance(v, float):
        return f'{v:.4f}'.rstrip('0').rstrip('.') if v != int(v) or abs(v) < 1e15 else str(v)
    return v


def write_csv(path, rows, cols):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([_fmt(r.get(c)) for c in cols])


def feature_cols(recs):
    skip = set(VIDEO_COLS) | {'channel', 'views_source'}
    cols = sorted({k for r in recs for k in r} - skip)
    return ['video_id', 'group'] + cols


def write_summary(path, channel, recs, rows, cfg, inputs):
    L = []
    a = L.append
    g = Counter(r['group'] for r in recs)
    elig = [r for r in recs if r['group'] in ('top', 'mid', 'bottom')]
    a(f'# 段階4a 分析結果：{NAMES[channel]}')
    a('')
    a('`mcshorts/analysis/run_4a.py` が自動で作るファイル。手で直さない。**このチャンネルだけの集計**で、もう一方のチャンネルとは混ぜていない。')
    a('')
    a('- 差は**相関**であり、原因とは限らない。本数が少ないものは「判断保留」にしている')
    a('- 値が無い・確認されていない項目は推測で埋めていない。未確認のデータに基づく行は「根拠の状態」に `UNVERIFIED` と出る')
    a('')
    a('## 1. 対象と別枠')
    a('')
    a('| グループ | 本数 |')
    a('|---|---|')
    for k in ('top', 'mid', 'bottom', 'young', 'long', 'no_api', 'no_rel'):
        if g.get(k):
            a(f'| {GROUP_JA[k]} | {g[k]} |')
    a(f'| **比較の対象（上位＋中間＋下位）** | **{len(elig)}** |')
    a('')
    for k in ('young', 'long', 'no_api', 'no_rel'):
        ids = sorted(r['video_id'] for r in recs if r['group'] == k)
        if ids:
            a(f"- {GROUP_JA[k]}：{', '.join(f'`{v}`' for v in ids)}")
    a('')
    a('## 2. 再生数の基準と相対再生')
    a('')
    srcs = Counter(r['views_source'] for r in recs if r['views_source'])
    a(f"- 再生数：動画ごとに、取得日時の分かる YouTube API の観測のうち最も新しいもの（{', '.join(f'`{s}` {n}本' for s, n in sorted(srcs.items()))}）")
    a(f"- 相対再生：再生数 ÷ 投稿順で前後{cfg['neighbors'][channel]}本（自分を除く。経過{cfg['min_age_days']}日以上の動画から取る）の再生数の中央値")
    rho, n = spearman([r['rel_api'] for r in elig], [r['rel_legacy'] for r in elig])
    a(f"- 既存の相対再生（`{LEGACY_REL[channel]}` の rel。取得日時が不明な再生数から計算されたもの）との順位相関：{'—' if rho is None else f'{rho:.3f}'}（{n}本）。照合のためだけに使い、分析には使っていない")
    a(f"- 上位・下位：比較の対象を相対再生で並べた上位{int(cfg['top_share']*100)}%・下位{int(cfg['bottom_share']*100)}%")
    a('')
    for grp, title in (('top', '上位'), ('bottom', '下位')):
        rs = sorted((r for r in recs if r['group'] == grp), key=lambda r: r['rank'])
        a(f'### {title}（{len(rs)}本）')
        a('')
        a('| 順位 | 動画ID | 相対再生 | 再生数 | 経過日数 | 長さ | 題名（ハッシュタグ除く） |')
        a('|---|---|---|---|---|---|---|')
        for r in rs:
            a(f"| {r['rank']} | `{r['video_id']}` | {r['rel_api']:.2f} | {r['views']:,} | {r['age_days']:.0f} | {r['duration_sec']} | {(r.get('t_core') or '').replace('|', '｜')} |")
        a('')
    a('## 3. 上位と下位で差が見られた特徴（傾向）')
    a('')
    a(f"判定：q ≤ {cfg['q_threshold']}（多重比較を補正した値）かつ、効果が閾値以上（数値は Cliff の δ の絶対値 ≥ {cfg['effect_threshold_numeric']}、割合は差の絶対値 ≥ {cfg['effect_threshold_share']}）。")
    a('')
    sig = [r for r in rows if r['verdict'] == '差あり（傾向）']
    if not sig:
        a('**この基準を満たす差は見つからなかった。** 下の表の数字は参考として残している。')
    else:
        a('| 特徴 | 根拠の状態 | 上位 | 下位 | 効果 | q | あり／なしの相対再生（本数） |')
        a('|---|---|---|---|---|---|---|')
        for r in sorted(sig, key=lambda r: -abs(r['effect'])):
            a('| ' + ' | '.join([r['label'], r['basis'], _show(r, 'top_value', r['n_top']), _show(r, 'bottom_value', r['n_bottom']),
                                f"{r['effect']:+.2f}", f"{r['q']:.3f}", _relshow(r)]) + ' |')
    a('')
    a('数値は中央値、有無・分類は割合（上位・下位それぞれで値がある動画のうち）。効果は、数値なら Cliff の δ（上位が大きいほど正）、割合なら差（上位−下位）。')
    a('')
    a('## 4. はっきりした差がなかった特徴（参考）')
    a('')
    a('| 特徴 | 根拠の状態 | 上位 | 下位 | 効果 | q |')
    a('|---|---|---|---|---|---|')
    for r in rows:
        if r['verdict'] == 'はっきりした差なし':
            a('| ' + ' | '.join([r['label'], r['basis'], _show(r, 'top_value', r['n_top']), _show(r, 'bottom_value', r['n_bottom']),
                                '—' if r['effect'] is None else f"{r['effect']:+.2f}", '—' if r['q'] is None else f"{r['q']:.3f}"]) + ' |')
    a('')
    a('## 5. 判断保留（上位・下位のどちらかで値のある動画が5本未満）')
    a('')
    held = [r for r in rows if r['verdict'].startswith('判断保留')]
    if not held:
        a('なし')
    for r in held:
        a(f"- {r['label']}（{r['basis']}）：上位 {r['n_top']}本・下位 {r['n_bottom']}本")
    a('')
    a('## 6. データの状態と、分析していないこと')
    a('')
    for line in DATA_NOTES[channel]:
        a(f'- {line}')
    cov = Counter()
    for r in elig:
        for k in ('tt_status', 'nw_status', 'nc_status'):
            if k in r:
                cov[(k, r[k])] += 1
    a('')
    a('比較の対象での状態の内訳：')
    a('')
    a('| 項目 | ok | UNVERIFIED | 値なし |')
    a('|---|---|---|---|')
    for k, label in (('tt_status', '上部タイトル'), ('nw_status', '冒頭ナレーション（Whisper）'), ('nc_status', '冒頭ナレーション（CSV）')):
        if any(kk == k for kk, _ in cov):
            a(f"| {label} | {cov[(k, 'ok')]} | {cov[(k, 'UNVERIFIED')]} | {cov[(k, None)]} |")
    a('')
    a('## 7. 入力')
    a('')
    for k, v in inputs.items():
        a(f'- `{k}`：SHA-256 `{v}`')
    a('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


DATA_NOTES = {
    'dream': [
        '冒頭ナレーション（Whisper）は確認済みの書き起こしだが、聞き間違いはあり得る（人名など）。CSV の文は未確認',
        '個別分析・実測の数値（フックの秒・カット・字幕の切り替え・BGM）は 58本そろっている',
        'CSV の分類（冒頭の型・赤字の型など）は未確認。フック・展開・オチの分類のし直しは段階4b で行う',
        'Gemini の映像・音の読み（14本だけ）は使っていない',
        '視聴維持率・クリック率などは取得できないので分析していない',
        '58本と少ないので、差が出ても「傾向」としか言えない',
    ],
    'smp': [
        '**全編のナレーション・字幕・展開・オチ・編集の実測は、確認済みのデータが無いので分析していない**（段階3で whisper.cpp などを受け取ってから）',
        '冒頭ナレーションはユーザー提供CSV由来（未確認）だけ。元のCSVはリポジトリに無い',
        '上部タイトルの確認済み（30本）は、再生数の上位15・下位15から選ばれた標本なので偏りがある。「確認済みのみ」の行はこの点に注意',
        'smp_open（Gemini・冒頭8秒、55本）は、再生数で選んだ動画だけなので偏りを避けるため使っていない',
        'API が返さなかった7本は再生数の基準が無いので別枠（推測で補っていない）',
        '視聴維持率・クリック率などは取得できないので分析していない',
    ],
}


def _show(r, key, n):
    v = r[key]
    if v is None:
        return '—'
    if r['kind'] == 'num':
        return f'{v:g}（{n}本）'
    return f'{v*100:.0f}%（{n}本）'


def _relshow(r):
    if r['kind'] == 'num':
        return '—'
    t = '—' if r['rel_true'] is None else f"{r['rel_true']:.2f}"
    f = '—' if r['rel_false'] is None else f"{r['rel_false']:.2f}"
    return f"あり {t}（{r['n_true']}）／なし {f}（{r['n_false']}）"


def run(out_dir=os.path.join(HERE, 'out'), data_dir=DATA):
    cfg = load_config()
    tn = load_tn_feat()
    data = load_data(data_dir)
    inputs = {f'data/{n}': _sha(os.path.join(data_dir, n)) for n in ('videos.jsonl', 'features.jsonl')}
    inputs['tools/tn_feat.py'] = _sha(os.path.join(os.path.dirname(os.path.dirname(HERE)), 'tools', 'tn_feat.py'))
    inputs['analysis/config.json'] = _sha(os.path.join(HERE, 'config.json'))
    result = {}
    for ch in CHANNELS:
        recs, rows = analyze_channel(ch, data[ch], cfg, tn)
        d = os.path.join(out_dir, ch)
        os.makedirs(d, exist_ok=True)
        write_csv(os.path.join(d, 'videos.csv'), sorted(recs, key=lambda r: (r['rank'] is None, r['rank'] or 0, r['video_id'])), VIDEO_COLS)
        write_csv(os.path.join(d, 'features.csv'), sorted(recs, key=lambda r: r['video_id']), feature_cols(recs))
        write_csv(os.path.join(d, 'compare.csv'), rows, COMPARE_COLS)
        write_summary(os.path.join(d, 'summary.md'), ch, recs, rows, cfg, inputs)
        result[ch] = {'records': recs, 'compare': rows}
    with open(os.path.join(out_dir, 'inputs.json'), 'w', encoding='utf-8') as f:
        json.dump({'inputs': inputs, 'config': cfg}, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    args = ap.parse_args()
    res = run(args.out)
    for ch, r in res.items():
        g = Counter(x['group'] for x in r['records'])
        v = Counter(x['verdict'] for x in r['compare'])
        print(ch, dict(g), dict(v))


if __name__ == '__main__':
    main()
