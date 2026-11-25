"""段階4c-2：Dream の動画ごとのナレーション個別分析（10項目）。

    mcshorts/.venv/bin/python mcshorts/analysis/narration/per_video.py

出力：mcshorts/analysis/narration/per_video/dream/<video_id>.json と <video_id>.md、summary.md
決まりごと
- 字幕（narration_list.md）の文単位の時刻と、Whisper の単語単位の時刻は別々に計算する。対応付けない
- 盛り上がり・クライマックスは「実測値（measured）」と「規則による候補（interpretation・断定しない）」に分ける
- 確かさ（ok / DOC_OBSERVED / DOC_INTERPRETATION / UNVERIFIED）を値ごとに付ける
- 分析できない項目は理由とともに unavailable に書く。推測で埋めない
"""
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from analysis.common import load_tn_feat  # noqa: E402
from analysis.narration import nlp, roles as RL  # noqa: E402

OUT = os.path.join(HERE, 'per_video', 'dream')
WINDOWS = (1.0, 3.0, 5.0)
GAP_REPORT = 0.30          # これ以上の単語の間を「間」として数える（秒）
EXCITE_LABELS = ('Screaming', 'Shout', 'Yell', 'Explosion', 'Boom', 'Laughter', 'Cheering', 'Gasp')
EXCITE_THRESHOLD = 0.30
CANDIDATE_RULE = (f'音量の急な変化（実測の spikes）がある秒、または音タグの {"・".join(EXCITE_LABELS)} の'
                  f'いずれかが {EXCITE_THRESHOLD} 以上の秒を「盛り上がりの候補」とする（規則による候補。断定しない）')


def _r(x, n=3):
    return None if x is None else round(x, n)


