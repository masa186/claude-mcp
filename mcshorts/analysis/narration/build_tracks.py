"""段階4c-1：Dream のナレーションの元データを、動画ごとに1つのファイルに整える（Dream だけ）。

    mcshorts/.venv/bin/python mcshorts/analysis/narration/build_tracks.py

出力：mcshorts/analysis/narration/tracks/dream/<video_id>.json と discrepancies.md、manifest.json
- 字幕（narration_list.md、文単位の時刻）と Whisper（単語単位の時刻）は別々に持つ。対応付けはしない
  （時間が重なっているかどうかだけを事実として記録する）
- 食い違い（字幕・Whisper・CSV）は消さずに並べる。どれが正しいかは決めない
- 元データは読むだけ
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from analysis.narration import nlp, sources as S  # noqa: E402

OUT = os.path.join(HERE, 'tracks', 'dream')


def _overlap(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1


def _bigram_sim(a, b):
    a, b = a.replace(' ', ''), b.replace(' ', '')
    A = {a[i:i + 2] for i in range(len(a) - 1)}
    B = {b[i:i + 2] for i in range(len(b) - 1)}
    return round(len(A & B) / len(A | B), 3) if A and B else 0.0


def _norm(t):
    import re
    return re.sub(r'[\s、。,.!！?？…・「」]', '', t or '')


def build_video(vid, nl):
    whisper, raw = S.load_whisper(vid)
    rows = nl['rows']
    ja = []
    for i, s in enumerate(raw['ja']['segs']):
        seg = {'segment_index': i, 'start': s['start'], 'end': s['end'], 'text': s['text'],
               'category': S.classify_ja_segment(s['text']),
               'no_speech': s.get('no_speech'), 'logprob': s.get('logprob'),
               'words': [{'start': w[0], 'end': w[1], 'word': w[2]} for w in s.get('words', [])],
               'overlaps_doc_rows': [r['row_index'] for r in rows if _overlap(s['start'], s['end'], r['start'], r['end'])]}
        ja.append(seg)
    en = [{'segment_index': i, 'start': s['start'], 'end': s['end'], 'text': s['text'],
           'category': S.classify_ja_segment(s['text']) if s['text'].strip() else 'other'}
          for i, s in enumerate(raw['en']['segs'])]
    csv = S.load_csv_tn58(vid)
    ind = S.parse_individual(vid)
    meas = S.load_measure(vid)

    discrepancies = []
    for r in rows:
        over = [s for s in ja if r['row_index'] in s['overlaps_doc_rows']]
        joined = ''.join(s['text'].strip() for s in over)
        d = {'row_index': r['row_index'], 'start': r['start'], 'end': r['end'], 'doc_text': r['text'],
             'whisper_ja_overlapping_text': joined or None,
             'whisper_ja_overlapping_segments': [s['segment_index'] for s in over],
             'bigram_similarity_doc_vs_whisper_ja': _bigram_sim(r['text'], joined) if joined else None,
             'doc_text_in_csv_voice': (_norm(r['text']) in _norm(csv['voice'])) if csv and csv.get('voice') else None,
             'doc_text_in_csv_sub': (_norm(r['text']) in _norm(csv['sub'])) if csv and csv.get('sub') else None}
        discrepancies.append(d)

    track = {
        'channel': 'dream', 'video_id': vid, 'no': nl['no'],
        'duration_sec': meas.get('dur'),
        'doc_narration': {'status': 'DOC_OBSERVED', 'source': S.NARRATION_LIST,
                          'time_unit': '字幕の区間（文単位）', 'rows': rows, 'notes': nl['notes']},
        'whisper_ja': {'status': 'ok', 'source': f'dream/data/asr/{vid}.json',
                       'time_unit': '単語単位（words）と区間', 'note': '聞き間違いはそのまま。直していない',
                       'segments': ja},
        'whisper_en': {'status': 'ok', 'source': f'dream/data/asr/{vid}.json', 'time_unit': '区間',
                       'segments': en},
        'csv_tn58': csv,
        'doc_individual': {'source': ind['file'],
                           'opening_frames': {'status': 'DOC_OBSERVED', 'rows': ind['opening_frames']},
                           'structure': {'rows': ind['structure'],
                                         'note': '「段階」は過去の分析の考察（DOC_INTERPRETATION）、「内容」は [画面] の観察（DOC_OBSERVED）'},
                           'fact_lines': {'status': 'DOC_OBSERVED', 'lines': ind['fact_lines']},
                           'interpretation_lines': {'status': 'DOC_INTERPRETATION', 'lines': ind['interpretation_lines'],
                                                    'note': '[考察] の行。事実としては使わない'},
                           'gemini_lines_excluded': ind['gemini_lines_excluded']},
        'measured': {'status': 'ok', 'source': f'{S.MEASURE}/{vid}.json', **meas},
        'audiotag': {'status': 'ok', 'source': f'{S.AUDIOTAG}/{vid}.json',
                     'note': '確率による自動判定（0〜1）。2秒の窓を1秒ずつずらしたもの', **S.load_audiotag(vid)},
        'codes_4b': {'status': 'UNVERIFIED', 'source': f'{S.CODINGS_4B}/claude_v1.jsonl',
                     'note': 'review があるものは確認済みの結果。effective_code は修正を重ねた分類（元の分類は code に残す）',
                     'codes': S.load_codes_4b(vid)},
        'discrepancies': discrepancies,
    }
    return track


def _sha(rel):
    with open(S.p(rel), 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def build(out_dir=OUT):
    nl_all = S.parse_narration_list()
    os.makedirs(out_dir, exist_ok=True)
    tracks = {}
    for vid in sorted(nl_all):
        t = build_video(vid, nl_all[vid])
        with open(os.path.join(out_dir, f'{vid}.json'), 'w', encoding='utf-8') as f:
            json.dump(t, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write('\n')
        tracks[vid] = t
    write_discrepancies(os.path.join(out_dir, 'discrepancies.md'), tracks)
    inputs = [S.NARRATION_LIST, S.VIDEOS, S.DATA_FEATURES, f'{S.CODINGS_4B}/claude_v1.jsonl',
              f'{S.CODINGS_4B}/review_sample.csv']
    manifest = {'channel': 'dream', 'n_videos': len(tracks), 'tool': nlp.tagger_info(),
                'inputs_sha256': {r: _sha(r) for r in inputs}}
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')
    return tracks


def write_discrepancies(path, tracks):
    L = ['# Dream：ナレーションの字幕・Whisper・CSV の違い（消さずに並べたもの）', '',
         '`build_tracks.py` が自動で作る。どれが正しいかは決めていない。本文の基準は `dream/narration_list.md` の字幕（DOC_OBSERVED）。',
         'Whisper 日本語は「字幕の区間と時間が重なる区間」を並べただけで、対応付けはしていない。似かた＝文字2つ組の重なり（0〜1）。', '',
         '| 動画ID | 行 | 秒（字幕） | 字幕 | Whisper 日本語（時間が重なる区間） | 似かた | CSVの声に含まれる |',
         '|---|---|---|---|---|---|---|']
    for vid, t in sorted(tracks.items()):
        for d in t['discrepancies']:
            w = (d['whisper_ja_overlapping_text'] or '（重なる区間なし）').replace('|', '｜')
            sim = '—' if d['bigram_similarity_doc_vs_whisper_ja'] is None else f"{d['bigram_similarity_doc_vs_whisper_ja']:.2f}"
            inc = {True: 'はい', False: 'いいえ', None: '—'}[d['doc_text_in_csv_voice']]
            L.append(f"| `{vid}` | {d['row_index']} | {d['start']}〜{d['end']} | {d['doc_text'].replace('|', '｜')} | {w[:80]} | {sim} | {inc} |")
        for n in t['doc_narration']['notes']:
            L.append(f'| `{vid}` | 注記 | — | {n} | — | — | — |')
    L.append('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    ts = build()
    print('tracks', len(ts))
