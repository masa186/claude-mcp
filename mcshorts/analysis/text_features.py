"""冒頭ナレーションの特徴と、既存の実測・数値（決まった規則で取り出すだけ）。

出どころと状態：
  Dream  nw_  Whisper の冒頭5秒（dream_asr_edges, ok）。聞き間違いはあり得る
         nc_  ユーザー提供CSVの声の文（dream_tn58, UNVERIFIED）
         m_   個別分析・実測の数値（dream_coded_rows / dream_measure, ok）
         c_   ユーザー提供CSVの分類（dream_tn58, UNVERIFIED）
  SMP    nc_  ユーザー提供CSVの冒頭ナレーション（smp_tn299, UNVERIFIED）
         SMP の全編ナレーション・字幕・実測は確認済みのものが無いので、特徴を作らない（None のまま）
smp_open（Gemini・冒頭8秒）は、再生数の上位・下位から選んだ55本だけなので、偏りを避けるため使わない。
"""
import re

from .title_features import text_flags

JA = re.compile(r'[぀-ヿ一-鿿]')
JA_CHARS = re.compile(r'[぀-ヿ一-鿿ー]')

DREAM_CODED_NUMERIC = ('hook_sec', 'narr_start_sec', 'narr_lines', 'narr_chars_per_sec', 'cuts',
                       'shot_mean_sec', 'cuts_first3s', 'sub_changes', 'sub_on_ratio', 'music_mean',
                       'music_ge05_ratio', 'bgm_drops')
DREAM_MEASURE_NUMERIC = ('shot_median', 'motion_median', 'n_subs')
DREAM_CSV_CATEGORIES = ('hook', 'ptype', 'redtype', 'colp')


def _num(v):
    if v is None or v == '':
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def narration_flags(text, tn, prefix, status, source):
    if not text:
        return {f'{prefix}status': None}
    t = tn.clean(text) if hasattr(tn, 'clean') else text
    f = {
        f'{prefix}status': status,
        f'{prefix}source': source,
        f'{prefix}text': text,
        f'{prefix}ja_chars': len(JA_CHARS.findall(text)),
        f'{prefix}ending': tn.ending(t) if t else None,
        f'{prefix}watch': bool(tn.watch(t)),
        f'{prefix}prohibit': bool(re.search(r'てはいけません|ないで(ください)?', t)),
        f'{prefix}result_report': bool(re.search(r'(ました|でした|なりました|ことになります|こうなります)', t)),
    }
    f.update(text_flags(t, tn, prefix))
    return f


def dream_features(rec, tn):
    f = {}
    # Whisper 冒頭5秒（日本語指定）
    head = [t for t in rec['transcripts'] if t['source'] == 'dream_asr_edges' and t.get('scope') == 'head_5s']
    if head:
        segs = [s for s in head[0]['segments'] if s.get('text') and JA.search(s['text'])]
        text = ''.join(s['text'] for s in segs)
        f.update(narration_flags(text, tn, 'nw_', head[0]['status'], 'dream_asr_edges'))
    else:
        f['nw_status'] = None
    # ユーザー提供CSVの声の文
    csv = rec['features'].get('dream_tn58')
    voice = csv['fields'].get('voice') if csv else None
    f.update(narration_flags(voice, tn, 'nc_', csv['status'] if csv else None, 'dream_tn58'))
    # 個別分析・実測の数値（ok）
    coded = rec['features'].get('dream_coded_rows')
    for k in DREAM_CODED_NUMERIC:
        f[f'm_{k}'] = _num(coded['fields'].get(k)) if coded else None
    meas = rec['features'].get('dream_measure')
    for k in DREAM_MEASURE_NUMERIC:
        f[f'm_{k}'] = _num(meas['fields'].get(k)) if meas else None
    if meas and isinstance(meas['fields'].get('audio'), dict):
        f['m_audio_median_db'] = _num(meas['fields']['audio'].get('median_db'))
    else:
        f['m_audio_median_db'] = None
    # ユーザー提供CSVの分類（UNVERIFIED）
    for k in DREAM_CSV_CATEGORIES:
        f[f'c_{k}'] = (csv['fields'].get(k) or None) if csv else None
    f['c_status'] = csv['status'] if csv else None
    return f


def smp_features(rec, tn):
    f = {}
    csv = rec['features'].get('smp_tn299')
    text = csv['fields'].get('narration') if csv else None
    if text in ('未確認', '不明'):
        text = None
    f.update(narration_flags(text, tn, 'nc_', csv['status'] if csv else None, 'smp_tn299'))
    return f
