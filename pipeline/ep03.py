"""第3話「ペンギンの足はなぜ凍らないか」を書き出す。

第1話と第2話の実データが、どこを直すかを教えてくれた。

  第2話 飛行機    0秒＝実写＋「9割が勘違いしてる」  冒頭離脱 43.2%
  第1話 電子レンジ 0秒＝黒板（暗い）＋断定          冒頭離脱 71.1%

TikTokは両方に「多くの視聴者が0:02で視聴を停止」と出した。
20本の1コマ目の実測は 実写13/20・明るい16/20・「9割」系8/20（1位）。
第2話は3つとも満たし、第1話は3つとも外していた。第1話は効いていた型を
捨てていた。ここでは第2話の型に戻す。

題材を動物にしたのも実データ。471本を分けた1日あたり再生数の中央値は
動物4,911回に対して仕組み・科学1,567回で、3.1倍ある。カワウソの先生と
いうキャラとも矛盾しない。

科学の確認は先に済ませてある。言ってはいけない言い切りが3つある:
  ・血に凍らない成分が入っている（ペンギンでは確認されていない）
  ・足は常に温かい（逆。0〜5度に保っている）
  ・絶対に凍傷にならない（動けなくなれば凍る）

  python3 ep03.py           全部書き出し
  python3 ep03.py --script  ナレーション原稿を出す
"""
import os, sys, time, subprocess, math
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
OUT = 'ep03.mp4'
FRAMES = 'frames3'
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

render.SHOTS = [
 # ---- 0〜2秒。ここだけが弱点だと2本ぶんの実データで分かっている。
 # 実写・明るい・「9割」系の3つを同時に置く。第2話と同じ型。
 dict(sec='hook', dur=1.2, kind='screen', clip='peng2', face='surprise',
      roll=False, se='impact', head=0.0,
      voice='punch', tele='{9割が知らない}',
      say='ペンギンの足、氷とおんなじ温度やねん。'),
 # 台詞を持たないビート。1行目の声はここへまたがる。
 # 1行目は声にすると3.2秒あり、1枚で持たせると3秒まで画が変わらない。
 # 第1話でこれをやって冒頭離脱71.1%だった。実測では21本中18本が
 # 0〜2秒に1回は切り替えている。ここは別の実写に切り替える。
 dict(dur=2.1, kind='screen', clip='peng', se='whoosh',
      mute=True, tele='{氷とおんなじ}温度'),
 dict(dur=1.4, kind='face', face='surprise', se='reveal',
      voice='punch', tele='{0度}やで'),
 dict(dur=1.4, kind='face', face='serious', who='viewer',
      voice='ask', tele='{え、凍らへんの}？'),

 # ---- 誤解を名指しする
 dict(sec='how', dur=1.9, kind='stage', scene='wrong', face='serious',
      fig=('rete0/', 1.02, None), add='血が{凍らへん成分}？',
      voice='ask', say='凍らん成分が入ってる、と思うやろ。'),
 dict(dur=1.6, kind='stage', scene='wrong', face='serious', beat=True,
      se='reveal', flash=True, fig=('rete0/', 1.02, None),
      add=dict(text='{×} そんなもんは無い', color=CRIMSON),
      voice='punch', tame=0.45, say='そんなもんは入ってへん。'),

 # ---- 実写にもう一度戻す。抽象だけで持たせない
 dict(sec='what', dur=1.7, kind='screen', clip='peng4', face='explain',
      se='whoosh', tele='足は{ほんまに冷たい}'),

 # ---- 仕組み。ここが山
 dict(dur=2.0, kind='stage', scene='rete', face='explain',
      fig=('rete/', 1.02, None), add='足の付け根で{熱を渡す}',
      say='足の付け根で、熱を渡してんねん。'),
 dict(dur=2.0, kind='stage', scene='rete', face='explain',
      fig=('rete/', 1.02, None), add='{行き}が{帰り}を温める',
      say='足へ行く温かい血が、戻る冷たい血を温め直す。'),
 # この行は1枚で4.7秒あった。台詞を持たないビートへまたがせて割る
 dict(dur=2.0, kind='face', face='explain', se='whoosh',
      mute=True, tele='{温め直して}から帰す'),

 # ---- 数字。上位120本中50本が数字を入れていた
 dict(sec='num', dur=1.3, kind='face', face='point',
      tele='からだは{38度}'),
 dict(dur=1.7, kind='stage', scene='num', face='surprise', se='rise',
      fig=('rete/', 1.02, None), add='足は{0度}',
      voice='punch', say='足は、ゼロ度。'),
 dict(dur=1.3, kind='face', face='surprise', who='viewer',
      voice='ask', tele='{差ありすぎ}'),

 # ---- 反証。渡さなかったらどうなるか
 dict(sec='test', dur=1.9, kind='stage', scene='cold', face='serious',
      fig=('rete0/', 1.02, None), add='渡さんかったら？',
      voice='ask', say='もし熱を渡さんかったら？'),
 dict(dur=1.9, kind='stage', scene='cold', face='serious', beat=True,
      se='reveal', flash=True, fig=('rete0/', 1.02, None),
      add=dict(text='{体温}が逃げる', color=CRIMSON),
      voice='punch', say='冷たい血がそのまま帰って、体温が逃げる。'),

 # ---- オチ
 dict(sec='punch', dur=2.1, kind='board', se='dodon', flash=True, shake=True,
      hush=0.30, fig=('rete/', 0.86, None),
      board=[dict(text='わざと\n冷たいまま', size=150, color=MUSTARD)],
      voice='punch', tame=0.45,
      say='ペンギンは、足をわざと冷たいままにしてる。'),
 dict(dur=1.7, kind='screen', clip='peng2', face='proud', se='whoosh',
      mute=True, tele='{わざと}冷たいまま'),
 dict(dur=1.4, kind='face', face='proud',
      voice='ask', tele='{知らんかったやろ}'),

 # ---- 予告
 dict(sec='next', dur=1.5, kind='board',
      board=[dict(text='次は\n{冷蔵庫}', size=130)],
      say='次は冷蔵庫。'),
 dict(dur=1.6, kind='board', se='reveal', shake=True,
      board=[dict(text='冷やしてない', size=140, color=MUSTARD)],
      voice='punch', say='あれ、冷やしてないねん。'),
]

