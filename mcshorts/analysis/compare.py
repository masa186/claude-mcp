"""上位と下位の比較（1チャンネルずつ）。

特徴の種類：
  num   数値。中央値・Cliff の δ（上位が大きいほど正）・並べ替え検定（中央値の差）
  bool  有無。割合の差（上位−下位）・並べ替え検定（割合の差）・あり／なしごとの相対再生の中央値
  cat   分類。比較対象の中で min_n 本以上ある分類ごとに「その分類かどうか」の bool として比べる
判定：
  上位・下位のどちらかで値のある動画が min_n 本未満 → 「判断保留（件数不足）」
  q ≤ q_threshold かつ 効果が閾値以上 → 「差あり（傾向）」  ※相関であり原因ではない
  それ以外 → 「はっきりした差なし」
値が無い動画（None）は数えない。0 や False で埋めない。
"""
from collections import Counter

from .common import bh_qvalues, cliffs_delta, diff_mean, diff_median, median, perm_test

# (特徴名, 種類, 日本語の名前, 状態の列, 状態の絞り込み)
#   状態の絞り込み：None＝値があるものすべて、'ok'＝確認済みだけ
COMMON_SPECS = [
    ('duration_sec', 'num', '長さ（秒）', None, None),
    ('like_rate', 'num', '高評価率（高評価÷再生）', None, None),
    ('comment_rate', 'num', 'コメント率（コメント÷再生）', None, None),
    ('t_core_len', 'num', '題名の文字数（ハッシュタグ除く）', 't_status', None),
    ('t_hashtags', 'num', '題名のハッシュタグの数', 't_status', None),
    ('t_has_question', 'bool', '題名に？', 't_status', None),
    ('t_has_exclaim', 'bool', '題名に！', 't_status', None),
    ('t_has_ellipsis', 'bool', '題名に…', 't_status', None),
    ('t_has_number', 'bool', '題名に数字', 't_status', None),
    ('t_has_person', 'bool', '題名に人名', 't_status', None),
    ('t_has_quote', 'bool', '題名に引用符', 't_status', None),
    ('t_superlative', 'bool', '題名に最上級の言葉（最強・史上など）', 't_status', None),
    ('t_twist', 'bool', '題名に逆接・ひねり（ですが・まさか等）', 't_status', None),
    ('t_has_ascii_word', 'bool', '題名に英字', 't_status', None),
    ('t_demonstrative_start', 'bool', '題名が「この・その・あの」で始まる', 't_status', None),
    ('t_ending', 'cat', '題名の文末の型', 't_status', None),
]
TOP_TITLE_SPECS = [
    ('tt_lines', 'num', '上部タイトルの行数'),
    ('tt_chars', 'num', '上部タイトルの文字数'),
    ('tt_line1_chars', 'num', '上部タイトル1行目の文字数'),
    ('tt_last_chars', 'num', '上部タイトル最終行の文字数'),
    ('tt_has_question', 'bool', '上部タイトルに？'),
    ('tt_has_exclaim', 'bool', '上部タイトルに！'),
    ('tt_has_number', 'bool', '上部タイトルに数字'),
    ('tt_has_person', 'bool', '上部タイトルに人名'),
    ('tt_superlative', 'bool', '上部タイトルに最上級の言葉'),
    ('tt_twist', 'bool', '上部タイトルに逆接・ひねり'),
]


def narration_specs(prefix, label):
    return [
        (f'{prefix}ja_chars', 'num', f'{label}：日本語の文字数', f'{prefix}status', None),
        (f'{prefix}ending', 'cat', f'{label}：文末の型', f'{prefix}status', None),
        (f'{prefix}has_number', 'bool', f'{label}：数字', f'{prefix}status', None),
        (f'{prefix}has_person', 'bool', f'{label}：人名', f'{prefix}status', None),
        (f'{prefix}has_question', 'bool', f'{label}：問いかけ（？）', f'{prefix}status', None),
        (f'{prefix}superlative', 'bool', f'{label}：最上級の言葉', f'{prefix}status', None),
        (f'{prefix}twist', 'bool', f'{label}：逆接・ひねり', f'{prefix}status', None),
        (f'{prefix}prohibit', 'bool', f'{label}：禁止（〜してはいけません）', f'{prefix}status', None),
        (f'{prefix}result_report', 'bool', f'{label}：結果の報告・予告（〜ました／ことになります）', f'{prefix}status', None),
        (f'{prefix}watch', 'bool', f'{label}：「〜を見る〇〇」型', f'{prefix}status', None),
    ]


DREAM_NUMERIC_LABELS = {
    'm_hook_sec': 'フックの秒（個別分析）', 'm_narr_start_sec': 'ナレーション開始の秒', 'm_narr_lines': '冒頭ナレーションの文の数',
    'm_narr_chars_per_sec': 'ナレーションの速さ（字/秒）', 'm_cuts': 'カット数', 'm_shot_mean_sec': '1カットの平均秒',
    'm_cuts_first3s': '最初の3秒のカット数', 'm_sub_changes': '字幕の切り替え回数', 'm_sub_on_ratio': '字幕が出ている割合',
    'm_music_mean': 'BGM らしさの平均（音タグ）', 'm_music_ge05_ratio': 'BGM が強い時間の割合', 'm_bgm_drops': 'BGM が途切れる回数',
    'm_shot_median': '1カットの秒（中央値）', 'm_motion_median': '画面の動きの大きさ（中央値）', 'm_n_subs': '字幕の枚数（実測）',
    'm_audio_median_db': '音量の中央値（dB）',
}
DREAM_CAT_LABELS = {'c_hook': '冒頭の型（CSV の分類）', 'c_ptype': '投稿タイトルの型（CSV の分類）',
                    'c_redtype': '赤字の型（CSV の分類）', 'c_colp': '上部タイトルの色（CSV の分類）'}


