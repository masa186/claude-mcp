"""伏線の補正レイヤー（v2）：v1 の分類に、ユーザーの確認・指示と規則 A〜D を重ねた有効データを作る（Dream だけ）。

    mcshorts/.venv/bin/python mcshorts/analysis/narration/foreshadow_corrections.py

読むだけのもの（変更しない）
- codings/dream/foreshadow_claude_v1.jsonl（v1 の伏線 51件）
- codings/dream/review_roles.csv（確認済み19件）
- tracks/dream/*.json と、その元の個別分析（dream/individual/*.md）・narration_list.md
- codebook_foreshadow_v2.json、codings/dream/foreshadow_decisions_v2.json、codings/dream/role_decisions_v2.json

書くもの（この2つだけ）
- codings/dream/foreshadow_effective_v2.jsonl：51件の有効データ（AI案は入れない）
- codings/dream/foreshadow_corrections_log.jsonl：変更の履歴

根拠の引用が元データと合わない、規則に反する、51件がそろわない、のどれかがあれば止める。
"""
import csv
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MCS = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(MCS)
sys.path.insert(0, MCS)

from analysis.narration import roles as R  # noqa: E402

CODINGS = os.path.join(HERE, 'codings', 'dream')
TRACKS = os.path.join(HERE, 'tracks', 'dream')
V1_FILE = 'foreshadow_claude_v1.jsonl'
OUT_EFFECTIVE = 'foreshadow_effective_v2.jsonl'
OUT_LOG = 'foreshadow_corrections_log.jsonl'
STATUSES = {'LINKED', 'PARTIAL', 'NOT_FOUND_IN_TEXT', 'HOLD'}
HOLD_REASONS = {'ROLE_HOLD', 'NEEDS_REVIEW'}
DECISION_STATUSES = {'USER_CONFIRMED', 'USER_DIRECTED', 'RULE', 'V1_UNCHANGED'}
REVIEW_RESULT_COL = '確認結果（正しい/違う）'


class QuoteNotFound(Exception):
    pass


class RuleViolation(Exception):
    pass


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_codebook():
    return _load_json(os.path.join(HERE, 'codebook_foreshadow_v2.json'))


def load_v1(codings_dir=CODINGS):
    """v1 の記録と、その行そのものの SHA-256（並びは v1 のまま）。"""
    out = []
    with open(os.path.join(codings_dir, V1_FILE), 'rb') as f:
        for raw in f:
            line = raw.rstrip(b'\n')
            if line:
                out.append((json.loads(line.decode('utf-8')), hashlib.sha256(line).hexdigest()))
    return out


def item_id(r):
    return f"foreshadow:{r['video_id']}:{r['from_row']}:{r['from_part']}"


def read_review_csv(codings_dir=CODINGS):
    with open(os.path.join(codings_dir, 'review_roles.csv'), encoding='utf-8', newline='') as f:
        return {row['item_id']: row for row in csv.DictReader(f)}


def labels_for(v1, reviews):
    """確認対象（6件）を除いた45件に、動画ID・行・部分の順で F01〜F45 を付ける（調査の一覧と同じ番号）。"""
    rest = sorted((r for r, _ in v1 if item_id(r) not in reviews),
                  key=lambda r: (r['video_id'], r['from_row'], r['from_part']))
    return {item_id(r): f'F{i:02d}' for i, r in enumerate(rest, 1)}


def role_holds(reviews, role_decisions):
    """役割が保留の部分（review_roles.csv の「保留」＋ role_decisions_v2.json の HOLD）。"""
    out = {}
    for iid, row in reviews.items():
        if iid.startswith('role:') and row[REVIEW_RESULT_COL] == '保留':
            out[iid] = {'source': 'review_roles.csv', 'memo': row['メモ']}
    for d in role_decisions['decisions']:
        if d['decision'] == 'HOLD':
            out[d['item_id']] = {'source': 'role_decisions_v2.json', 'memo': d['note'], 'decided_on': d['decided_on']}
    return out