if os.environ.get('TWO_VOICES') != '1':
    render.SHOTS = [x for x in render.SHOTS if not x.get('viewer_only')]
    for x in render.SHOTS:
        x.pop('who', None)
        x.update(x.pop('solo', {}))

render.CHAPTERS = {'hook': '', 'how': '習ったやつ', 'what': '正体',
                   'rete': '熱の受け渡し', 'num': '38度と0度',
                   'test': 'もし渡さんかったら', 'punch': '', 'next': ''}
render.DURATION = render.build()
render.OUT = FRAMES

import voice
VOICE = 'voice3.wav'
audio = voice.collect(render.SHOTS)
if audio:
    voice.fit(render.SHOTS, audio)
    render.DURATION = render.build()
    voice.write(VOICE, render.SHOTS, audio, render.DURATION)
nar = VOICE if os.path.exists(VOICE) else None
if nar:
    render.MOUTH_ENV = voice.envelope(nar, render.FPS, render.DURATION)
    render.MOUTH_MUTE = voice.mouth_mute(render.SHOTS)
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep03.txt'))

n = int(render.DURATION * render.FPS)
print('尺 %.1f秒 / %dショット / 平均 %.2f秒'
      % (render.DURATION, len(render.SHOTS), render.DURATION / len(render.SHOTS)))
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
    if i % 100 == 0:
        print('  %d/%d  %.0fs' % (i, n, time.time()-t0), flush=True)

sound.write_wav('se3.wav', sound.build_track(render.DURATION))

cmd = [FF, '-y', '-framerate', str(render.FPS), '-i', FRAMES + '/%05d.png', '-i', 'se3.wav']
labels, filt, idx = ['[1:a]'], [], 1
if nar:
    idx += 1; cmd += ['-i', nar]; labels.append('[%d:a]' % idx)
if os.path.exists('bgm.mp3'):
    idx += 1; cmd += ['-stream_loop', '-1', '-i', 'bgm.mp3']
    filt.append("[%d:a]extrastereo=m=1.8,volume='%s':eval=frame[b]"
                % (idx, sound.volume_expr(0.64 if nar else 1.0)))
    labels.append('[b]')
print('音: 効果音' + ('＋声(%s)' % nar if nar else '') +
      ('＋BGM' if os.path.exists('bgm.mp3') else ''), flush=True)
mix = ''.join(labels) + 'amix=inputs=%d:duration=first:normalize=0[m]' % len(labels)
lim = '[m]alimiter=limit=0.85:level=disabled:attack=3:release=60[a]'
cmd += ['-filter_complex', ';'.join(filt + [mix, lim]), '-map', '0:v', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
        '-r', str(render.FPS), '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT]

r = subprocess.run(cmd, capture_output=True, text=True)
print('ENCODE', 'OK' if r.returncode == 0 else r.stderr[-900:], flush=True)
if r.returncode == 0:
    print('size %.1f MB' % (os.path.getsize(OUT)/1e6))
