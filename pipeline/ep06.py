"""第6話「ぐるぐるの正体」（蚊取り線香）

参考チャンネル「無限の机」の18本を測って作りを変えた（docs/reference.md）。
一番はっきりした差はこれだった。

  同じチャンネルの中で、10万回/日を超えた5本は全部「失敗→改良」を
  2〜4回やっていて、1万回に届かなかった4本は1回もやっていない。5対0。

第1〜5話には失敗が1つも無い。問い→説明→答え、で誰も何も試していない。
ここを作り直す。ほかに変えたのは3つ。

  尺   43〜48秒 → 72秒（623本の実測で60〜90秒が中央値5,634回/日と最高。
       #shorts明記の有無で割っても同じ向き。43〜48秒は弱い帯の隣だった）
  題名 答えも題材名も書かない（向こうは「火を使わずにお湯を沸かす
       天才的発明」で中身がIH。「なぜ・仕組み」型は471本でも向こうの
       18本でも最下位）
  答え 尺の72% → 86%（向こうの中央値は88%）

中身の裏取りは先に済ませた（~/yt-analysis/data/katori.md）。
言ってはいけない言い方も確認済み:
  ×「煙でいぶして殺している」 → 熱で気化した成分が効く
  ×「人間も死ぬ」
  △ 1902年は「完成」した年。発売年と混同しない
  △ 7時間は製品・太さで6〜8時間の幅がある

  python3 ep06.py           全部書き出し
  SHORT=1 python3 ep06.py   TikTok用の短縮版
  python3 ep06.py --script  ナレーション原稿を出す
"""
import os, sys, time, subprocess
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