def specs_for(channel):
    s = list(COMMON_SPECS)
    for name, kind, label in TOP_TITLE_SPECS:
        s.append((name, kind, label + '［確認済み＋未確認］', 'tt_status', None))
        s.append((name, kind, label + '［確認済みのみ］', 'tt_status', 'ok'))
    if channel == 'dream':
        s += narration_specs('nw_', '冒頭ナレーション（Whisper）')
        s += narration_specs('nc_', '冒頭ナレーション（CSV・未確認）')
        s += [(k, 'num', v, None, None) for k, v in DREAM_NUMERIC_LABELS.items()]
        s += [(k, 'cat', v, 'c_status', None) for k, v in DREAM_CAT_LABELS.items()]
    else:
        s += narration_specs('nc_', '冒頭ナレーション（CSV・未確認）')
    return s


def _vals(recs, name, status_col, status_filter):
    out = []
    for r in recs:
        if status_col and r.get(status_col) is None:
            continue
        if status_filter and r.get(status_col) != status_filter:
            continue
        v = r.get(name)
        if v is None:
            continue
        out.append((r, v))
    return out


def _basis(recs, status_col, status_filter):
    if status_filter:
        return status_filter
    if not status_col:
        return 'ok'
    st = Counter(r.get(status_col) for r in recs if r.get(status_col))
    return '+'.join(sorted(st)) or '—'


def compare(records, cfg, channel):
    elig = [r for r in records if r['group'] in ('top', 'mid', 'bottom')]
    top = [r for r in elig if r['group'] == 'top']
    bot = [r for r in elig if r['group'] == 'bottom']
    rows = []
    for name, kind, label, status_col, status_filter in specs_for(channel):
        if kind == 'cat':
            vals = _vals(elig, name, status_col, status_filter)
            cats = Counter(v for _, v in vals)
            for cat, n in sorted(cats.items(), key=lambda x: (-x[1], str(x[0]))):
                if n < cfg['min_n']:
                    continue
                rows.append(_bool_row(top, bot, elig, name, f'{label}＝{cat}', status_col, status_filter, cfg,
                                      transform=lambda v, c=cat: v == c, category=cat))
            continue
        if kind == 'num':
            rows.append(_num_row(top, bot, elig, name, label, status_col, status_filter, cfg))
        else:
            rows.append(_bool_row(top, bot, elig, name, label, status_col, status_filter, cfg))
    q = bh_qvalues([r['p'] for r in rows])
    for r, qq in zip(rows, q):
        r['q'] = None if qq is None else round(qq, 4)
        r['verdict'] = _verdict(r, cfg)
    return rows


def _num_row(top, bot, elig, name, label, status_col, status_filter, cfg):
    a = [float(v) for _, v in _vals(top, name, status_col, status_filter)]
    b = [float(v) for _, v in _vals(bot, name, status_col, status_filter)]
    ok = len(a) >= cfg['min_n'] and len(b) >= cfg['min_n']
    return {
        'feature': name, 'label': label, 'kind': 'num', 'category': None,
        'basis': _basis(elig, status_col, status_filter),
        'n_top': len(a), 'n_bottom': len(b), 'n_all': len(_vals(elig, name, status_col, status_filter)),
        'top_value': _r(median(a)), 'bottom_value': _r(median(b)),
        'effect': _r(cliffs_delta(a, b)) if ok else None,
        'p': round(perm_test(a, b, diff_median, cfg['permutations'], cfg['seed']), 4) if ok else None,
        'rel_true': None, 'n_true': None, 'rel_false': None, 'n_false': None,
    }


def _bool_row(top, bot, elig, name, label, status_col, status_filter, cfg, transform=None, category=None):
    tf = transform or bool
    a = [1 if tf(v) else 0 for _, v in _vals(top, name, status_col, status_filter)]
    b = [1 if tf(v) else 0 for _, v in _vals(bot, name, status_col, status_filter)]
    allv = [(r, tf(v)) for r, v in _vals(elig, name, status_col, status_filter)]
    ok = len(a) >= cfg['min_n'] and len(b) >= cfg['min_n']
    rt = [r['rel_api'] for r, v in allv if v]
    rf = [r['rel_api'] for r, v in allv if not v]
    return {
        'feature': name, 'label': label, 'kind': 'bool' if category is None else 'cat', 'category': category,
        'basis': _basis(elig, status_col, status_filter),
        'n_top': len(a), 'n_bottom': len(b), 'n_all': len(allv),
        'top_value': _r(sum(a) / len(a)) if a else None, 'bottom_value': _r(sum(b) / len(b)) if b else None,
        'effect': _r(sum(a) / len(a) - sum(b) / len(b)) if ok else None,
        'p': round(perm_test(a, b, diff_mean, cfg['permutations'], cfg['seed']), 4) if ok and (sum(a) + sum(b)) else (1.0 if ok else None),
        'rel_true': _r(median(rt)), 'n_true': len(rt), 'rel_false': _r(median(rf)), 'n_false': len(rf),
    }


def _verdict(r, cfg):
    if r['p'] is None:
        return '判断保留（件数不足）'
    thr = cfg['effect_threshold_numeric'] if r['kind'] == 'num' else cfg['effect_threshold_share']
    if r['q'] is not None and r['q'] <= cfg['q_threshold'] and r['effect'] is not None and abs(r['effect']) >= thr:
        return '差あり（傾向）'
    return 'はっきりした差なし'


def _r(x, nd=4):
    return None if x is None else round(x, nd)
