"""題名（YouTube の投稿タイトル）と上部タイトル（画面上部の見出し）の特徴を、決まった規則で取り出す。

値が無いものは None のまま（0 や False で埋めない）。
上部タイトルは出どころごとに状態（ok / UNVERIFIED）を付け、確認済みを優先して1つ選ぶ。
"""
import re

QUOTE = re.compile(r'[「」『』"“”]')
ELLIPSIS = re.compile(r'…|\.\.\.|‥')
DEMONSTRATIVE = re.compile(r'^(この|その|あの)')


def core_title(t):
    """ハッシュタグを除いた題名本文。"""
    return re.sub(r'\s+', ' ', re.sub(r'#\S+', '', t or '')).strip()


def text_flags(text, tn, prefix):
    """題名・見出し・ナレーションで共通の規則。"""
    if text is None:
        return {}
    t = text
    return {
        f'{prefix}has_question': bool(re.search(r'[？?]', t)),
        f'{prefix}has_exclaim': bool(re.search(r'[！!]', t)),
        f'{prefix}has_ellipsis': bool(ELLIPSIS.search(t)),
        f'{prefix}has_number': bool(tn.has_num(t)),
        f'{prefix}has_person': bool(re.search(tn.NAMES, t)),
        f'{prefix}has_quote': bool(QUOTE.search(t)),
        f'{prefix}superlative': bool(tn.superl(t)),
        f'{prefix}twist': bool(tn.twist(t)),
        f'{prefix}has_ascii_word': bool(re.search(r'[A-Za-z]{2,}', t)),
    }


def title_features(title, tn):
    if title is None:
        return {'t_status': None}
    core = core_title(title)
    f = {
        't_status': 'ok',
        't_core': core,
        't_core_len': len(core),
        't_hashtags': len(re.findall(r'#\S+', title)),
        't_demonstrative_start': bool(DEMONSTRATIVE.search(core)),
        't_ending': tn.ending(core) if core else None,
    }
    f.update(text_flags(core, tn, 't_'))
    return f


def pick_top_title(channel, feats):
    """上部タイトルを1つ選ぶ。確認済み（ok）を優先。戻り値 (行のリスト, 出どころ, 状態) か None。"""
    cands = []
    if channel == 'dream':
        x = feats.get('dream_coded_rows')
        if x and x['fields'].get('top_telop'):
            cands.append(([s.strip() for s in x['fields']['top_telop'].split('／')], 'dream_coded_rows', 'ok'))
        x = feats.get('dream_tn58')
        if x and x['fields'].get('top_lines'):
            lines = x['fields']['top_lines']
            if isinstance(lines, str):
                lines = [s.strip(" '[]") for s in lines.split("',")]
            cands.append((lines, 'dream_tn58', x['status']))
    else:
        x = feats.get('smp_topbottom')
        if x and x['fields'].get('top_title'):
            cands.append(([s.strip() for s in re.split(r'[／/\n]', x['fields']['top_title']) if s.strip()],
                          'smp_topbottom', 'ok'))
        x = feats.get('smp_tn299')
        if x and x['fields'].get('tl') not in (None, '', '[]', []):
            tl = x['fields']['tl']
            if isinstance(tl, str):
                tl = [s.strip(" '[]") for s in tl.split("',") if s.strip(" '[]")]
            if tl:
                cands.append((tl, 'smp_tn299', x['status']))
    if not cands:
        return None
    cands.sort(key=lambda c: 0 if c[2] == 'ok' else 1)
    return cands[0]


def top_title_features(channel, feats, tn):
    pick = pick_top_title(channel, feats)
    if pick is None:
        return {'tt_status': None}
    lines, src, status = pick
    text = ''.join(lines)
    f = {
        'tt_status': status,
        'tt_source': src,
        'tt_text': '／'.join(lines),
        'tt_lines': len(lines),
        'tt_chars': len(text),
        'tt_line1_chars': len(lines[0]) if lines else None,
        'tt_last_chars': len(lines[-1]) if lines else None,
    }
    f.update(text_flags(text, tn, 'tt_'))
    return f
