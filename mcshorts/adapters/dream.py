"""Dream Clips（ドリームクリップ）の既存データを読む。既存ファイルには書き込まない。"""
import glob
import os

from .common import load_json

CH = 'dream'

# measure から features に写す数値（値はそのまま。解釈はしない）
MEASURE_KEYS = ('dur', 'fps', 'w', 'h', 'n_shots', 'shot_mean', 'shot_median', 'n_subs',
                'sub_on_ratio', 'motion_median', 'cuts_first3s', 'layout', 'audio')


def _segs(segs):
    """書き起こしの区間。単語ごとの時刻（words）は大きいので写さず、元ファイルを参照する。"""
    out = []
    for s in segs:
        seg = {'start': s.get('start'), 'end': s.get('end'), 'text': s.get('text')}
        for k in ('no_speech', 'logprob'):
            if k in s:
                seg[k] = s[k]
        out.append(seg)
    return out


def load(root, sources, coll):
    p = lambda rel: os.path.join(root, rel)

    # ---- 一覧（ユーザー提供）
    vids = load_json(p(sources['dream_videos']['path']))
    by_no = {}
    for r in vids:
        vid = r['id']
        by_no[r['no']] = vid
        coll.video_obs(CH, vid, 'dream_videos', title=r.get('title'), published=r.get('upload'),
                       duration_sec=r.get('duration'), views=r.get('views'))
        coll.set_extra(CH, vid, 'dream_no', r['no'])
        path = r.get('path')
        if path and os.path.exists(path):
            coll.mark(CH, vid, 'media_file', 'ok', 'dream_videos')
        else:
            coll.mark_missing(CH, vid, 'media_file', 'NO_MEDIA',
                              'videos.json の path（前のセッションの一時フォルダ）にファイルが無い')

    # ---- 一覧（YouTube API）
    s = sources['dream_api_five']
    ch_data = load_json(p(s['path']))[s['key']]
    for v in ch_data['vs']:
        coll.video_obs(CH, v['id'], 'dream_api_five', title=v.get('title'), published=v.get('at'),
                       duration_sec=v.get('sec'), views=v.get('views'), likes=v.get('likes'),
                       comments=v.get('comments'))
        coll.mark(CH, v['id'], 'list_api', 'ok', 'dream_api_five')

    known = set(by_no.values())

    # ---- 個別分析を数値にしたもの
    for r in load_json(p(sources['dream_coded_rows']['path'])):
        vid = r['id']
        fields = {k: v for k, v in r.items() if k not in ('id', 'views', 'title', 'upload', 'duration_sec')}
        coll.add_feature(CH, vid, 'dream_coded_rows', fields, 'ok')
        coll.mark(CH, vid, 'coded_features', 'ok', 'dream_coded_rows')
        if r.get('top_telop'):
            coll.mark(CH, vid, 'top_title', 'ok', 'dream_coded_rows', 'コマから読んだもの')

    # ---- ユーザー提供CSV由来（動画IDが無いので no で対応付け）
    for r in load_json(p(sources['dream_tn58']['path'])):
        vid = by_no.get(r.get('no'))
        if vid is None:
            coll.anomaly('dream_tn58_no_unmatched', no=r.get('no'))
            continue
        fields = {k: v for k, v in r.items() if k not in ('views', 'title', 'up', 'dur')}
        coll.add_feature(CH, vid, 'dream_tn58', fields, 'UNVERIFIED')
        for kind, key in (('narration_voice', 'voice'), ('subtitle_sequence', 'sub')):
            if r.get(key):
                coll.add_transcript(CH, vid, {
                    'source': 'dream_tn58', 'method': 'user_csv', 'kind': kind, 'scope': 'narration',
                    'lang': 'ja', 'status': 'UNVERIFIED',
                    'segments': [{'start': None, 'end': None, 'text': r[key]}],
                    'missing': {'timestamps': {'code': 'NOT_COLLECTED', 'note': 'CSV に区間ごとの秒が無い'}},
                })
        if r.get('voice') or r.get('sub'):
            coll.mark(CH, vid, 'narration_text', 'UNVERIFIED', 'dream_tn58')
        if r.get('top_lines'):
            coll.mark(CH, vid, 'top_title', 'UNVERIFIED', 'dream_tn58')

    # ---- Whisper（全編・日本語指定と英語指定）
    s = sources['dream_asr']
    for f in sorted(glob.glob(p(os.path.join(s['path'], '*.json')))):
        d = load_json(f)
        vid = d.get('id') or os.path.basename(f)[:-5]
        if vid not in known:
            coll.anomaly('dream_asr_unknown_id', file=os.path.relpath(f, root))
        for lang_key in ('ja', 'en'):
            part = d.get(lang_key)
            if not part:
                continue
            coll.add_transcript(CH, vid, {
                'source': 'dream_asr', 'method': 'whisper', 'tool': s['tool'], 'kind': 'speech',
                'scope': 'full', 'lang': lang_key, 'detected_lang': part.get('lang'),
                'status': 'ok', 'file': os.path.relpath(f, root),
                'segments': _segs(part.get('segs', [])),
                'note': '単語ごとの時刻は file に残っている',
            })
        coll.mark(CH, vid, 'transcript_full', 'ok', 'dream_asr')

    # ---- Whisper（冒頭5秒・最後7秒）
    s = sources['dream_asr_edges']
    for f in sorted(glob.glob(p(os.path.join(s['path'], '*.json')))):
        d = load_json(f)
        vid = d.get('id') or os.path.basename(f)[:-5]
        for part, scope in (('head', 'head_5s'), ('tail', 'tail_7s')):
            coll.add_transcript(CH, vid, {
                'source': 'dream_asr_edges', 'method': 'whisper', 'tool': s['tool'], 'kind': 'speech',
                'scope': scope, 'lang': 'ja', 'status': 'ok', 'file': os.path.relpath(f, root),
                'segments': _segs(d.get(part, [])),
            })
        coll.mark(CH, vid, 'transcript_opening', 'ok', 'dream_asr_edges')

    # ---- Gemini（14本だけ）
    s = sources['dream_gemini']
    got = set()
    for f in sorted(glob.glob(p(os.path.join(s['path'], '*.json')))):
        d = load_json(f)
        vid = os.path.basename(f)[:-5]
        got.add(vid)
        coll.add_transcript(CH, vid, {
            'source': 'dream_gemini', 'method': 'gemini', 'tool': d.get('_model'), 'kind': 'narration_subtitle',
            'scope': 'full', 'lang': 'ja', 'status': 'UNVERIFIED', 'file': os.path.relpath(f, root),
            'segments': [{'start': x.get('t'), 'end': None, 'text': x.get('text')}
                         for x in d.get('narration_lines', [])],
            'missing': {'end': {'code': 'NOT_COLLECTED', 'note': '終了秒は答えさせていない'}},
        })
        coll.add_feature(CH, vid, 'dream_gemini',
                         {k: v for k, v in d.items() if k != 'narration_lines'}, 'UNVERIFIED')
        coll.mark(CH, vid, 'gemini_av', 'UNVERIFIED', 'dream_gemini')
    for vid in known - got:
        coll.mark_missing(CH, vid, 'gemini_av', 'QUOTA_LIMIT', 'Gemini の無料枠の上限で取得できなかった（dream/README.md）')

    # ---- 実測
    s = sources['dream_measure']
    for f in sorted(glob.glob(p(os.path.join(s['path'], '*.json')))):
        d = load_json(f)
        vid = d.get('id') or os.path.basename(f)[:-5]
        fields = {k: d[k] for k in MEASURE_KEYS if k in d}
        fields['n_cuts'] = len(d.get('cuts', []))
        fields['file'] = os.path.relpath(f, root)
        coll.add_feature(CH, vid, 'dream_measure', fields, 'ok')
        coll.mark(CH, vid, 'measure', 'ok', 'dream_measure')

    # ---- 音タグ（中身は元ファイルを参照。ここでは有無と窓の設定だけ）
    s = sources['dream_audiotag']
    for f in sorted(glob.glob(p(os.path.join(s['path'], '*.json')))):
        d = load_json(f)
        vid = d.get('id') or os.path.basename(f)[:-5]
        coll.add_feature(CH, vid, 'dream_audiotag',
                         {'win': d.get('win'), 'hop': d.get('hop'), 'n_rows': len(d.get('rows', [])),
                          'file': os.path.relpath(f, root)}, 'ok')
        coll.mark(CH, vid, 'audiotag', 'ok', 'dream_audiotag')
