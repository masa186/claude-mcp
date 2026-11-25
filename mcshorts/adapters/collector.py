"""各アダプタが読んだものを集め、共通形式（videos / transcripts / features / coverage）に組み立てる。

値を1つに決めることはしない。出どころごとの観測をすべて残し、食い違いは conflicts に出す。
"""
from collections import defaultdict

from .common import CHANNELS, STATUSES, missing, norm_title, date_part

# 充足表の項目（順番は表示順）
ITEMS = [
    ('list_api', '一覧（YouTube API）'),
    ('views', '再生数の観測'),
    ('top_title', '上部タイトル'),
    ('narration_text', 'ナレーション文（CSV由来）'),
    ('transcript_opening', '冒頭の書き起こし'),
    ('transcript_full', '全編の書き起こし'),
    ('whisper_cpp', 'whisper.cpp の取り込み'),
    ('gemini_av', 'Gemini の映像・音の読み'),
    ('measure', '実測（カット・字幕・音量）'),
    ('audiotag', '音タグ'),
    ('coded_features', '構成の分類（個別分析）'),
    ('media_file', '動画ファイル'),
]
ITEM_KEYS = [k for k, _ in ITEMS]

# 何も記録が無いときの欠損理由（チャンネル別）
DEFAULT_MISSING = {
    'list_api': ('NOT_COLLECTED', 'API の一覧に無い'),
    'views': ('NOT_COLLECTED', None),
    'top_title': ('NOT_COLLECTED', None),
    'narration_text': ('NOT_COLLECTED', None),
    'transcript_opening': ('NOT_COLLECTED', None),
    'transcript_full': ('NOT_COLLECTED', None),
    'whisper_cpp': ('NOT_COLLECTED', 'imports/whisper_cpp/ に該当ファイルなし'),
    'gemini_av': ('NOT_COLLECTED', None),
    'measure': ('NOT_COLLECTED', '動画ファイルが必要'),
    'audiotag': ('NOT_COLLECTED', '動画ファイルが必要'),
    'coded_features': ('NOT_COLLECTED', None),
    'media_file': ('NO_MEDIA', None),
}

_RANK = {'ok': 3, 'UNVERIFIED': 2, 'REJECTED': 1}