def effective_role(r, reviews):
    rid = f"role:{r['video_id']}:{r['from_row']}:{r['from_part']}"
    row = reviews.get(rid)
    if row and row[REVIEW_RESULT_COL] == '違う' and row['正しい分類']:
        return row['正しい分類']
    return r['from_role']


class Resolver:
    """根拠の指定（種類・時刻の範囲・引用）を、tracks と元の文書の両方で照合する。"""

    def __init__(self, tracks, root=ROOT):
        self.tracks = tracks
        self.root = root
        self._md = {}

    def md_lines(self, rel):
        if rel not in self._md:
            with open(os.path.join(self.root, rel), encoding='utf-8') as f:
                self._md[rel] = f.read().splitlines()
        return self._md[rel]

    def resolve(self, vid, preview_row, spec):
        t = self.tracks[vid]
        src, q = spec['source'], spec['quote']
        where = f"{vid} {spec.get('range_raw', spec.get('row', ''))} 「{q[:30]}」"
        if src == 'doc_structure':
            rows = t['doc_individual']['structure']['rows']
            idx = [i for i, s in enumerate(rows) if s['range_raw'] == spec['range_raw']]
            if len(idx) != 1:
                raise QuoteNotFound(f'構成の表に時刻の範囲が1行だけ無い: {where}')
            s = rows[idx[0]]
            if q not in s['content'] or sum(q in x['content'] for x in rows) != 1:
                raise QuoteNotFound(f'引用がその行だけに含まれていない: {where}')
            rel = t['doc_individual']['source']
            md = [i + 1 for i, line in enumerate(self.md_lines(rel)) if line.startswith(f"| {spec['range_raw']} |") and q in line]
            if len(md) != 1:
                raise QuoteNotFound(f'元の個別分析の行と一致しない: {where}')
            return {'source': src, 'quote': q, 'range_raw': s['range_raw'], 'start': s['start'], 'end': s['end'],
                    'time_known': True, 'structure_row': idx[0], 'stage_label': s['stage_label'],
                    'stage_label_status': s['stage_label_status'], 'status': s['content_status'],
                    'source_file': rel, 'source_line': md[0]}
        if src == 'doc_narration':
            rows = [r for r in t['doc_narration']['rows'] if q in r['text']]
            if len(rows) != 1 or rows[0]['row_index'] != spec['row'] or spec['row'] <= preview_row['row_index']:
                raise QuoteNotFound(f'後のナレーションの行と一致しない: {where}')
            rel = t['doc_narration']['source']
            md = [i + 1 for i, line in enumerate(self.md_lines(rel)) if q in line]
            if not md:
                raise QuoteNotFound(f'narration_list.md に無い: {where}')
            r = rows[0]
            return {'source': src, 'quote': q, 'row': r['row_index'], 'start': r['start'], 'end': r['end'],
                    'time_known': True, 'status': r['status'], 'source_file': rel, 'source_line': md[0]}
        if src == 'doc_fact_line':
            lines = t['doc_individual']['fact_lines']['lines']
            idx = [i for i, l in enumerate(lines) if q in l['text']]
            if len(idx) != 1:
                raise QuoteNotFound(f'[画面] の行が1行だけ無い: {where}')
            fl = lines[idx[0]]
            if '画面' not in fl['tags'] or '考察' in fl['tags'] or 'Gemini' in fl['tags']:
                raise RuleViolation(f'規則A：[画面] の行だけを使う（[考察]・Gemini は除く）: {where}')
            rel = t['doc_individual']['source']
            md = [i + 1 for i, line in enumerate(self.md_lines(rel)) if q in line]
            if len(md) != 1 or '[画面]' not in self.md_lines(rel)[md[0] - 1] or '[考察]' in self.md_lines(rel)[md[0] - 1]:
                raise QuoteNotFound(f'元の個別分析の [画面] の行と一致しない: {where}')
            return {'source': src, 'quote': q, 'start': None, 'end': None, 'time_known': False,
                    'fact_line_index': idx[0], 'section': fl['section'], 'tags': fl['tags'],
                    'status': t['doc_individual']['fact_lines']['status'], 'source_file': rel, 'source_line': md[0]}
        if src in ('whisper_en', 'whisper_ja'):
            segs = [s for s in t[src]['segments'] if q in s['text']]
            if len(segs) != 1:
                raise QuoteNotFound(f'Whisper の区間と一致しない: {where}')
            s = segs[0]
            return {'source': src, 'quote': q, 'segment_index': s['segment_index'], 'start': s['start'],
                    'end': s['end'], 'time_known': True, 'status': 'ok', 'source_file': t[src]['source']}
        raise ValueError(f'根拠の種類が codebook に無い: {src}')


