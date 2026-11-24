"""1本ぶんの材料（実測・書き起こし・音タグ・Gemini）を1枚の文字にまとめて出す。

    python3 tools/dream_dossier.py <no または id> ...

個別分析を書くときに、これとコマのシートを並べて見る。
"""
import os, sys, json, re
import numpy as np

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dream', 'data')
JA = re.compile(r'[぀-ヿ一-鿿]')


def j(sub, vid):
    p = os.path.join(D, sub, vid + '.json')
    return json.load(open(p)) if os.path.exists(p) else None


def narration(asr):
    """日本語ナレーション（日本語の文字を含む区間）を拾う"""
    out = []
    for s in asr['ja']['segs']:
        t = s['text']
        if not JA.search(t):
            continue
        # 区間の中で最初の日本語の語の時刻を、ナレーション開始とみなす
        st = s['start']
        for w in s.get('words', []):
            if JA.search(w[2]):
                st = w[0]
                break
        out.append(dict(start=st, end=s['end'], text=t, no_speech=s['no_speech']))
    return out


def tag_summary(at):
    rows = at['rows']
    if not rows:
        return {}
    music = np.array([r['w'].get('Music', 0) for r in rows])
    speech = np.array([r['w'].get('Speech', 0) for r in rows])
    notable = []
    skip = {'Speech', 'Music', 'Musical instrument', 'Male speech, man speaking',
            'Female speech, woman speaking', 'Narration, monologue', 'Child speech, kid speaking',
            'Silence', 'Television', 'Inside, small room', 'Vehicle', 'Single-lens reflex'}
    for r in rows:
        for name, pr in r['top']:
            if name not in skip and pr >= 0.15:
                notable.append('%ds %s %.2f' % (r['t'], name, pr))
    voice = {k: round(float(np.mean([r['w'].get(k, 0) for r in rows])), 3)
             for k in ('Male speech, man speaking', 'Female speech, woman speaking',
                       'Child speech, kid speaking')}
    return dict(music_mean=round(float(music.mean()), 2),
                music_ge05_ratio=round(float((music >= 0.5).mean()), 2),
                music_by_sec=' '.join('%d' % round(x * 9) for x in music),
                speech_by_sec=' '.join('%d' % round(x * 9) for x in speech),
                notable=notable, voice=voice)


def show(v):
    vid = v['id']
    print('=' * 70)
    print('#%02d %s  %s' % (v['no'], vid, v['title']))
    print('再生 %s / API長さ %ss / 投稿 %s' % (format(v['views'], ','), v['duration'], v['upload']))
    m = j('measure', vid)
    if m:
        print('[実測] 長さ %.2fs  レイアウト %s' % (m['dur'], m['layout']))
        print('[実測] カット %d回（ショット平均 %.2fs, 中央値 %.2fs） 0〜3秒のカット %s' % (
            len(m['cuts']), m['shot_mean'], m['shot_median'], m['cuts_first3s']))
        print('[実測] カット秒 %s' % m['cuts'])
        print('[実測] 連続的な大きな動き（ズーム/パン/暗転の候補） %s' % m['moves'])
        print('[実測] 字幕の切替 %d回  字幕が出ている割合 %s  上部テロップの変化 %s' % (
            m['n_subs'], m['sub_on_ratio'], m['top_changes']))
        a = m.get('audio') or {}
        print('[実測] 音 最初に音が出る %ss / 中央値 %sdB / 95%% %sdB / 突出(中央値+8dB) %s' % (
            a.get('onset'), a.get('median_db'), a.get('p95_db'), a.get('spikes')))
        print('[実測] 0〜3秒の音量(0.2秒刻み dB) %s' % a.get('first3s_db'))
        print('[シート] %s 枚, コマの秒 %s' % (m['n_sheets'], m['sheet_times']))
    asr = j('asr', vid)
    if asr:
        nar = narration(asr)
        print('[書き起こし・日本語ナレーション] %d 文' % len(nar))
        for s in nar:
            print('  %6.2f-%6.2f %s%s' % (s['start'], s['end'], s['text'],
                                         '  (no_speech %.2f)' % s['no_speech'] if s['no_speech'] > 0.5 else ''))
        print('[書き起こし・英語の元音声]')
        for s in asr['en']['segs']:
            flag = '  (怪しい)' if s['no_speech'] > 0.6 or s['logprob'] < -1.0 else ''
            print('  %6.2f-%6.2f %s%s' % (s['start'], s['end'], s['text'], flag))
    else:
        print('[書き起こし] まだ無い')
    ed = j('asr_edges', vid)
    if ed:
        print('[書き起こし・冒頭5秒と最後7秒を日本語指定で再書き起こし]')
        for s in ed['head'] + ed['tail']:
            print('  %6.2f-%6.2f %s' % (s['start'], s['end'], s['text']))
    at = j('audiotag', vid)
    if at:
        t = tag_summary(at)
        print('[音タグ(AST自動判定)] Music 平均 %.2f / 0.5以上の秒の割合 %.2f / 声の性別 %s' % (
            t['music_mean'], t['music_ge05_ratio'], t['voice']))
        print('  Music(0-9) 1秒ごと: %s' % t['music_by_sec'])
        print('  Speech(0-9)1秒ごと: %s' % t['speech_by_sec'])
        print('  目立つ音: %s' % '; '.join(t['notable'][:30]))
    else:
        print('[音タグ] まだ無い')
    g = j('gemini', vid)
    if g:
        # Gemini は秒を「分.秒」（0.31＝31秒）で返すことがある。全部の t が 2 未満なら分.秒とみなして直す
        ts = [x.get('t') for k in ('narration_lines', 'bgm', 'sfx', 'visual_edits', 'top_text', 'beats')
              for x in (g.get(k) or []) if isinstance(x, dict) and isinstance(x.get('t'), (int, float))]
        if ts and max(ts) < 2 and v['duration'] > 20:
            for k in ('narration_lines', 'bgm', 'sfx', 'visual_edits', 'top_text', 'beats'):
                for x in (g.get(k) or []):
                    if isinstance(x, dict) and isinstance(x.get('t'), (int, float)):
                        t = x['t']; x['t'] = int(t) * 60 + round((t - int(t)) * 100)
            print('  ※Gemini の秒は「分.秒」だったので秒に直した')
        print('[Gemini判定 %s]' % g.get('_model'))
        print(json.dumps({k: v for k, v in g.items() if k != '_model'}, ensure_ascii=False)[:3000])
    else:
        print('[Gemini] 取得できず（無料枠の上限・混雑）')


if __name__ == '__main__':
    vids = json.load(open(os.path.join(D, 'videos.json')))
    for a in sys.argv[1:]:
        for v in vids:
            if a == v['id'] or (a.isdigit() and int(a) == v['no']):
                show(v)