class Collector:
    def __init__(self, sources):
        self.sources = sources
        self.obs = defaultdict(list)          # (ch, vid) -> [観測]
        self.extra = defaultdict(dict)        # (ch, vid) -> {key: value}
        self.transcripts = defaultdict(list)  # (ch, vid) -> [書き起こし]
        self.features = []                    # [{channel, video_id, source, status, fields}]
        self.marks = defaultdict(dict)        # (ch, vid) -> {item: {'status'|'missing', 'sources', 'note'}}
        self.channel_missing = defaultdict(dict)  # ch -> {item: missing}
        self.anomalies = []                   # 照合できなかったもの等
        self.list_diffs = []                  # 一覧どうしの差（事実だけ。理由は書かない）
        self.api_not_returned = []            # API の取得で返ってこなかった動画
        self.snapshots = {}                   # API の取得結果の状態（チャンネル別）
        self.imports = {}                     # 取り込みフォルダの状態

    # ---- 追加
    def video_obs(self, ch, vid, sid, **fields):
        assert ch in CHANNELS, ch
        o = {'source': sid}
        o.update({k: v for k, v in fields.items()})
        self.obs[(ch, vid)].append(o)
        if fields.get('views') is not None:
            self.mark(ch, vid, 'views', 'ok', sid,
                      None if fields.get('observed_at') else '値はある。取得日時は不明（observed_before が上限）')

    def set_extra(self, ch, vid, key, value):
        self.extra[(ch, vid)][key] = value

    def add_transcript(self, ch, vid, entry):
        assert ch in CHANNELS, ch
        assert entry.get('status') in STATUSES, entry.get('status')
        self.transcripts[(ch, vid)].append(entry)

    def add_feature(self, ch, vid, sid, fields, status='ok'):
        assert status in STATUSES
        self.features.append({'channel': ch, 'video_id': vid, 'source': sid,
                              'status': status, 'fields': fields})

    def mark(self, ch, vid, item, status, sid, note=None):
        """値がある：status は ok / UNVERIFIED / REJECTED。良い方を残し、出どころは全部残す。"""
        assert item in ITEM_KEYS, item
        assert status in STATUSES, status
        cur = self.marks[(ch, vid)].get(item)
        if cur is None or 'missing' in cur:
            self.marks[(ch, vid)][item] = {'status': status, 'sources': [sid]}
            if note:
                self.marks[(ch, vid)][item]['note'] = note
            return
        if sid not in cur['sources']:
            cur['sources'].append(sid)
        if _RANK[status] > _RANK[cur['status']]:
            cur['status'] = status

    def mark_missing(self, ch, vid, item, code, note=None):
        assert item in ITEM_KEYS, item
        cur = self.marks[(ch, vid)].get(item)
        if cur is None:
            self.marks[(ch, vid)][item] = {'missing': missing(code, note)}

    def set_channel_missing(self, ch, item, code, note=None):
        self.channel_missing[ch][item] = missing(code, note)

    def anomaly(self, kind, **info):
        self.anomalies.append(dict(kind=kind, **info))

    # ---- 組み立て
    def keys(self):
        ks = set(self.obs) | set(self.transcripts) | set(self.marks) | {
            (f['channel'], f['video_id']) for f in self.features}
        return sorted(ks)

    def known_ids(self, ch=None):
        return {vid for (c, vid) in self.obs if ch is None or c == ch}

    def coverage_cell(self, ch, vid, item):
        m = self.marks[(ch, vid)].get(item)
        if m is not None:
            return m
        if item in self.channel_missing[ch]:
            return {'missing': self.channel_missing[ch][item]}
        code, note = DEFAULT_MISSING[item]
        return {'missing': missing(code, note)}

    def build_videos(self):
        rows = []
        for ch, vid in self.keys():
            obs = self.obs.get((ch, vid), [])

            def prov(o):
                p = self.sources.provenance(o['source'])
                # API の取得結果は動画ごとに正確な取得日時を持つ。段階1の観測にはこの項目が無い
                if o.get('observed_at') is not None:
                    p['observed_at'] = o['observed_at']
                return p

            def field_obs(name):
                out = []
                for o in obs:
                    if o.get(name) is not None:
                        out.append({'value': o[name], **prov(o)})
                return out

            views = []
            for o in obs:
                if o.get('views') is None:
                    continue
                v = {'views': o['views'], **prov(o)}
                for k in ('likes', 'comments'):
                    v[k] = o.get(k)
                views.append(v)

            row = {
                'channel': ch,
                'video_id': vid,
                'url': f'https://www.youtube.com/watch?v={vid}',
                'title': field_obs('title'),
                'published': field_obs('published'),
                'duration_sec': field_obs('duration_sec'),
                'views': views,
                'in_sources': sorted({o['source'] for o in obs}),
                'extra': dict(sorted(self.extra.get((ch, vid), {}).items())),
                'missing': {},
            }
            for name in ('title', 'published', 'duration_sec'):
                if not row[name]:
                    row['missing'][name] = missing('NOT_COLLECTED', 'どの一覧にも記録なし')
            if not views:
                row['missing']['views'] = missing('NOT_COLLECTED', 'どの一覧にも記録なし')
            elif all(v['observed_at'] is None for v in views):
                row['missing']['views_observed_at'] = missing(
                    'UNKNOWN', '再生数の取得日時はどの出どころにも記録なし（observed_before が上限）')
            if all(v.get('likes') is None for v in views):
                row['missing']['likes_comments'] = missing('NOT_COLLECTED', 'API の一覧に無い')
            rows.append(row)
        return rows

    def build_transcripts(self):
        out = {}
        for (ch, vid), entries in sorted(self.transcripts.items()):
            out[(ch, vid)] = {
                'channel': ch,
                'video_id': vid,
                'transcripts': sorted(entries, key=lambda e: (e['source'], e.get('lang') or '',
                                                               e.get('scope') or '', e.get('kind') or '',
                                                               e.get('file') or '')),
            }
        return out

    def build_conflicts(self, videos):
        """同じはずの値が出どころで食い違うもの。再生数は時点が違うので食い違いとして扱わない。"""
        out = []
        for r in videos:
            key = {'channel': r['channel'], 'video_id': r['video_id']}
            t = {}
            for o in r['title']:
                t.setdefault(norm_title(o['value']), []).append(o['source'])
            if len(t) > 1:
                out.append({**key, 'field': 'title',
                            'values': [{'value': o['value'], 'source': o['source']} for o in r['title']]})
            d = {}
            for o in r['published']:
                d.setdefault(date_part(o['value']), []).append(o['source'])
            if len(d) > 1:
                out.append({**key, 'field': 'published_date',
                            'values': [{'value': o['value'], 'source': o['source']} for o in r['published']],
                            'note': 'API は UTC。ほかの出どころの時刻帯は記録なし'})
            durs = [o['value'] for o in r['duration_sec'] if isinstance(o['value'], (int, float))]
            if durs and max(durs) - min(durs) > 1.0:
                out.append({**key, 'field': 'duration_sec',
                            'values': [{'value': o['value'], 'source': o['source']} for o in r['duration_sec']],
                            'note': '1秒を超える差'})
        return out

    @staticmethod
    def build_view_decreases(videos):
        """正確な取得日時がある観測どうしで、後の再生数が前より小さいもの（直さずに一覧にする）。"""
        out = []
        for r in videos:
            timed = sorted((v for v in r['views'] if v.get('observed_at')), key=lambda v: v['observed_at'])
            for a, b in zip(timed, timed[1:]):
                if isinstance(a['views'], int) and isinstance(b['views'], int) and b['views'] < a['views']:
                    out.append({'channel': r['channel'], 'video_id': r['video_id'],
                                'before': {'views': a['views'], 'observed_at': a['observed_at'], 'source': a['source']},
                                'after': {'views': b['views'], 'observed_at': b['observed_at'], 'source': b['source']}})
        return out

    @staticmethod
    def build_likes_zero_vs_null(videos):
        """既存の観測で高評価数が 0、API の取得結果では null（非公開）になっているもの。既存の値は書き換えない。"""
        out = []
        for r in videos:
            zero = [v for v in r['views'] if v.get('likes') == 0 and not v.get('observed_at')]
            hidden = [v for v in r['views'] if v.get('observed_at') and v.get('likes') is None]
            if zero and hidden:
                out.append({'channel': r['channel'], 'video_id': r['video_id'],
                            'zero_sources': sorted({v['source'] for v in zero}),
                            'null_sources': sorted({v['source'] for v in hidden})})
        return out

    def build_coverage(self):
        rows = []
        for ch, vid in self.keys():
            cells = {item: self.coverage_cell(ch, vid, item) for item in ITEM_KEYS}
            rows.append({'channel': ch, 'video_id': vid, 'cells': cells})
        return rows
