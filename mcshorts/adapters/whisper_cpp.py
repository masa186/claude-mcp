"""whisper.cpp の出力を imports/whisper_cpp/ から読む。

読める形式（whisper.cpp の出力オプション）：
  .json  -oj（区間）/ -ojf（区間＋トークン）
  .srt   -osrt
  .vtt   -ovtt
  .csv   -ocsv（start,end[,speaker],text。時刻はミリ秒）
  .lrc   -olrc
  .txt   -otxt（時刻なし）。ただし「[00:00:00.000 --> 00:00:02.000] 文」の行が並ぶ
         画面出力を保存したものは、時刻付きとして読む
  .log   画面出力を保存したもの

注意：これらの形式は whisper.cpp の公開仕様に合わせた自作サンプルでしか確かめていない。
実ファイルが届いたら tests/fixtures に加えて確かめ、README の「確認状況」を更新する。

動画との対応付け（推測はしない）：
  1. manifest.csv に書かれていればそれに従う
  2. 書かれていなければ、ファイル名に「既知の動画ID」がちょうど1つ含まれているときだけ対応付ける
  3. それ以外は UNMATCHED として一覧に出し、取り込まない
"""
import csv
import io
import json
import os
import re

from .common import CHANNELS, is_video_id, sha256_file

FORMATS = ('.json', '.srt', '.vtt', '.csv', '.lrc', '.txt', '.log')
SKIP_NAMES = {'README.md', 'manifest.csv', 'manifest.example.csv', '.gitkeep'}
MANIFEST_COLUMNS = ['file', 'video_id', 'channel', 'model', 'language', 'scope', 'run_date', 'note']

_TS = r'(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})'
_RANGE = re.compile(r'^\s*\[?\s*' + _TS + r'\s*-->\s*' + _TS + r'\s*\]?\s*(.*)$')
_LRC = re.compile(r'^\[(\d+):(\d{2})(?:[.:](\d{1,3}))?\](.*)$')


def _sec(h, m, s, frac):
    frac = (frac or '0')
    return round(int(h or 0) * 3600 + int(m) * 60 + int(s) + int(frac) / (10 ** len(frac)), 3)


def _range(line):
    m = _RANGE.match(line)
    if not m:
        return None
    g = m.groups()
    return _sec(*g[0:4]), _sec(*g[4:8]), g[8]


def parse_json(text):
    d = json.loads(text)
    segs = []
    for t in d.get('transcription', []):
        off = t.get('offsets') or {}
        seg = {'start': off.get('from') / 1000 if off.get('from') is not None else None,
               'end': off.get('to') / 1000 if off.get('to') is not None else None,
               'text': (t.get('text') or '').strip()}
        if seg['start'] is None and t.get('timestamps'):
            r = _range(f"{t['timestamps'].get('from')} --> {t['timestamps'].get('to')}")
            if r:
                seg['start'], seg['end'] = r[0], r[1]
        if t.get('tokens'):
            seg['n_tokens'] = len(t['tokens'])
        segs.append(seg)
    meta = {
        'model': (d.get('model') or {}).get('type') or (d.get('params') or {}).get('model'),
        'language': (d.get('result') or {}).get('language') or (d.get('params') or {}).get('language'),
        'has_tokens': any('n_tokens' in s for s in segs),
    }
    return segs, meta


def parse_srt_vtt(text):
    segs, cur = [], None
    for line in text.splitlines():
        r = _range(line)
        if r:
            cur = {'start': r[0], 'end': r[1], 'text': ''}
            segs.append(cur)
            continue
        if cur is None:
            continue
        if not line.strip():
            cur = None
            continue
        cur['text'] = (cur['text'] + ' ' + line.strip()).strip() if cur['text'] else line.strip()
    return segs, {}


