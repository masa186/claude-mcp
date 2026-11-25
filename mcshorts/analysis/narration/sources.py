"""段階4c-1：Dream のナレーション分析の元データを読む（すべて読み取り専用）。

確かさのラベル：
  ok             Whisper の書き起こし・実測・音タグ（機械的に得た値。Whisper は聞き間違いあり）
  DOC_OBSERVED   文書由来の観察。narration_list.md の字幕（Whisper で声を確認済み）、
                 individual/*.md の [画面][実測][書き起こし][音タグ] の印が付いた表・行
  DOC_INTERPRETATION  文書の中の考察（[考察] の行、構成の表の「段階」の列）。事実としては使わない
  UNVERIFIED     ユーザー提供 CSV（dream_tn58）、Claude の分類（段階4b）
Gemini の行は使わない。
"""
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
MCS = os.path.dirname(ANALYSIS)
ROOT = os.path.dirname(MCS)

NARRATION_LIST = 'dream/narration_list.md'
VIDEOS = 'dream/data/videos.json'
INDIVIDUAL = 'dream/individual'
MEASURE = 'dream/data/measure'
AUDIOTAG = 'dream/data/audiotag'
DATA_TRANSCRIPTS = 'mcshorts/data/transcripts/dream'
DATA_FEATURES = 'mcshorts/data/features.jsonl'
CODINGS_4B = 'mcshorts/analysis/codings/dream'

AUDIOTAG_LABELS = ['Speech', 'Narration, monologue', 'Female speech, woman speaking', 'Male speech, man speaking',
                   'Music', 'Laughter', 'Screaming', 'Shout', 'Yell', 'Explosion', 'Boom', 'Sound effect',
                   'Whoosh, swoosh, swish', 'Cheering', 'Gasp', 'Silence']
FACT_TAGS = {'画面', '実測', '書き起こし', '音タグ'}
BOILERPLATE = {'ご視聴ありがとうございました', 'ご視聴ありがとうございました。'}

_JA = re.compile(r'[぀-ヿ一-鿿]')


def p(rel):
    return os.path.join(ROOT, rel)