render.SHOTS = [
 # ============ つかみ（0〜5秒）。現象だけ見せる。名前は最後まで出さない
 # 向こうの4本は全部「動いているものが最初から映っている」。
 # こちらも、燃えている所と蚊が落ちる所を0秒から動かす。
 #
 # 声を持たないショットを挟んで、1行の声を2枚にまたがせている。
 # 実測で分かったこと: 声に合わせてショットが伸びると、寄りの速度が
 # 1/尺で落ちるので、長いショットほど画が止まって見える。
 # 30ショット77秒（1カット3.87秒）では、参考4本のどれより遅かった。
 # 行を分けずにショットだけ割れば、合成をやり直さずにカットを増やせる。
 dict(sec='hook', dur=1.4, kind='board', se='impact', head=0.0, hush=0.0,
      fig=('kiku/', 1.00, None),
      board=[dict(text='この草を{燃やすと}', size=118, color=MUSTARD)],
      voice='punch', say='この草な、燃やすとおもろいねん。'),
 dict(dur=1.4, kind='face', face='point', se='pa', tele='{おもろい}ことが起きる'),
 dict(short=True, dur=1.5, kind='stage', scene='q', face='surprise',
      se='reveal', fig=('kiku/', 1.02, None), add='蚊が{ぽとぽと落ちる}',
      say='飛んでる蚊が、ぽとぽと落ちる。'),
 dict(short=True, dur=1.2, kind='board', se='pa', fig=('kiku/', 0.74, None),
      board=[dict(text='{ぽとぽと}', size=126, color=MUSTARD)]),
 dict(short=True, dur=1.5, kind='face', face='point',
      voice='punch', tele='{なんでや}と思う？', say='なんでやと思う？'),

 # ============ 段1：なぜ効くのか（5〜18秒）
 dict(short=True, sec='s1', dur=1.5, kind='face', face='explain',
      tele='この草は{除虫菊}', say='この草は、除虫菊いうねん。'),
 dict(short=True, dur=1.3, kind='board', se='pa', fig=('kiku/', 0.80, None),
      board=[dict(text='{除虫菊}', size=132, color=MUSTARD)]),
 dict(short=True, dur=1.7, kind='board', se='whoosh',
      fig=('pyre/', 1.00, None),
      board=[dict(text='火の熱で', size=104)],
      say='火の熱で、中の成分が気体になる。'),
 dict(short=True, dur=1.6, kind='face', face='explain', se='pa',
      tele='中の成分が{気体}になる'),
 dict(short=True, dur=1.7, kind='stage', scene='s1', face='explain',
      se='reveal', fig=('pyre/', 1.02, None), add='蚊の{神経}に効く',
      say='それが蚊の神経に効いて、飛ばれへんようになる。'),
 dict(short=True, dur=1.9, kind='face', face='surprise', se='pa',
      tele='{飛ばれへん}ようになる'),
 # 裏取りで一番強く出た注意点をここで潰しておく
 dict(short=True, dur=2.1, kind='face', face='serious',
      tele='{煙}でいぶしてるんちゃう', say='煙でいぶしてるんとちゃうで。'),

 # ============ 段2：失敗その1（18〜28秒）粉のままは一瞬で終わる
 dict(short=True, sec='s2', dur=1.5, kind='face', face='point',
      tele='ほな{粉}のまま燃やす？', say='ほな、粉のまま燃やしたらええやん。'),
 dict(short=True, dur=1.2, kind='board', se='pa', fig=('powder/', 0.78, None),
      board=[dict(text='やってみた', size=118)]),
 dict(short=True, dur=1.7, kind='board', se='rise',
      fig=('powder/', 1.00, None),
      board=[dict(text='ぼっと燃えて', size=110)],
      say='やってみたら、ぼっと燃えて、'),
 dict(short=True, dur=1.7, kind='stage', scene='s2', face='surprise',
      se='dodon', flash=True, fig=('powder/', 1.02, None),
      add=dict(text='{一瞬}で終わり', color=CRIMSON),
      voice='punch', say='一瞬で終わり。'),
 dict(short=True, dur=1.5, kind='face', face='explain',
      tele='そこで{練り固めた}', say='そこで、線香に練り込んで固めた。'),
 dict(short=True, dur=1.5, kind='board', se='pa', fig=('stick/', 0.76, None),
      board=[dict(text='線香に{練り込む}', size=104)]),

 # ============ 段3：失敗その2（28〜40秒）棒は40分で消える
 dict(short=True, sec='s3', dur=1.6, kind='board', se='whoosh',
      fig=('stick/', 1.00, None),
      board=[dict(text='{棒}にした', size=116, color=MUSTARD)],
      say='まっすぐな棒。これが最初の形や。'),
 dict(short=True, dur=1.5, kind='face', face='explain', se='pa',
      tele='これが{最初の形}'),
 dict(short=True, dur=1.7, kind='stage', scene='s3', face='explain',
      se='reveal', fig=('stick/', 1.02, None), add='端から{燃えていく}',
      say='端に火をつけたら、ゆっくり燃えていく。'),
 dict(short=True, dur=1.3, kind='face', face='serious', se='pa',
      tele='{ゆっくり}燃えていく'),
 dict(short=True, dur=1.7, kind='board', se='dodon', flash=True,
      fig=('stick/', 1.00, None),
      board=[dict(text='{40分}で消えた', size=112, color=CRIMSON)],
      voice='punch', say='けど、四十分で消えた。'),
 dict(short=True, dur=2.4, kind='face', face='serious',
      tele='夜は{もたへん}', say='これでは、寝てる間もたへん。'),

 # ============ 段4：失敗その3（40〜53秒）長くしたら折れる
 dict(short=True, sec='s4', dur=1.7, kind='face', face='point',
      tele='ほな{長く}したら？', say='ほな、長くしたらええやん。'),
 dict(short=True, dur=1.6, kind='board', se='rise',
      fig=('stickl/', 1.00, None),
      board=[dict(text='長くした', size=110)],
      say='のばした。確かに長持ちする。'),
 dict(short=True, dur=1.3, kind='face', face='explain', se='pa',
      tele='確かに{長持ちする}'),
 dict(short=True, dur=1.7, kind='stage', scene='s4', face='surprise',
      se='dodon', flash=True, fig=('stickl/', 1.02, None),
      add=dict(text='自分の重さで{折れる}', color=CRIMSON),
      voice='punch', say='でも、自分の重さで折れる。'),
 dict(short=True, dur=1.5, kind='face', face='serious', se='pa',
      tele='{折れる}'),
 dict(short=True, dur=1.7, kind='stage', scene='s4', face='serious',
      se='pa', fig=('stickl/', 1.02, None), add='置く{場所}も無い',
      say='まっすぐのままやと、置く場所も無い。'),
 dict(short=True, dur=1.5, kind='face', face='serious',
      tele='{行き詰まった}', say='ここで行き詰まった。'),

 # ============ 段5：解決（53〜65秒）巻く
 dict(short=True, sec='s5', dur=1.6, kind='face', face='explain',
      tele='奥さんが{見た}もの', say='そこで、奥さんがあるもんを見た。'),
 dict(short=True, dur=1.4, kind='board', se='pa',
      board=[dict(text='あるもん', size=126)]),
 dict(short=True, dur=1.9, kind='board', se='whoosh',
      board=[dict(text='とぐろを巻いた\n{ヘビ}', size=112, color=MUSTARD)],
      voice='punch', say='とぐろを巻いた、ヘビや。'),
 dict(short=True, dur=1.6, kind='board', se='rise',
      fig=('coil/', 1.00, None),
      board=[dict(text='{巻いたら}どうなる', size=104)],
      say='長い線を、ぐるぐるに巻いたらどうなる。'),
 dict(short=True, dur=1.4, kind='face', face='point', se='pa',
      tele='長い線を{ぐるぐる}に'),
 dict(short=True, dur=1.6, kind='stage', scene='s5', face='surprise',
      se='reveal', fig=('coil/', 1.02, None), add='同じ場所に{長い線}',
      say='同じ場所に、めちゃくちゃ長い線が収まる。'),
 dict(short=True, dur=1.5, kind='face', face='surprise', se='pa',
      tele='{同じ場所}に収まる'),

 # ============ 答え（65〜73秒）
 dict(short=True, sec='ans', dur=1.4, kind='board',
      fig=('coil/', 0.78, None),
      board=[dict(text='結果', size=132)],
      say='結果。'),
 dict(short=True, dur=2.2, kind='board', se='dodon', flash=True, shake=True,
      hush=0.30, fig=('coil/', 1.00, None),
      board=[dict(text='{7時間}もつ', size=150, color=MUSTARD)],
      voice='punch', say='七時間、もつようになった。'),
 dict(short=True, dur=2.4, kind='stage', scene='ans', face='proud',
      se='reveal', fig=('coil/', 1.02, None),
      add=dict(text='これが{蚊取り線香}', color=MUSTARD),
      voice='punch', say='これが、蚊取り線香や。'),
 dict(dur=1.7, kind='face', face='explain',
      tele='{1902年}・日本で完成', say='千九百二年、日本で完成した形や。'),
 dict(dur=1.8, kind='board', se='pa', fig=('coil/', 0.84, None),
      board=[dict(text='日本で{完成}', size=118, color=MUSTARD)]),

 # ============ 予告（73〜77秒）
 dict(sec='next', dur=1.5, kind='board', fig=('kiku/', 0.70, None),
      board=[dict(text='次は\n{ラクダ}', size=126)],
      say='次はラクダ。'),
 dict(dur=1.6, kind='board', se='reveal', shake=True,
      fig=('pyre/', 0.70, None),
      board=[dict(text='水をためてない', size=122, color=MUSTARD)],
      voice='punch', say='あのコブ、水ちゃうねん。'),
]