def parse_csv(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    segs = []
    for r in rows:
        r = {(k or '').strip().lower(): v for k, v in r.items()}
        def t(v):
            v = (v or '').strip()
            if re.fullmatch(r'\d+', v):
                return int(v) / 1000  # whisper.cpp の CSV はミリ秒
            rr = _range(f'{v} --> {v}')
            return rr[0] if rr else None
        seg = {'start': t(r.get('start')), 'end': t(r.get('end')), 'text': (r.get('text') or '').strip()}
        if r.get('speaker'):
            seg['speaker'] = r['speaker']
        segs.append(seg)
    return segs, {}


def parse_lrc(text):
    segs = []
    for line in text.splitlines():
        m = _LRC.match(line.strip())
        if not m or not re.fullmatch(r'\d+', m.group(1)):
            continue
        start = _sec(0, m.group(1), m.group(2), m.group(3))
        segs.append({'start': start, 'end': None, 'text': m.group(4).strip()})
    # LRC には終了時刻が無い。次の行の開始で埋めることはしない（推測になるため）
    return segs, {'no_end': True}


def parse_txt(text):
    lines = [l for l in text.splitlines() if l.strip()]
    timed = [_range(l) for l in lines]
    if lines and sum(r is not None for r in timed) >= max(1, len(lines) // 2):
        return [{'start': r[0], 'end': r[1], 'text': r[2].strip()} for r in timed if r], {'timed': True}
    return [{'start': None, 'end': None, 'text': l.strip()} for l in lines], {'timed': False}


def parse_file(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        text = f.read()
    if ext == '.json':
        return parse_json(text)
    if ext in ('.srt', '.vtt'):
        return parse_srt_vtt(text)
    if ext == '.csv':
        return parse_csv(text)
    if ext == '.lrc':
        return parse_lrc(text)
    if ext in ('.txt', '.log'):
        return parse_txt(text)
    raise ValueError(f'未対応の形式: {ext}')


def read_manifest(folder):
    path = os.path.join(folder, 'manifest.csv')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8-sig') as f:
        return {r['file'].strip(): {k: (v or '').strip() for k, v in r.items()}
                for r in csv.DictReader(f) if (r.get('file') or '').strip()}


def match_id(name, known):
    """ファイル名に含まれる既知の動画ID。ちょうど1つのときだけ返す。"""
    hits = sorted({vid for vid in known if vid in name})
    return hits[0] if len(hits) == 1 else None, hits


def load(imports_dir, coll, known_by_channel):
    """known_by_channel: {'dream': {id...}, 'smp': {id...}}"""
    folder = os.path.join(imports_dir, 'whisper_cpp')
    state = {'folder': 'imports/whisper_cpp', 'files': [], 'imported': 0}
    if not os.path.isdir(folder):
        coll.imports['whisper_cpp'] = state
        return
    manifest = read_manifest(folder)
    id2ch = {vid: ch for ch, ids in known_by_channel.items() for vid in ids}
    all_known = set(id2ch)

    for dirpath, _, files in os.walk(folder):
        for name in sorted(files):
            if name in SKIP_NAMES:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, folder)
            info = {'file': rel, 'bytes': os.path.getsize(full), 'sha256': sha256_file(full)}
            state['files'].append(info)
            ext = os.path.splitext(name)[1].lower()
            if ext not in FORMATS:
                info['result'] = 'UNSUPPORTED'
                info['note'] = f'未対応の拡張子 {ext}'
                continue

            m = manifest.get(rel) or manifest.get(name) or {}
            vid = m.get('video_id') or None
            ch = m.get('channel') or None
            if vid:
                if not is_video_id(vid):
                    info.update(result='UNMATCHED', note='manifest の video_id が11文字の動画IDでない')
                    continue
                how = 'manifest'
            else:
                vid, hits = match_id(name, all_known)
                if vid is None:
                    info.update(result='UNMATCHED',
                                note='ファイル名に既知の動画IDが無い' if not hits else f'既知の動画IDが複数含まれる: {hits}')
                    continue
                how = 'filename'
            ch = ch or id2ch.get(vid)
            if ch not in CHANNELS:
                info.update(result='OUT_OF_SCOPE' if ch else 'UNMATCHED',
                            note=f'チャンネルが対象外: {ch}' if ch else
                            '動画IDが既知の一覧に無く、manifest に channel も無い')
                continue

            try:
                segs, meta = parse_file(full)
            except Exception as e:  # 読めなかったものは取り込まず、理由を残す
                info.update(result='PARSE_ERROR', note=f'{type(e).__name__}: {e}')
                continue

            entry = {
                'source': 'whisper_cpp', 'method': 'whisper_cpp', 'kind': 'speech',
                'file': os.path.join('mcshorts/imports/whisper_cpp', rel), 'format': ext.lstrip('.'),
                'sha256': info['sha256'], 'matched_by': how,
                'tool': m.get('model') or meta.get('model'),
                'lang': m.get('language') or meta.get('language'),
                'scope': m.get('scope') or 'full',
                'run_date': m.get('run_date') or None,
                'status': 'UNVERIFIED',
                'segments': segs,
                'note': '形式は実ファイルで未確認。' + (m.get('note') or ''),
                'missing': {},
            }
            if not entry['tool']:
                entry['missing']['tool'] = {'code': 'UNKNOWN', 'note': 'モデル名の記録なし（manifest に model を書く）'}
            if not entry['lang']:
                entry['missing']['lang'] = {'code': 'UNKNOWN', 'note': '言語の記録なし'}
            if not entry['run_date']:
                entry['missing']['run_date'] = {'code': 'UNKNOWN', 'note': '実行日の記録なし（manifest に run_date を書く）'}
            if segs and all(s.get('start') is None for s in segs):
                entry['missing']['timestamps'] = {'code': 'NOT_COLLECTED', 'note': '時刻の無い形式'}
            elif meta.get('no_end'):
                entry['missing']['end'] = {'code': 'NOT_COLLECTED', 'note': 'LRC 形式には終了時刻が無い'}
            if vid not in all_known:
                entry['note'] += ' 動画一覧に未登録（段階2で取得）。'
            coll.add_transcript(ch, vid, entry)
            coll.mark(ch, vid, 'whisper_cpp', 'UNVERIFIED', 'whisper_cpp')
            if entry['scope'] == 'full':
                coll.mark(ch, vid, 'transcript_full', 'UNVERIFIED', 'whisper_cpp')
            info.update(result='IMPORTED', video_id=vid, channel=ch, matched_by=how, n_segments=len(segs))
            state['imported'] += 1
    state['files'].sort(key=lambda x: x['file'])
    coll.imports['whisper_cpp'] = state