def load_json(rel):
    with open(p(rel), encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------------ narration_list.md
def split_parts(text):
    """日本語どうしの間の空白で区切る（英語の人名などの中の空白では区切らない）。"""
    out = []
    for piece in re.split(r'[ 　]+', text.strip()):
        if not piece:
            continue
        if out and re.search(r'[A-Za-z0-9]$', out[-1]) and re.match(r'[A-Za-z0-9]', piece):
            out[-1] += ' ' + piece          # 「Grox Jr」のような英数字の並びは区切らない
        else:
            out.append(piece)
    return out


def parse_narration_list():
    """{video_id: {'rows': [...], 'notes': [...]}}。秒は字幕の区間（文単位）。"""
    vids = {v['no']: v['id'] for v in load_json(VIDEOS)}
    with open(p(NARRATION_LIST), encoding='utf-8') as f:
        lines = f.read().splitlines()
    header = '\n'.join(l for l in lines if not l.startswith('|'))
    notes = {}
    for m in re.finditer(r'#(\d{2})', header):
        no = int(m.group(1))
        sent = [s for s in re.split(r'[。\n]', header) if f'#{m.group(1)}' in s]
        notes.setdefault(vids[no], [])
        for s in sent:
            if s.strip() and s.strip() not in notes[vids[no]]:
                notes[vids[no]].append(s.strip())
    out = {}
    cur = None
    for line in lines:
        m = re.match(r'^\|\s*(\d*)\s*\|\s*([\d,]*)\s*\|\s*([\d.]+)〜([\d.]+)\s*\|\s*(.*?)\s*\|\s*$', line)
        if not m:
            continue
        if m.group(1):
            cur = int(m.group(1))
        vid = vids[cur]
        rec = out.setdefault(vid, {'no': cur, 'rows': [], 'notes': notes.get(vid, [])})
        text = m.group(5)
        rec['rows'].append({
            'row_index': len(rec['rows']),
            'start': float(m.group(3)), 'end': float(m.group(4)),
            'text': text,
            'parts': [{'part_index': i, 'text': t} for i, t in enumerate(split_parts(text))],
            'status': 'DOC_OBSERVED', 'source': NARRATION_LIST,
        })
    return out


# ------------------------------------------------------------------ individual/*.md
def _sections(text):
    return {m.group(2): m.group(3) for m in
            re.finditer(r'^### (\d+)\.\s*(.+?)\n(.*?)(?=^### |\Z)', text, re.M | re.S)}


def _table(sec):
    rows = []
    for line in sec.splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if set(''.join(cells)) <= set('-: ') or cells[0] in ('秒', '区間'):
            continue
        rows.append(cells)
    return rows


def _range(s):
    nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', s)]
    if not nums:
        return None, None
    return nums[0], (nums[1] if len(nums) > 1 else None)


def _tags(line):
    raw = re.findall(r'\[([^\]]+)\]', line)
    tags = set()
    for r in raw:
        for t in re.split(r'[・、,\s]+', r.split(':')[0].split('：')[0]):
            if t in FACT_TAGS | {'考察', 'Gemini'}:
                tags.add(t)
    return tags


def parse_individual(video_id):
    files = [f for f in os.listdir(p(INDIVIDUAL)) if video_id in f]
    if len(files) != 1:
        return None
    rel = f'{INDIVIDUAL}/{files[0]}'
    with open(p(rel), encoding='utf-8') as f:
        sec = _sections(f.read())
    k1 = next(k for k in sec if '冒頭0' in k)
    k4 = next(k for k in sec if '構成' in k)
    opening = []
    for c in _table(sec[k1]):
        s, e = _range(c[0])
        opening.append({'time_raw': c[0], 'start': s, 'end': e, 'visual': c[1], 'subtitle': c[2],
                        'status': 'DOC_OBSERVED'})
    structure = []
    for c in _table(sec[k4]):
        s, e = _range(c[0])
        structure.append({'range_raw': c[0], 'start': s, 'end': e,
                          'stage_label': c[1], 'stage_label_status': 'DOC_INTERPRETATION',
                          'content': c[2], 'content_status': 'DOC_OBSERVED'})
    facts, interp, gemini = [], [], 0
    for name, body in sec.items():
        for line in body.splitlines():
            if not line.startswith('- '):
                continue
            tags = _tags(line)
            if 'Gemini' in tags:
                gemini += 1
                continue
            if not tags:
                continue
            item = {'section': name, 'text': line[2:].strip(), 'tags': sorted(tags)}
            (interp if '考察' in tags else facts).append(item)
    return {'file': rel, 'opening_frames': opening, 'structure': structure,
            'fact_lines': facts, 'interpretation_lines': interp, 'gemini_lines_excluded': gemini}


# ------------------------------------------------------------------ Whisper・CSV・実測・音タグ・段階4b
def classify_ja_segment(text):
    t = (text or '').strip()
    if t in BOILERPLATE:
        return 'boilerplate_suspect'
    if re.search(r'(.{1,4})\1{7,}', t):
        return 'repetition_suspect'
    letters = [ch for ch in t if not ch.isspace()]
    if letters and sum(ch.isascii() and ch.isalpha() for ch in letters) / len(letters) >= 0.6:
        return 'latin'
    return 'japanese' if _JA.search(t) else 'other'


def load_whisper(video_id):
    doc = load_json(f'{DATA_TRANSCRIPTS}/{video_id}.json')
    out = {}
    for t in doc['transcripts']:
        if t['source'] == 'dream_asr' and t['scope'] == 'full':
            out[t['lang']] = t
    raw = load_json(f'dream/data/asr/{video_id}.json')   # 単語ごとの時刻は元ファイルにだけある
    return out, raw


def load_csv_tn58(video_id):
    with open(p(DATA_FEATURES), encoding='utf-8') as f:
        for line in f:
            x = json.loads(line)
            if x['channel'] == 'dream' and x['video_id'] == video_id and x['source'] == 'dream_tn58':
                return {'voice': x['fields'].get('voice'), 'sub': x['fields'].get('sub'),
                        'status': x['status'], 'source': 'tools/tn_dream58.json'}
    return None


def load_measure(video_id):
    m = load_json(f'{MEASURE}/{video_id}.json')
    keep = ('dur', 'cuts', 'moves', 'sub_changes', 'top_changes', 'n_shots', 'shot_mean', 'shot_median',
            'cuts_first3s', 'sub_on_ratio', 'n_subs', 'motion_median', 'audio', 'layout')
    return {k: m.get(k) for k in keep}


def load_audiotag(video_id):
    t = load_json(f'{AUDIOTAG}/{video_id}.json')
    rows = [{'t': r['t'], **{k: r['w'].get(k) for k in AUDIOTAG_LABELS}} for r in t['rows']]
    return {'win': t['win'], 'hop': t['hop'], 'labels': AUDIOTAG_LABELS, 'rows': rows}


def load_codes_4b(video_id):
    codes = {}
    with open(p(f'{CODINGS_4B}/claude_v1.jsonl'), encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            if r['video_id'] == video_id:
                codes[r['dimension']] = {'code': r['code'], 'status': r['status'], 'quote': r['quote'],
                                         'review': None, 'effective_code': r['code']}
    rp = p(f'{CODINGS_4B}/review_sample.csv')
    if os.path.exists(rp):
        with open(rp, encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                if row['video_id'] != video_id or not row['確認結果（正しい/違う）']:
                    continue
                c = codes[row['dimension']]
                c['review'] = {'result': row['確認結果（正しい/違う）'], 'corrected_code': row['正しい分類'] or None,
                               'memo': row['メモ'] or None, 'source': f'{CODINGS_4B}/review_sample.csv'}
                if row['確認結果（正しい/違う）'] == '違う' and row['正しい分類']:
                    c['effective_code'] = row['正しい分類']
    return codes