# say を持たないショットは読ませない。前の行の声がここへまたがってくる。
# これを付け忘れると voice.lines() が tele を読んでしまい、
# 「間を作るために挟んだカット」が全部しゃべり出して尺が95秒に膨らんだ。
for _s in render.SHOTS:
    if not _s.get('say'):
        _s['mute'] = True

if os.environ.get('SHORT') == '1':
    render.SHOTS = [render.SHOTS[0]] + [x for x in render.SHOTS[1:] if x.get('short')]
    OUT, FRAMES = 'ep06s.mp4', 'frames6s'
    VOICE_FILE, SE_FILE = 'voice6s.wav', 'se6s.wav'
else:
    OUT, FRAMES = 'ep06.mp4', 'frames6'
    VOICE_FILE, SE_FILE = 'voice6.wav', 'se6.wav'

# 章の見出し。向こうは章を出さないが、こちらは「いま何段目か」が
# 分からないと黒板だけの画で迷子になる。段の名前は結論を言わないものにする。
render.CHAPTERS = {'hook': '', 's1': 'なぜ効くのか', 's2': '一度目の失敗',
                   's3': '二度目の失敗', 's4': '三度目の失敗',
                   's5': '', 'ans': '', 'next': ''}
render.DURATION = render.build()
render.OUT = FRAMES