def timing(ev, preview_row):
    """規則B：予告の字幕の行が終わった後に始まれば after。"""
    if not ev['time_known']:
        return 'unknown'
    if ev['start'] >= preview_row['end']:
        return 'after'
    if ev['start'] >= preview_row['start']:
        return 'overlap'
    return 'before'


def _short(evs):
    return [f"{e['source']} {e.get('range_raw', e.get('row', '時刻なし'))}「{e['quote']}」" for e in evs]


def _v1_spec(e):
    if e['source'] == 'doc_structure':
        return {'source': e['source'], 'range_raw': e['range_raw'], 'quote': e['quote']}
    if e['source'] == 'doc_narration':
        return {'source': e['source'], 'row': e['row'], 'quote': e['quote']}
    return {'source': e['source'], 'quote': e['quote']}


def check_record(rec, holds):
    """状態と根拠の欄の決まり（規則B・C・D と codebook の状態）を検査する。"""
    iid, st, ev = rec['item_id'], rec['status'], rec['evidence']
    if st not in STATUSES or rec['decision_status'] not in DECISION_STATUSES:
        raise RuleViolation(f'{iid}: codebook に無い状態')
    for e in ev:
        if e['timing'] not in ('after', 'unknown'):
            raise RuleViolation(f'{iid}: 規則B：予告の字幕の行が終わる前に始まる場面は回収の根拠にできない')
        if e['timing'] == 'unknown' and e['source'] != 'doc_fact_line':
            raise RuleViolation(f'{iid}: 時刻なしの根拠は [画面] の行だけ')
    for e in rec['concurrent']:
        if e['timing'] not in ('before', 'overlap'):
            raise RuleViolation(f'{iid}: 同時の説明は予告の字幕の行が終わる前に始まる場面だけ')
    if st == 'LINKED' and (not ev or rec['not_confirmed']):
        raise RuleViolation(f'{iid}: LINKED は根拠があり、確認できない要素が無い')
    if st == 'PARTIAL' and (not ev or not rec['not_confirmed']):
        raise RuleViolation(f'{iid}: 規則D：PARTIAL は根拠と確認できない要素の両方がある')
    if st == 'NOT_FOUND_IN_TEXT' and ev:
        raise RuleViolation(f'{iid}: NOT_FOUND は根拠が空')
    if st == 'HOLD':
        if ev or rec['hold_reason'] not in HOLD_REASONS:
            raise RuleViolation(f'{iid}: HOLD は根拠が空で、理由がある')
    elif rec['hold_reason'] is not None:
        raise RuleViolation(f'{iid}: HOLD 以外に保留の理由は付けない')
    role_on_hold = rec['from_role_item_id'] in holds
    if role_on_hold != (st == 'HOLD' and rec['hold_reason'] == 'ROLE_HOLD'):
        raise RuleViolation(f'{iid}: 規則C：起点の役割が保留 ⇔ HOLD（ROLE_HOLD）')


def _resolve_list(res, vid, prow, specs, keep=('relation', 'origin', 'note', 'kind')):
    out = []
    for sp in specs or []:
        e = res.resolve(vid, prow, sp)
        e['timing'] = timing(e, prow)
        for k in keep:
            if k in sp:
                e[k] = sp[k]
        out.append(e)
    return out


