"""SMP Clips（SMPクリップ）の既存データを読む。既存ファイルには書き込まない。"""
import os

from .common import load_json

CH = 'smp'


def _api_list(root, sources, coll, sid):
    s = sources[sid]
    data = load_json(os.path.join(root, s['path']))[s['key']]
    for v in data['vs']:
        coll.video_obs(CH, v['id'], sid, title=v.get('title'), published=v.get('at'),
                       duration_sec=v.get('sec'), views=v.get('views'), likes=v.get('likes'),
                       comments=v.get('comments'))
        coll.mark(CH, v['id'], 'list_api', 'ok', sid)
    return {v['id']: v for v in data['vs']}


def load(root, sources, coll):
    p = lambda rel: os.path.join(root, rel)

    # ---- 一覧（YouTube API、2回分）
    older = _api_list(root, sources, coll, 'smp_api_0830')
    latest = _api_list(root, sources, coll, 'smp_api_1124')
    only_old = sorted(set(older) - set(latest))
    for vid in only_old:
        coll.set_extra(CH, vid, 'list_membership', 'smp_api_0830 にあり smp_api_1124 に無い（理由は記録なし）')
    coll.list_diffs.append({
        'channel': CH, 'what': 'smp_api_0830 にあり smp_api_1124 に無い動画',
        'count': len(only_old), 'video_ids': only_old,
        'note': '削除・非公開などの理由は記録が無いので書かない。段階2の取り直しで状態を確かめる',
    })

    # ---- 上位・下位を選んだ一覧（smp_api_1124 から作ったもの）
    for sid in ('smp_top40', 'smp_topbottom'):
        for r in load_json(p(sources[sid]['path'])):
            vid = r['id']
            base = latest.get(vid)
            if base is None:
                coll.anomaly('subset_not_in_parent', source=sid, video_id=vid)
            elif base.get('views') != r.get('views'):
                # 元の一覧と違う値なら、別の観測として残す（勝手にどちらかに決めない）
                coll.video_obs(CH, vid, sid, views=r.get('views'), likes=r.get('likes'),
                               comments=r.get('comments'))
                coll.anomaly('subset_views_differ', source=sid, video_id=vid)
            fields = {k: r[k] for k in ('group', 'rank', 'top_title') if k in r}
            coll.add_feature(CH, vid, sid, fields, 'ok')
            if r.get('top_title'):
                coll.mark(CH, vid, 'top_title', 'ok', sid, 'コマから読んだもの')

    # ---- ユーザー提供CSV由来（299本）
    for r in load_json(p(sources['smp_tn299']['path'])):
        vid = r['id']
        fields = {k: v for k, v in r.items() if k not in ('id', 'views', 'title', 'at', 'dur')}
        coll.add_feature(CH, vid, 'smp_tn299', fields, 'UNVERIFIED')
        if r.get('narration'):
            coll.add_transcript(CH, vid, {
                'source': 'smp_tn299', 'method': 'user_csv' if r.get('src') == 'csv' else r.get('src'),
                'kind': 'narration_text', 'scope': 'opening_narration', 'lang': 'ja',
                'status': 'UNVERIFIED',
                'segments': [{'start': None, 'end': None, 'text': r['narration']}],
                'raw': {'sec': r.get('sec'), 'src': r.get('src')},
                'missing': {'timestamps': {'code': 'NOT_COLLECTED',
                                           'note': '区間ごとの秒が無い。raw.sec の意味は記録なし'}},
            })
            coll.mark(CH, vid, 'narration_text', 'UNVERIFIED', 'smp_tn299')
        if r.get('top'):
            coll.mark(CH, vid, 'top_title', 'UNVERIFIED', 'smp_tn299')

    # ---- Gemini：冒頭8秒（未確認）
    for vid, d in sorted(load_json(p(sources['smp_open']['path'])).items()):
        coll.add_transcript(CH, vid, {
            'source': 'smp_open', 'method': 'gemini', 'tool': d.get('_model'), 'kind': 'narration_subtitle',
            'scope': 'opening_8s', 'lang': 'ja', 'status': 'UNVERIFIED',
            'segments': [{'start': x.get('t'), 'end': None, 'text': x.get('text'), 'color': x.get('color')}
                         for x in d.get('narration_lines', [])],
            'missing': {'end': {'code': 'NOT_COLLECTED', 'note': '終了秒は答えさせていない'}},
        })
        coll.add_feature(CH, vid, 'smp_open',
                         {k: v for k, v in d.items() if k != 'narration_lines'}, 'UNVERIFIED')
        coll.mark(CH, vid, 'transcript_opening', 'UNVERIFIED', 'smp_open')
        if d.get('top_title'):
            coll.mark(CH, vid, 'top_title', 'UNVERIFIED', 'smp_open')

    # ---- Gemini：全編（不採用。照合用に残すだけ）
    for vid, d in sorted(load_json(p(sources['smp_full']['path'])).items()):
        segs = [{'start': x.get('t'), 'end': None, 'text': x.get('text'), 'track': 'voice'}
                for x in d.get('narration_voice_lines', [])]
        segs += [{'start': x.get('t'), 'end': None, 'text': x.get('text'), 'track': 'subtitle'}
                 for x in d.get('narration_subtitles', [])]
        coll.add_transcript(CH, vid, {
            'source': 'smp_full', 'method': 'gemini', 'tool': d.get('_model'), 'kind': 'narration',
            'scope': 'full', 'lang': 'ja', 'status': 'REJECTED', 'segments': segs,
            'note': sources['smp_full']['note'],
        })
        coll.mark(CH, vid, 'transcript_full', 'REJECTED', 'smp_full')

    for vid, d in sorted(load_json(p(sources['smp_voice']['path'])).items()):
        segs = [{'start': x.get('t'), 'end': x.get('end'), 'text': x.get('text'), 'track': 'japanese_voice'}
                for x in d.get('japanese_voice', [])]
        segs += [{'start': x.get('t'), 'end': None, 'text': x.get('text'), 'track': 'subtitle',
                  'color': x.get('color')} for x in d.get('subtitles', [])]
        coll.add_transcript(CH, vid, {
            'source': 'smp_voice', 'method': 'gemini', 'tool': d.get('_model'), 'kind': 'voice+subtitle',
            'scope': 'full', 'lang': 'ja', 'status': 'REJECTED', 'segments': segs,
            'note': sources['smp_voice']['note'],
        })
        coll.mark(CH, vid, 'transcript_full', 'REJECTED', 'smp_voice')

    # ---- チャンネル全体の欠損（記録が無いものの理由）
    coll.set_channel_missing(CH, 'media_file', 'NO_MEDIA',
                             '過去に一部の実ファイルを読んだ記録（docs/smp_real.md など）はあるが、ファイルはリポジトリに無い')
    coll.set_channel_missing(CH, 'measure', 'NOT_COLLECTED', 'SMP の実測データは構造化されていない（文書のみ）。動画ファイルが必要')
    coll.set_channel_missing(CH, 'audiotag', 'NOT_COLLECTED', '動画ファイルが必要')
    coll.set_channel_missing(CH, 'gemini_av', 'NOT_COLLECTED', None)
    coll.set_channel_missing(CH, 'coded_features', 'NOT_COLLECTED',
                             'Dream のような1本ずつの構成分類は SMP では作られていない（smp_tn299 の分類は narration_text 側）')
    coll.set_channel_missing(CH, 'narration_text', 'NOT_COLLECTED',
                             'tn_smp299 に含まれない（元CSVの「未確認」「欠番」行、または一覧外。1本ずつの理由は記録なし）')