import voice
audio = voice.collect(render.SHOTS)
if audio:
    voice.fit(render.SHOTS, audio)
    render.DURATION = render.build()
    voice.write(VOICE_FILE, render.SHOTS, audio, render.DURATION)
nar = VOICE_FILE if os.path.exists(VOICE_FILE) else None
if nar:
    render.MOUTH_ENV = voice.envelope(nar, render.FPS, render.DURATION)
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep06.txt'))

n = int(render.DURATION * render.FPS)
ansat = [s['t'] for s in render.SHOTS if s.get('sec') == 'ans']
print('尺 %.1f秒 / %dショット / 平均 %.2f秒'
      % (render.DURATION, len(render.SHOTS), render.DURATION / len(render.SHOTS)))
if ansat:
    print('答えを出すのは %.1f秒（尺の%.0f%%）。参考チャンネル4本の中央値は88%%'
          % (ansat[0], 100*ansat[0]/render.DURATION))
ev = sound.se_events()
print('効果音 %d個 / 平均 %.2f秒に1回' % (len(ev), render.DURATION / max(len(ev), 1)))

if '--script' in sys.argv:
    for s in render.SHOTS:
        line = s.get('say') or s.get('tele', '')
        if line and not s.get('mute'):
            print('%5.1fs  %s' % (s['t'], line.replace('{', '').replace('}', '')))
    sys.exit()

os.makedirs(FRAMES, exist_ok=True)
t0 = time.time()
for i in range(n):
    render.render_frame(i / render.FPS).save('%s/%05d.png' % (FRAMES, i))
    if i % 200 == 0:
        print('  %d/%d  %.0fs' % (i, n, time.time()-t0), flush=True)

sound.write_wav(SE_FILE, sound.build_track(render.DURATION))
cmd = [FF, '-y', '-framerate', str(render.FPS), '-i', FRAMES + '/%05d.png', '-i', SE_FILE]
labels, filt, idx = ['[1:a]'], [], 1
if nar:
    idx += 1; cmd += ['-i', nar]; labels.append('[%d:a]' % idx)
if os.path.exists('bgm.mp3'):
    idx += 1; cmd += ['-stream_loop', '-1', '-i', 'bgm.mp3']
    filt.append("[%d:a]extrastereo=m=1.8,volume='%s':eval=frame[b]"
                % (idx, sound.volume_expr(0.64 if nar else 1.0)))
    labels.append('[b]')
mix = ''.join(labels) + 'amix=inputs=%d:duration=first:normalize=0[m]' % len(labels)
lim = '[m]alimiter=limit=0.85:level=disabled:attack=3:release=60[a]'
cmd += ['-filter_complex', ';'.join(filt + [mix, lim]), '-map', '0:v', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
        '-r', str(render.FPS), '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT]
r = subprocess.run(cmd, capture_output=True, text=True)
print('ENCODE', 'OK' if r.returncode == 0 else r.stderr[-900:], flush=True)
if r.returncode == 0:
    print('size %.1f MB' % (os.path.getsize(OUT)/1e6))