def time_word_notes(cb, rec, prow):
    words = [w for w in cb['time_words'] if w in rec['from_quote']]
    known = [e for e in rec['evidence'] if e['time_known']]
    if not words or not known:
        return []
    first = min(e['start'] for e in known)
    return [{'kind': 'time_word', 'words': words, 'preview_row_start': prow['start'], 'first_evidence_start': first,
             'gap_seconds': round(first - prow['start'], 2),
             'text': f"予告の「{'・'.join(words)}」と、最初の回収の根拠（{first}秒）の差は {round(first - prow['start'], 2)} 秒。判定には使わない"}]


def build(out_dir=CODINGS, codings_dir=CODINGS, tracks_dir=TRACKS, root=ROOT):
    cb = load_codebook()
    v1 = load_v1(codings_dir)
    reviews = read_review_csv(codings_dir)
    decisions = _load_json(os.path.join(codings_dir, 'foreshadow_decisions_v2.json'))
    role_dec = _load_json(os.path.join(codings_dir, 'role_decisions_v2.json'))
    tracks = R.load_tracks(tracks_dir)
    res = Resolver(tracks, root)
    holds = role_holds(reviews, role_dec)
    labels = labels_for(v1, reviews)
    ids = [item_id(r) for r, _ in v1]
    if len(ids) != 51 or len(set(ids)) != 51:
        raise ValueError(f'v1 の伏線が51件そろっていない: {len(ids)}')
    for d in role_dec['decisions']:
        _, vid, row, part = d['item_id'].split(':')
        if tracks[vid]['doc_narration']['rows'][int(row)]['parts'][int(part)]['text'] != d['quote']:
            raise QuoteNotFound(f"役割の判断の引用が字幕と一致しない: {d['item_id']}")
    dec_by = {}
    for d in decisions['decisions']:
        if d['item_id'] in dec_by or d['item_id'] not in ids:
            raise ValueError(f"判定の item_id が重複している、または v1 に無い: {d['item_id']}")
        if 'label' in d and labels.get(d['item_id']) != d['label']:
            raise ValueError(f"番号が一覧と合わない: {d['item_id']} {d.get('label')}")
        dec_by[d['item_id']] = d

    records, logs = [], []
    for r, sha in v1:
        iid = item_id(r)
        vid = r['video_id']
        prow = tracks[vid]['doc_narration']['rows'][r['from_row']]
        if prow['parts'][r['from_part']]['text'] != r['from_quote']:
            raise QuoteNotFound(f'{iid}: 予告の引用が字幕と一致しない')
        role = effective_role(r, reviews)
        rid = f"role:{vid}:{r['from_row']}:{r['from_part']}"
        if rid not in holds and role not in R.PREVIEW | {R.REHOOK}:
            raise RuleViolation(f'{iid}: 起点の役割が予告ではない（{role}）')
        v1_ev = _resolve_list(res, vid, prow, [_v1_spec(e) for e in r['evidence']])
        for e, orig in zip(v1_ev, r['evidence']):
            if e['source'] == 'doc_structure' and e['structure_row'] != orig['structure_row']:
                raise QuoteNotFound(f'{iid}: v1 の根拠の行が変わっている')
        rec = {'item_id': iid, 'label': labels.get(iid), 'channel': r['channel'], 'video_id': vid,
               'from_row': r['from_row'], 'from_part': r['from_part'], 'from_quote': r['from_quote'],
               'from_row_start': prow['start'], 'from_row_end': prow['end'], 'from_role': r['from_role'],
               'from_role_effective': 'HOLD' if rid in holds else role, 'from_role_item_id': rid,
               'v1_status': r['status'], 'v1_note': r['note'], 'v1_sha256': sha,
               'reviewed_in_csv': iid in reviews}
        steps = [{'seq': 1, 'kind': 'v1', 'by': r['coder'], 'status': r['status'], 'evidence': _short(v1_ev),
                  'note': r['note'], 'certainty': 'UNVERIFIED'}]
        d = dec_by.get(iid)
        if d:
            ev = _resolve_list(res, vid, prow, d.get('evidence'))
            conc = _resolve_list(res, vid, prow, d.get('concurrent'))
            ref = _resolve_list(res, vid, prow, d.get('reference'))
            for x in ref:
                if 'kind' not in x or x['kind'] not in cb['reference_kinds']:
                    raise RuleViolation(f'{iid}: 参考の場面の種類が codebook に無い')
            for s in d['sources']:
                if s['kind'] == 'review_csv':
                    row = reviews[s['item_id']]
                    if row[REVIEW_RESULT_COL] != s['expect']:
                        raise ValueError(f'{iid}: 確認結果が review_roles.csv と合わない')
                    steps.append({'seq': len(steps) + 1, 'kind': 'user_review_csv', 'by': 'user',
                                  'source': f"review_roles.csv {s['item_id']}", 'result': row[REVIEW_RESULT_COL],
                                  'corrected': row['正しい分類'], 'memo': row['メモ']})
                else:
                    steps.append({'seq': len(steps) + 1, 'kind': 'user_chat', 'by': 'user', 'date': s['date'],
                                  'text': s['text']})
            for rule in d.get('rules_applied', []):
                steps.append({'seq': len(steps) + 1, 'kind': f'rule_{rule}', 'text': cb['rules'][rule]})
            kept = {(e['source'], e['quote']) for e in ev}
            removed = [e for e in v1_ev if (e['source'], e['quote']) not in kept]
            rec.update({'status': d['status'], 'hold_reason': d.get('hold_reason'), 'evidence': ev,
                        'concurrent': conc, 'reference': ref, 'not_confirmed': d.get('not_confirmed', []),
                        'decision_status': d['decision_status'], 'confirmed': True,
                        'confirmed_basis': 'ユーザーの確認・指示', 'user_notes': d.get('user_notes', [])})
            if removed:
                steps.append({'seq': len(steps) + 1, 'kind': 'v1_evidence_not_used', 'evidence': _short(removed)})
        else:
            ev, conc, ref, nc = list(v1_ev), [], [], []
            status, hold_reason, ds, confirmed, basis = r['status'], None, 'V1_UNCHANGED', False, 'v1（Claude・UNVERIFIED）'
            if status == 'NOT_FOUND_IN_TEXT' and ev:
                ref = [dict(e, kind='reference_nearest', origin='v1') for e in ev]
                ev, ds = [], 'RULE'
                basis = '状態は v1 のまま（未確認）。根拠の欄の参考の場面を移しただけ'
                steps.append({'seq': len(steps) + 1, 'kind': 'rule_structure',
                              'text': 'NOT_FOUND の根拠の欄にあった場面を参考の場面（reference_nearest）に移す', 'moved': _short(ref)})
            moved = [e for e in ev if e['timing'] in ('before', 'overlap')]
            if moved:
                conc = [dict(e, origin='v1') for e in moved]
                ev = [e for e in ev if e['timing'] not in ('before', 'overlap')]
                ds = 'RULE'
                steps.append({'seq': len(steps) + 1, 'kind': 'rule_B', 'text': cb['rules']['B'], 'moved': _short(moved)})
                if not ev and status in ('LINKED', 'PARTIAL'):
                    status, hold_reason = 'HOLD', 'NEEDS_REVIEW'
                    basis = '規則Bで回収の根拠が無くなり、再判定待ち（状態は未確定）'
            if rid in holds:
                ref = ref + [dict(e, kind='pending_candidate', origin='v1') for e in ev]
                ev, status, hold_reason, ds, confirmed = [], 'HOLD', 'ROLE_HOLD', 'RULE', False
                basis = (f"規則Cで機械的に保留（未確定）。元のユーザー判断は basis_user_decision"
                         f"（起点の役割が {holds[rid]['source']} で保留）")
                steps.append({'seq': len(steps) + 1, 'kind': 'rule_C', 'text': cb['rules']['C'],
                              'role_hold': holds[rid]})
            for e in ev:
                e.setdefault('relation', 'unspecified')
                e.setdefault('origin', 'v1')
            rec.update({'status': status, 'hold_reason': hold_reason, 'evidence': ev, 'concurrent': conc,
                        'reference': ref, 'not_confirmed': nc, 'decision_status': ds, 'confirmed': confirmed,
                        'confirmed_basis': basis, 'user_notes': []})
        rec['notes'] = time_word_notes(cb, rec, prow)
        rec['basis_user_decision'] = ({'role_item_id': rid, **holds[rid]}
                                      if rec['hold_reason'] == 'ROLE_HOLD' and rid in holds else None)
        check_record(rec, holds)
        if rec['confirmed'] != (rec['decision_status'] in ('USER_CONFIRMED', 'USER_DIRECTED')):
            raise RuleViolation(f'{iid}: confirmed=true は USER_CONFIRMED・USER_DIRECTED だけ')
        records.append(rec)
        if len(steps) > 1:
            steps.append({'seq': len(steps) + 1, 'kind': 'effective_v2', 'status': rec['status'],
                          'hold_reason': rec['hold_reason'], 'decision_status': rec['decision_status'],
                          'evidence': _short(rec['evidence'])})
            logs.append({'item_id': iid, 'label': rec['label'], 'v1_sha256': sha, 'steps': steps})

    proposals = check_proposals(decisions['ai_proposals'], res, tracks, v1, labels, holds, cb)
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in ((OUT_EFFECTIVE, records), (OUT_LOG, logs)):
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8') as f:
            for x in rows:
                f.write(json.dumps(x, ensure_ascii=False, sort_keys=True) + '\n')
    return {'records': records, 'logs': logs, 'proposals': proposals}