def _med(xs):
    xs = sorted(xs)
    if not xs:
        return None
    k = len(xs)
    return xs[k // 2] if k % 2 else (xs[k // 2 - 1] + xs[k // 2]) / 2


def _nearest(t, events):
    return min((abs(t - e) for e in events), default=None)


def analyze(track, parts, links, tn):
    vid = track['video_id']
    dur = track['duration_sec']
    rows = track['doc_narration']['rows']
    my_parts = sorted([p for p in parts if p['video_id'] == vid], key=lambda p: (p['row'], p['part']))
    my_links = [x for x in links if x['video_id'] == vid]
    ja = track['whisper_ja']['segments']
    en = track['whisper_en']['segments']
    meas = track['measured']
    tags = track['audiotag']['rows']
    codes = track['codes_4b']['codes']
    unavailable = []      # データが無くて分析できなかったもの
    not_applicable = []   # 分析はしたが、その特徴が無かったもの（分析結果）

    # ---- 2・6：単語と文の印（字幕の部分ごと）
    part_feats = []
    for p in my_parts:
        toks = nlp.tokens(p['quote'])
        part_feats.append({
            'row': p['row'], 'part': p['part'], 'text': p['quote'], 'status': 'DOC_OBSERVED',
            'chars': nlp.ja_len(p['quote']),
            'pos_counts': nlp.pos_counts(toks),
            'content_lemmas': [t['lemma'] for t in toks if t['pos1'] in ('名詞', '動詞', '形容詞', '副詞', '代名詞')],
            'first_token': {k: toks[0][k] for k in ('surface', 'pos1', 'pos2', 'lemma')} if toks else None,
            'flags': nlp.flags(p['quote'], toks, tn),
        })
    all_lemmas = Counter(l for f in part_feats for l in f['content_lemmas'])

    # ---- 1・7：役割と順番・伏線（Claude の分類・UNVERIFIED）
    roles = [{'row': p['row'], 'part': p['part'], 'role': p['role'], 'label': p['role_label'], 'also': p['also'],
              'reason': p['reason'], 'flag': p['flag'], 'status': 'UNVERIFIED'} for p in my_parts]
    order = [p['role'] for p in my_parts]
    if not my_links:
        not_applicable.append({'item': 7, 'what': '伏線', 'reason': '予告（結果・ひねり・再フック）の部分が無い'})

    # ---- 3：0〜1・0〜3・0〜5秒の言葉（字幕と Whisper を別々に）
    windows = {}
    words = [w | {'segment_index': s['segment_index'], 'category': s['category']}
             for s in ja for w in s['words']]
    for W in WINDOWS:
        drows = [{'row': r['row_index'], 'start': r['start'], 'end': r['end'], 'text': r['text'],
                  'fully_inside': r['end'] <= W} for r in rows if r['start'] < W]
        ws = [w for w in words if w['start'] < W]
        windows[f'0-{int(W)}s'] = {
            'doc_subtitle': {'status': 'DOC_OBSERVED', 'rows_starting_in_window': drows,
                             'note': '行の区間が窓をまたぐ場合、窓の中の文字数は推測しない（fully_inside=false）'},
            'whisper_ja_words': {'status': 'ok', 'words': [w['word'] for w in ws],
                                 'text': ''.join(w['word'] for w in ws), 'chars': nlp.ja_len(''.join(w['word'] for w in ws)),
                                 'categories': sorted({w['category'] for w in ws}),
                                 'note': 'Whisper 日本語指定の単語のうち、開始が窓の中のもの。聞き間違いはそのまま'},
        }
    first_word = min(words, key=lambda w: w['start']) if words else None
    if not words:
        unavailable.append({'item': 3, 'what': 'Whisper の単語の時刻', 'reason': 'Whisper 日本語指定に単語が無い'})

    # ---- 4：冒頭のフックにつながる表現
    first_row = rows[0]
    fp = [f for f in part_feats if f['row'] == 0]
    opening_frames = [r for r in track['doc_individual']['opening_frames']['rows'] if r['start'] is not None and r['start'] <= 1.0]
    hook = {
        'first_doc_row': {'start': first_row['start'], 'end': first_row['end'], 'text': first_row['text'],
                          'chars': nlp.ja_len(first_row['text']), 'status': 'DOC_OBSERVED'},
        'first_parts': [{'text': f['text'], 'first_token': f['first_token'], 'flags': f['flags']} for f in fp],
        'first_roles': [r for r in roles if r['row'] == 0],
        'whisper_first_word': ({'word': first_word['word'], 'start': first_word['start'], 'category': first_word['category'],
                                'status': 'ok'} if first_word else None),
        'opening_frames_0_1s': {'status': 'DOC_OBSERVED', 'rows': opening_frames},
        'hook_code_4b': codes.get('hook'),
    }

    # ---- 5：文字数・文の長さ・話速・間
    row_stats = []
    for i, r in enumerate(rows):
        d = r['end'] - r['start']
        ch = nlp.ja_len(r['text'])
        row_stats.append({'row': r['row_index'], 'chars': ch, 'duration': _r(d, 2),
                          'chars_per_sec': _r(ch / d, 2) if d > 0 else None,
                          'gap_to_next_row': _r(rows[i + 1]['start'] - r['end'], 2) if i + 1 < len(rows) else None})
    nw = [w for s in ja if s['overlaps_doc_rows'] for w in s['words']]
    gaps = []
    for s in ja:
        if not s['overlaps_doc_rows']:
            continue
        ws = s['words']
        gaps += [b['start'] - a['end'] for a, b in zip(ws, ws[1:]) if b['start'] - a['end'] > 0]
    whisper_rate = None
    if nw:
        span = max(w['end'] for w in nw) - min(w['start'] for w in nw)
        whisper_rate = _r(nlp.ja_len(''.join(w['word'] for w in nw)) / span, 2) if span > 0 else None
    else:
        unavailable.append({'item': 5, 'what': 'Whisper による話速・間',
                            'reason': '字幕の区間と時間が重なる Whisper 日本語の区間が無い'})
    speed = {
        'doc_rows': {'status': 'DOC_OBSERVED', 'rows': row_stats,
                     'total_chars': sum(x['chars'] for x in row_stats),
                     'median_chars_per_sec': _r(_med([x['chars_per_sec'] for x in row_stats if x['chars_per_sec']]), 2)},
        'whisper_overlapping_doc_rows': {'status': 'ok', 'chars_per_sec': whisper_rate,
                                         'n_words': len(nw), 'word_gaps_positive': len(gaps),
                                         'gap_median': _r(_med(gaps), 3), 'gap_max': _r(max(gaps), 3) if gaps else None,
                                         f'gaps_ge_{GAP_REPORT}s': sum(g >= GAP_REPORT for g in gaps),
                                         'note': '字幕の行と時間が重なる Whisper 日本語の区間の単語だけ。対応付けではない'},
    }

    # ---- 8：展開・盛り上がり・クライマックス・オチ
    cuts = meas.get('cuts') or []
    bins = {}
    for c in cuts:
        b = int(c // 5) * 5
        bins[b] = bins.get(b, 0) + 1
    spikes = [s if isinstance(s, (int, float)) else s.get('t') if isinstance(s, dict) else s[0]
              for s in (meas.get('audio') or {}).get('spikes') or []]
    spikes = [s for s in spikes if s is not None]
    excite = [{'t': r['t'], **{k: r[k] for k in EXCITE_LABELS if r.get(k) is not None and r[k] >= EXCITE_THRESHOLD}}
              for r in tags if any((r.get(k) or 0) >= EXCITE_THRESHOLD for k in EXCITE_LABELS)]
    cand_secs = sorted({int(s) for s in spikes} | {e['t'] for e in excite})
    narration_pos = [{'row': r['row_index'], 'start': r['start'], 'position': (
        'opening' if r['start'] < 10 else 'end' if dur and r['end'] >= dur - 10 else 'middle')} for r in rows]
    development = {
        'narration_positions': {'status': 'DOC_OBSERVED', 'rows': narration_pos,
                                'note': 'opening＝10秒より前、end＝最後の10秒、それ以外＝middle'},
        'measured': {'status': 'ok', 'duration_sec': dur, 'cuts': len(cuts),
                     'cuts_per_5s': {str(k): v for k, v in sorted(bins.items())},
                     'audio_spikes_sec': [_r(s, 2) for s in spikes],
                     'excitement_audiotag_ge_threshold': excite},
        'interpretation': {'status': 'INTERPRETATION', 'rule': CANDIDATE_RULE,
                           'candidate_seconds': cand_secs,
                           'note': '候補であってクライマックスとは断定しない。映像は見ていない'},
        'doc_structure': {'note': '「段階」は過去の分析の考察（DOC_INTERPRETATION）、「内容」は [画面] の観察（DOC_OBSERVED）',
                          'rows': [{k: s[k] for k in ('range_raw', 'stage_label', 'content')} for s in track['doc_individual']['structure']['rows']]},
        'codes_4b': {k: codes.get(k) for k in ('development', 'payoff')},
    }
    if not cand_secs:
        not_applicable.append({'item': 8, 'what': '盛り上がりの候補', 'reason': '規則に当てはまる秒が無い'})

    # ---- 9：最後の一言と締め方
    last = rows[-1]
    last_en = next((s for s in reversed(en) if s['text'].strip()), None)
    last_ja = next((s for s in reversed(ja) if s['category'] not in ('boilerplate_suspect', 'repetition_suspect') and s['text'].strip()), None)
    ending = {
        'last_doc_row': {'text': last['text'], 'start': last['start'], 'end': last['end'],
                         'sec_from_end': _r(dur - last['end'], 2) if dur else None,
                         'is_end_position': bool(dur and last['end'] >= dur - 10), 'status': 'DOC_OBSERVED'},
        'last_doc_row_roles': [r for r in roles if r['row'] == last['row_index']],
        'last_whisper_en': ({'text': last_en['text'], 'start': last_en['start'], 'status': 'ok'} if last_en else None),
        'last_whisper_ja_non_boilerplate': ({'text': last_ja['text'], 'start': last_ja['start'], 'category': last_ja['category'],
                                             'status': 'ok'} if last_ja else None),
        'payoff_code_4b': codes.get('payoff'),
    }
    if not (dur and last['end'] >= dur - 10):
        not_applicable.append({'item': 9, 'what': '締めのナレーション',
                               'reason': '最後の10秒にナレーションの行が無い（最後の行は締めのナレーションではない）'})

    # ---- 10：映像・字幕・効果音・BGM とのタイミング（実測と文書の観察だけ）
    subch = meas.get('sub_changes') or []
    rel = []
    for r in rows:
        secs = [t for t in tags if r['start'] - 0.5 <= t['t'] < r['end'] + 0.5]
        music = [t['Music'] for t in secs if t.get('Music') is not None]
        rel.append({'row': r['row_index'], 'start': r['start'], 'end': r['end'],
                    'nearest_cut_to_start': _r(_nearest(r['start'], cuts), 2),
                    'nearest_cut_to_end': _r(_nearest(r['end'], cuts), 2),
                    'nearest_subtitle_change_to_start': _r(_nearest(r['start'], subch), 2),
                    'nearest_subtitle_change_to_end': _r(_nearest(r['end'], subch), 2),
                    'music_mean_during_row': _r(sum(music) / len(music), 3) if music else None,
                    'spikes_within_row_or_1s_after': [_r(s, 2) for s in spikes if r['start'] <= s <= r['end'] + 1.0]})
    in_rows = {t['t'] for t in tags for r in rows if r['start'] - 0.5 <= t['t'] < r['end'] + 0.5}
    out_music = [t['Music'] for t in tags if t['t'] not in in_rows and t.get('Music') is not None]
    timing = {
        'status': 'ok（実測・音タグ）と DOC_OBSERVED（字幕の区間）の組み合わせ',
        'first_doc_row_start': first_row['start'], 'first_cut': cuts[0] if cuts else None,
        'first_cut_minus_first_row_start': _r(cuts[0] - first_row['start'], 2) if cuts else None,
        'audio_onset': (meas.get('audio') or {}).get('onset'),
        'rows': rel,
        'music_mean_outside_narration': _r(sum(out_music) / len(out_music), 3) if out_music else None,
        'opening_frames_0_3s': {'status': 'DOC_OBSERVED', 'rows': track['doc_individual']['opening_frames']['rows']},
        'note': '音タグは2秒の窓・1秒刻みなので、区間の前後0.5秒を含めて平均した。効果音の種類は音タグの判定（確率）',
    }

    return {
        'channel': 'dream', 'video_id': vid, 'no': track['no'], 'duration_sec': dur,
        'tool': nlp.tagger_info(),
        'sources': {'narration_text': 'dream/narration_list.md（DOC_OBSERVED・本文の基準）',
                    'whisper': track['whisper_ja']['source'] + '（ok・聞き間違いあり）',
                    'individual': track['doc_individual']['source'] + '（DOC_OBSERVED / DOC_INTERPRETATION）',
                    'roles': 'analysis/narration/codings/dream/roles_claude_v1.jsonl（UNVERIFIED）',
                    'codes_4b': track['codes_4b']['source'] + '（UNVERIFIED。確認済みのものは review 付き）'},
        'doc_notes': track['doc_narration']['notes'],
        'items': {
            '1_roles': {'status': 'UNVERIFIED', 'parts': roles},
            '2_words': {'status': 'DOC_OBSERVED（本文）・形態素解析', 'parts': part_feats,
                        'top_content_lemmas': all_lemmas.most_common(15)},
            '3_opening_windows': windows,
            '4_hook': hook,
            '5_length_speed_pause': speed,
            '6_sentence_flags': {'status': 'DOC_OBSERVED（本文）・規則', 'parts': [{'row': f['row'], 'part': f['part'], 'text': f['text'], **f['flags']} for f in part_feats]},
            '7_order_foreshadow': {'status': 'UNVERIFIED', 'role_sequence': order, 'links': my_links},
            '8_development': development,
            '9_ending': ending,
            '10_timing': timing,
        },
        'unavailable': unavailable,
        'not_applicable': not_applicable,
    }


# ------------------------------------------------------------------ 読める形（md）
def to_md(a):
    it = a['items']
    L = [f"# Dream #{a['no']:02d} `{a['video_id']}` ナレーション個別分析（{a['duration_sec']}秒）", '',
         '自動で作るファイル。確かさ：ok＝機械的な値、DOC_OBSERVED＝文書の観察、DOC_INTERPRETATION＝文書の考察、UNVERIFIED＝未確認（Claude の分類・CSV）、INTERPRETATION＝規則による候補（断定しない）。', '']
    if a['doc_notes']:
        L += ['**本文の注記（narration_list.md）**：' + ' ／ '.join(a['doc_notes']), '']
    L += ['## 1・7. 文の役割と順番（UNVERIFIED）', '', '| 秒（行） | 部分 | 役割 | 理由 |', '|---|---|---|---|']
    for r, f in zip(it['1_roles']['parts'], it['2_words']['parts']):
        L.append(f"| 行{r['row']} | {f['text']} | `{r['role']}` {r['label']}" + (f"（副：{' '.join(r['also'])}）" if r['also'] else '') + f" | {r['reason']} |")
    L += ['', '役割の並び：' + ' → '.join(it['7_order_foreshadow']['role_sequence']), '']
    for x in it['7_order_foreshadow']['links']:
        ev = ' ／ '.join(f"{e['source']}「{e['quote']}」" for e in x['evidence']) or '—'
        L.append(f"- 伏線 `{x['status']}`：「{x['from_quote']}」→ {ev}" + (f"（{x['note']}）" if x['note'] else ''))
    L += ['', '## 3. 冒頭0〜1・0〜3・0〜5秒の言葉', '', '| 窓 | 字幕（DOC_OBSERVED。区間が窓の中で始まる行） | Whisper 日本語の単語（ok） |', '|---|---|---|']
    for k, w in it['3_opening_windows'].items():
        d = ' ／ '.join(f"{x['text']}（{x['start']}〜{x['end']}{'' if x['fully_inside'] else '・窓をまたぐ'}）" for x in w['doc_subtitle']['rows_starting_in_window']) or '—'
        L.append(f"| {k} | {d} | {w['whisper_ja_words']['text'] or '—'}（{w['whisper_ja_words']['chars']}字） |")
    h = it['4_hook']
    L += ['', '## 4. フック', '', f"- 最初の行（{h['first_doc_row']['start']}〜{h['first_doc_row']['end']}秒、{h['first_doc_row']['chars']}字）：{h['first_doc_row']['text']}"]
    if h['whisper_first_word']:
        L.append(f"- Whisper の最初の単語：「{h['whisper_first_word']['word']}」{h['whisper_first_word']['start']}秒（{h['whisper_first_word']['category']}）")
    hc = h['hook_code_4b'] or {}
    L.append(f"- 段階4bのフックの分類：`{hc.get('code')}`" + (f"（確認：{hc['review']['result']}、修正後 `{hc.get('effective_code')}`）" if hc.get('review') else '（未確認）'))
    for r in h['opening_frames_0_1s']['rows']:
        L.append(f"- 0〜1秒の画（DOC_OBSERVED）{r['time_raw']}：{r['visual']} ／ 字幕 {r['subtitle']}")
    s = it['5_length_speed_pause']
    L += ['', '## 5. 文字数・話速・間', '', f"- 字幕：合計 {s['doc_rows']['total_chars']}字、行ごとの話速の中央値 {s['doc_rows']['median_chars_per_sec']}字/秒（DOC_OBSERVED の区間から）",
          f"- Whisper（字幕と時間が重なる区間）：{s['whisper_overlapping_doc_rows']['chars_per_sec']}字/秒、単語の間 中央値 {s['whisper_overlapping_doc_rows']['gap_median']}秒・最大 {s['whisper_overlapping_doc_rows']['gap_max']}秒"]
    L += ['', '## 6. 文の印', '', '| 部分 | 文末の型 | 疑問 | 断定 | 逆接 | 数字 | 伏せ字 | 感情語 | 強調語 |', '|---|---|---|---|---|---|---|---|---|']
    for f in it['6_sentence_flags']['parts']:
        yn = lambda b: '○' if b else ''
        L.append(f"| {f['text']} | {f['ending_type']} | {yn(f['question'])} | {yn(f['assertion'])} | {yn(f['adversative'])} | {yn(f['number'])} | {yn(f['fuseji'])} | {'・'.join(f['emotion_words'])} | {'・'.join(f['emphasis_words'])} |")
    d = it['8_development']
    L += ['', '## 8. 展開・盛り上がり', '', f"- 実測（ok）：カット {d['measured']['cuts']}回、5秒ごとのカット {d['measured']['cuts_per_5s']}、音量の急な変化 {d['measured']['audio_spikes_sec']}",
          f"- 規則による候補（INTERPRETATION・断定しない）：{d['interpretation']['candidate_seconds']}秒",
          f"- 段階4bの分類：展開 `{(d['codes_4b']['development'] or {}).get('effective_code')}`、オチ `{(d['codes_4b']['payoff'] or {}).get('effective_code')}`（UNVERIFIED。確認済みは修正後）"]
    e = it['9_ending']
    L += ['', '## 9. 最後の一言', '', f"- 最後のナレーションの行：「{e['last_doc_row']['text']}」（終わりまで {e['last_doc_row']['sec_from_end']}秒）",
          f"- 最後の英語の台詞（Whisper）：{(e['last_whisper_en'] or {}).get('text')}"]
    t = it['10_timing']
    L += ['', '## 10. タイミング', '', f"- 最初の行の開始 {t['first_doc_row_start']}秒、最初のカット {t['first_cut']}秒（差 {t['first_cut_minus_first_row_start']}秒）、音の立ち上がり {t['audio_onset']}秒",
          f"- ナレーション外の BGM（Music）の平均 {t['music_mean_outside_narration']}", '',
          '| 行 | 秒 | 最寄りのカット（始/終） | 最寄りの字幕の切り替え（始/終） | 行の間の Music | 行中〜1秒後の音量の急な変化 |', '|---|---|---|---|---|---|']
    for r in t['rows']:
        L.append(f"| {r['row']} | {r['start']}〜{r['end']} | {r['nearest_cut_to_start']} / {r['nearest_cut_to_end']} | {r['nearest_subtitle_change_to_start']} / {r['nearest_subtitle_change_to_end']} | {r['music_mean_during_row']} | {r['spikes_within_row_or_1s_after']} |")
    L += ['', '## 分析できなかった項目（データなし）', '']
    L += [f"- 項目{u['item']} {u['what']}：{u['reason']}" for u in a['unavailable']] or ['なし']
    L += ['', '## 該当なし（分析はしたが、その特徴が無かった）', '']
    L += [f"- 項目{u['item']} {u['what']}：{u['reason']}" for u in a['not_applicable']] or ['なし']
    L.append('')
    return '\n'.join(L)


def build(out_dir=OUT, tracks_dir=RL.TRACKS):
    tn = load_tn_feat()
    tracks = RL.load_tracks(tracks_dir)
    with open(os.path.join(RL.CODINGS, 'roles_claude_v1.json'), encoding='utf-8') as f:
        decisions = json.load(f)
    parts, links = RL.build_records(tracks, decisions, RL.load_codebook())
    os.makedirs(out_dir, exist_ok=True)
    res = {}
    for vid, t in sorted(tracks.items()):
        a = analyze(t, parts, links, tn)
        with open(os.path.join(out_dir, f'{vid}.json'), 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write('\n')
        with open(os.path.join(out_dir, f'{vid}.md'), 'w', encoding='utf-8') as f:
            f.write(to_md(a))
        res[vid] = a
    write_summary(os.path.join(out_dir, 'summary.md'), res)
    return res


def write_summary(path, res):
    un = Counter((u['item'], u['what']) for a in res.values() for u in a['unavailable'])
    na = Counter((u['item'], u['what']) for a in res.values() for u in a['not_applicable'])
    tool = next(iter(res.values()))['tool']
    L = ['# Dream ナレーション個別分析（58本）の一覧', '',
         f"形態素解析：fugashi {tool['fugashi']}・unidic-lite {tool['unidic_lite']}（辞書 {tool['dictionary_info'][0]['filename']}、version {tool['dictionary_info'][0]['version']}）・語の一覧 {tool['lexicon_version']}", '',
         f'処理した動画：{len(res)}本', '', '## 分析できなかった項目（データなし・本数）', '', '| 項目 | 内容 | 本数 |', '|---|---|---|']
    for (i, w), n in sorted(un.items()):
        L.append(f'| {i} | {w} | {n} |')
    if not un:
        L.append('| — | なし | 0 |')
    L += ['', '## 該当なし（分析はしたが、その特徴が無かった本数）', '', '| 項目 | 内容 | 本数 |', '|---|---|---|']
    for (i, w), n in sorted(na.items()):
        L.append(f'| {i} | {w} | {n} |')
    L += ['', '## 動画ごと', '', '| # | 動画ID | 最初の行 | 役割の並び | 最初の行の話速（字/秒） |', '|---|---|---|---|---|']
    for vid, a in sorted(res.items(), key=lambda x: x[1]['no']):
        rs = a['items']['5_length_speed_pause']['doc_rows']['rows'][0]
        L.append(f"| {a['no']:02d} | [`{vid}`]({vid}.md) | {a['items']['4_hook']['first_doc_row']['text']} | {' → '.join(a['items']['7_order_foreshadow']['role_sequence'])} | {rs['chars_per_sec']} |")
    L.append('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    r = build()
    print('per_video', len(r))
