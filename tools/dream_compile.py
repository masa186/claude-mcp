"""個別分析58本をまとめる。

    python3 tools/dream_compile.py

- dream/individual/*.md の最後の JSON ブロックと、実測・音タグを合わせて dream/comparison.csv を作る
- dream/individual/*.md をつなげて dream/individual_analysis.md を作る
- 横断の集計（再生数との関係）を dream/data/stats.json に書く
"""
import os, re, csv, json, glob, statistics as st
import numpy as np

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dream')
D = os.path.join(R, 'data')


def coded(path):
    s = open(path, encoding='utf-8').read()
    m = re.findall(r'```json\n(\{.*?\})\n```', s, re.S)
    return json.loads(m[-1]), s


def tags(vid):
    p = os.path.join(D, 'audiotag', vid + '.json')
    if not os.path.exists(p):
        return {}
    rows = json.load(open(p))['rows']
    mu = np.array([r['w'].get('Music', 0) for r in rows])
    sp = np.array([r['w'].get('Speech', 0) for r in rows])
    # BGM を一度抜く（Music が 0.15 未満に落ちる秒、冒頭2秒は除く）
    drops = [r['t'] for r in rows if r['t'] >= 2 and r['w'].get('Music', 0) < 0.15]
    return dict(music_mean=round(float(mu.mean()), 2), music_ge05=round(float((mu >= .5).mean()), 2),
                bgm_drops=len(drops), speech_mean=round(float(sp.mean()), 2))


def main():
    vids = {v['id']: v for v in json.load(open(os.path.join(D, 'videos.json')))}
    rows, texts = [], []
    for p in sorted(glob.glob(os.path.join(R, 'individual', '*.md'))):
        c, s = coded(p)
        v = vids[c['id']]
        m = json.load(open(os.path.join(D, 'measure', c['id'] + '.json')))
        t = tags(c['id'])
        sc = c['scores']
        rows.append(dict(
            no=c['no'], id=c['id'], upload=v['upload'], views=v['views'],
            duration_sec=m['dur'], title=v['title'].split('#')[0].strip(),
            top_telop=c['top_telop'], creator=c['creator'], material=c['material'],
            hook_type=c['hook_type'], hook_sec=c['hook_sec'],
            narr_start_sec=c['narr_start'], narr_lines=c['narr_lines'],
            narr_chars_per_sec=c['narr_chars_per_sec'], narr_pattern=c['narr_pattern'],
            ending_type=c['ending_type'], loop=c['loop'],
            cuts=len(m['cuts']), shot_mean_sec=m['shot_mean'], cuts_first3s=len(m['cuts_first3s']),
            sub_changes=m['n_subs'], sub_on_ratio=m['sub_on_ratio'],
            music_mean=t.get('music_mean'), music_ge05_ratio=t.get('music_ge05'),
            bgm_drops=t.get('bgm_drops'),
            s_hook=sc['hook'], s_narration=sc['narration'], s_telop=sc['telop'],
            s_story=sc['story'], s_material=sc['material'], s_edit=sc['edit'],
            s_ending=sc['ending'], s_total=sc['total'],
            file='individual/' + os.path.basename(p)))
        texts.append(s.rstrip())
    rows.sort(key=lambda r: r['no'])
    assert len(rows) == 58, len(rows)
    with open(os.path.join(R, 'comparison.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    head = ('# Dream Clips 58本 個別分析\n\n'
            '58本すべてを1本ずつ分析したもの。番号は受け取った一覧の番号（1＝新しい、58＝古い）。\n'
            '各行の [画面][実測][書き起こし][音タグ][Gemini][考察] の意味は `README.md` を参照。'
            '事実は [画面]〜[Gemini]、解釈は [考察]。\n\n'
            '各動画の末尾の JSON は `comparison.csv` の元データ。\n\n'
            '| # | 再生 | 題名 |\n|---|---|---|\n' +
            ''.join('| [%02d](#%02d) | %s | %s |\n' % (r['no'], r['no'], format(r['views'], ','), r['title'])
                    for r in rows) + '\n---\n\n')
    texts_sorted = [t for _, t in sorted(zip([r['no'] for r in rows], texts))]
    body = '\n\n---\n\n'.join('<a id="%02d"></a>\n\n%s' % (n, t)
                              for n, t in zip(sorted(r['no'] for r in rows), texts_sorted))
    open(os.path.join(R, 'individual_analysis.md'), 'w', encoding='utf-8').write(head + body + '\n')
    json.dump(rows, open(os.path.join(D, 'coded_rows.json'), 'w'), ensure_ascii=False, indent=1)
    print('rows', len(rows))


if __name__ == '__main__':
    main()