def check_proposals(props, res, tracks, v1, labels, holds, cb):
    """AI案も同じ照合と規則で検査する（有効データには入れない。confirmed=false）。"""
    by = {item_id(r): r for r, _ in v1}
    out = []
    seen = set()
    for p in props:
        iid = p['item_id']
        if iid not in by or iid in seen or labels.get(iid) != p['label']:
            raise ValueError(f'AI案の item_id・番号が合わない: {iid}')
        seen.add(iid)
        r = by[iid]
        prow = tracks[r['video_id']]['doc_narration']['rows'][r['from_row']]
        rec = {'item_id': iid, 'status': p['proposed_status'], 'hold_reason': p.get('proposed_hold_reason'),
               'evidence': _resolve_list(res, r['video_id'], prow, p.get('evidence')),
               'concurrent': _resolve_list(res, r['video_id'], prow, p.get('concurrent')),
               'not_confirmed': p.get('not_confirmed', []), 'decision_status': 'V1_UNCHANGED',
               'from_role_item_id': f"role:{r['video_id']}:{r['from_row']}:{r['from_part']}"}
        _resolve_list(res, r['video_id'], prow, p.get('reference'))
        _resolve_list(res, r['video_id'], prow, p.get('user_declined'))
        check_record(rec, holds)
        out.append({'item_id': iid, 'label': p['label'], 'proposed_status': p['proposed_status'],
                    'confirmed': False, 'proposer': 'claude'})
    return out


if __name__ == '__main__':
    from collections import Counter
    r = build()
    recs = r['records']
    print('有効データ', len(recs), Counter(x['status'] for x in recs))
    print('判定の出どころ', Counter(x['decision_status'] for x in recs))
    print('確定済み（confirmed=true）', sum(x['confirmed'] for x in recs), Counter(x['status'] for x in recs if x['confirmed']))
    print('保留の理由', Counter(x['hold_reason'] for x in recs if x['status'] == 'HOLD'))
    print('変更の履歴', len(r['logs']), '件 ／ AI案（検査済み・有効データには入れない）', len(r['proposals']), '件')
