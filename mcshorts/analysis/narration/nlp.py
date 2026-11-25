"""形態素解析（fugashi + unidic-lite）と、文の印（規則）。

伏せ字（〇 ○ ● × ＊ *）は数詞と誤って判定されるので、解析の前に「■」に置き換え、元の位置を記録する。
基本形（lemma）が無い語（未知語・英字の人名など）は、表記をそのまま使う。
"""
import importlib.metadata
import re

import fugashi

FUSEJI = re.compile(r'[〇○●×＊*]')
MASK = '■'

# 規則で使う語の一覧（Claude が決めた。版を記録する）
LEXICON_VERSION = 'v1'
EMOTION = ['悲惨', '悲劇', '怖', '恐怖', '可哀想', 'かわいそう', '狂', '最高', '凄', 'すご', '嬉し', '悲し', '怒',
           'ブチギレ', '絶望', '感動', '号泣', '理不尽', 'スカッと', '気持ちよ', '地獄', '驚', '爆笑', '笑',
           'ざまぁ', '残念', 'サイコパス', 'かっこい', '天罰', '自業自得']
EMPHASIS = ['すぎ', '最強', '史上', '世界一', '絶対', '絶体絶命', '完全', '本当に', '普通に', 'まさか', 'とんでもない',
            'ありえない', '神', '天才', 'ヤバ', 'やば', 'マジ', 'ガチ', '唯一', '全て', 'すべて', 'もはや', '最速',
            '最悪', '異常', '伝説', '奇跡', '一気に', 'さらなる', '更なる', 'ついに', '遂に', '容赦']
CTA = ['チャンネル登録', 'いいね', '高評価', 'フォロー']
DEMONSTRATIVE = ('この', 'その', 'あの', 'こんな', 'そんな', 'あんな')
ADVERSATIVE_SURFACE = {'が', 'けど', 'けれど', 'けれども', 'のに', 'ものの'}
ADVERSATIVE_CONJ = {'しかし', 'でも', 'だが', 'ところが', 'けれど', 'けど', 'なのに', '一方', 'ですが'}


def tagger_info(tagger=None):
    t = tagger or get_tagger()
    return {
        'fugashi': importlib.metadata.version('fugashi'),
        'unidic_lite': importlib.metadata.version('unidic-lite'),
        'dictionary_info': [{k: d.get(k) for k in ('charset', 'size', 'version')} | {'filename': d.get('filename', '').split('/site-packages/')[-1]}
                            for d in t.dictionary_info],
        'lexicon_version': LEXICON_VERSION,
    }


_TAGGER = None


def get_tagger():
    global _TAGGER
    if _TAGGER is None:
        _TAGGER = fugashi.Tagger()
    return _TAGGER


def tokens(text):
    """[{surface, pos1, pos2, lemma, fuseji}]。伏せ字は ■ として扱う（数詞にしない）。"""
    masked = FUSEJI.sub(MASK, text)
    out = []
    for w in get_tagger()(masked):
        f = w.feature
        out.append({'surface': w.surface, 'pos1': f.pos1, 'pos2': f.pos2,
                    'lemma': f.lemma if f.lemma not in (None, '*', '') else w.surface,
                    'fuseji': MASK in w.surface})
    return out


def ja_len(text):
    """文字数（空白・記号を除いた文字。伏せ字は1文字として数える）。"""
    return len(re.sub(r'[\s、。,.!！?？…・「」『』（）()"“”\-ー]', '', text or ''))


def flags(text, toks, tn):
    """文の印（規則）。tn は tools/tn_feat.py（文末の型を借りる）。"""
    t = text.strip()
    clean = tn.clean(t) if t else t
    end = tn.ending(clean) if clean else None
    adv = any((x['pos2'] == '接続助詞' and x['surface'] in ADVERSATIVE_SURFACE) for x in toks) or \
        any(x['surface'] in ADVERSATIVE_CONJ for x in toks) or 'ですが' in t
    return {
        'ending_type': end,
        'question': bool(re.search(r'[？?]$|でしょうか|ますか|ですか', t)),
        'assertion': bool(re.search(r'(です|だ|である|でした|だった)[。！!…]*$', t)) and not re.search(r'ですが[。…]*$', t),
        'adversative': adv,
        'number': any(x['pos2'] == '数詞' and not x['fuseji'] for x in toks),
        'fuseji': any(x['fuseji'] for x in toks),
        'emotion_words': sorted({w for w in EMOTION if w in t}),
        'emphasis_words': sorted({w for w in EMPHASIS if w in t}),
        'cta': any(w in t for w in CTA),
        'proper_nouns': sorted({x['surface'] for x in toks if x['pos2'] == '固有名詞'} |
                               set(re.findall(tn.NAMES, t))),
        'demonstrative_start': t.startswith(DEMONSTRATIVE),
        'prohibition': bool(re.search(r'てはいけません|ないで(ください)?$', t)),
    }


def pos_counts(toks):
    c = {}
    for x in toks:
        c[x['pos1']] = c.get(x['pos1'], 0) + 1
    return dict(sorted(c.items()))
