"""第5話「冷蔵庫を開けっぱなしにしたら部屋は涼しくなる？」

伸びているショート10本を1本ずつ見せて取った記録（data/design.md）で、
決定的な差が1つ見つかった。

  タイトルの約束が回収されるまでの秒数： 4/11/18/36/42/47/48/48/54/57
  中央値 44.5秒。40秒以降に回収するものが7本。

  こちらの4本は、答えを 1.5〜3.3秒 で出していた。
    飛行機   0秒「翼の形だけで飛んでへん」  → 1.5秒で回収
    電子レンジ 0秒「温めてへん」          → 1.8秒
    ペンギン  0秒「氷とおんなじ温度」      → 3.3秒
    冷蔵庫   0秒「冷やしてへん」          → 2.1秒

答えが2秒で出るなら、残る理由がない。継続が24〜29%（第2話を除く）
だったのはこれが理由だと考えて、ここでは答えを32秒まで引っ張る。

タイトルの型も変えた。471本で測ると、こちらの型は下位だった。
  世界で唯一・幻の  9,366回/日 ／ もし〜たらどうなる 4,308回/日
  実は・仕組み     1,384回/日 ／ なぜ・理由          572回/日 ← 最下位

構成は「もし〜たらどうなる」。説明は3段階（実測で9/10本が3段階）。
0〜2秒に巨大テロップでタイトル全文（実測10/10本）。

第2話の構成は守る（視聴者役なし・タメなし・mute なし）。

  python3 ep05.py           全部書き出し
  SHORT=1 python3 ep05.py   TikTok用の短縮版
  python3 ep05.py --script  ナレーション原稿を出す
"""
import os, sys, time, subprocess
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

# 冷蔵庫の実写がまだ無い（素材サイトはこの環境から取れない）。
# 実測では0〜2秒に実写を出しているのが7/10本。届いたら差し替える。
HAS_CLIP = os.path.isdir('clips/fridge') and os.listdir('clips/fridge')
HOOK = (dict(sec='hook', dur=2.4, kind='screen', clip='fridge', face='surprise',
             roll=False, se='impact', head=0.0,
             voice='punch', tele='{開けっぱなし}で部屋は涼しなる？',
             say='冷蔵庫、開けっぱなしにしたら部屋は涼しなるか。')
        if HAS_CLIP else
        dict(sec='hook', dur=2.4, kind='stage', scene='q', face='surprise',
             se='impact', flash=True, shake=True, head=0.0,
             fig=('pump/', 1.02, None),
             add='{開けっぱなし}で部屋は涼しなる？',
             voice='punch', say='冷蔵庫、開けっぱなしにしたら部屋は涼しなるか。'))

render.SHOTS = [
 HOOK,
 dict(short=True, dur=1.5, kind='face', face='point',
      voice='punch', tele='{どっちやと思う}？'),

 # ---- 段階1。直感のほうを先に肯定して、引っ張る
 dict(short=True, sec='s1', dur=1.9, kind='face', face='explain',
      tele='開けたら{冷たい風}出るやん'),
 dict(short=True, dur=1.8, kind='stage', scene='s1', face='explain',
      se='reveal', fig=('pump/', 1.02, None), add='冷気は{ほんまに出てる}',
      say='あの風は、ほんまに冷たい。'),
 dict(short=True, dur=1.4, kind='face', face='serious', tele='{せやのに}'),

 # ---- 段階2。答えの前に、仕組みそのものを積む。
 # 第4話（冷蔵庫の仕組み）の中身をここへ移した。単体で1本にするより、
 # 答えを引っ張るための「タメ」として使ったほうが効く。
 # 実測の上位10本は、答えを尺の9割あたりまで引っ張っていた。
 dict(short=True, sec='s2', dur=1.7, kind='face', face='point',
      tele='そもそも{冷気}は作れへん'),
 dict(short=True, dur=1.9, kind='face', face='explain',
      tele='{打ち水}したら涼しいやろ'),
 dict(short=True, dur=2.1, kind='stage', scene='s2', face='explain',
      se='reveal', fig=('pump/', 1.02, None),
      add='液体が気体になると{熱を奪う}',
      say='液体が気体になるとき、熱を奪うねん。'),
 dict(short=True, dur=2.0, kind='stage', scene='s2', face='explain',
      fig=('pump/', 1.02, None), add='管が{熱を拾う}',
      say='冷蔵庫は、それを管の中でやってる。'),
 dict(short=True, dur=2.2, kind='stage', scene='s2', face='explain',
      fig=('pump/', 1.02, None), add='庫内の熱を{裏から外へ}',
      say='冷蔵庫は、庫内の熱を裏から外に出してる。'),
 dict(short=True, dur=2.0, kind='stage', scene='s2', face='surprise', se='rise',
      fig=('pumpb/', 1.02, None), add='裏は{40〜50度}',
      voice='punch', say='だから裏は、四十度から五十度ある。'),
 dict(short=True, dur=1.4, kind='face', face='point', tele='{ここまでは}ええな'),

 # ---- 段階3。扉を開けると、その熱はどこへ行くのか
 dict(short=True, sec='s3', dur=2.0, kind='stage', scene='s3', face='serious',
      fig=('pump/', 1.02, None), add='扉を開けたら{どこへ}？',
      say='ほな、扉を開けたら、その熱はどこ行く。'),
 dict(short=True, dur=2.1, kind='stage', scene='s3', face='serious', beat=True,
      se='reveal', flash=True, fig=('pump/', 1.02, None),
      add=dict(text='{同じ部屋}に戻るだけ', color=CRIMSON),
      voice='punch', say='同じ部屋に、戻ってくるだけや。'),
 dict(short=True, dur=1.4, kind='face', face='surprise', tele='{しかも}'),
 dict(short=True, dur=2.1, kind='stage', scene='s3', face='explain',
      se='reveal', fig=('pumpb/', 1.02, None), add='電気のぶんが{上乗せ}',
      say='動かす電気も、ぜんぶ熱になって足される。'),

 # ---- ここで回収。実測の中央値は44.5秒、40秒以降が7/10本
 dict(short=True, sec='ans', dur=1.5, kind='board',
      board=[dict(text='つまり', size=140)],
      say='つまり。'),
 dict(short=True, dur=2.2, kind='board', se='dodon', flash=True, shake=True,
      hush=0.30, board=[dict(text='部屋は\n暑くなる', size=152, color=MUSTARD)],
      voice='punch', say='部屋は、暑くなる。'),
 dict(short=True, dur=2.0, kind='stage', scene='ans', face='explain',
      fig=('pumpb/', 1.02, None), add='広さによるが{1〜3度}',
      say='広さにもよるけど、一度から三度上がる。'),
 dict(dur=1.5, kind='face', face='proud', tele='{逆やってん}'),

 # ---- 予告
 dict(sec='next', dur=1.5, kind='board',
      board=[dict(text='次は\n{ラクダ}', size=130)],
      say='次はラクダ。'),
 dict(dur=1.6, kind='board', se='reveal', shake=True,
      board=[dict(text='水をためてない', size=126, color=MUSTARD)],
      voice='punch', say='あのコブ、水ちゃうねん。'),
]

if os.environ.get('SHORT') == '1':
    render.SHOTS = [render.SHOTS[0]] + [x for x in render.SHOTS[1:] if x.get('short')]
    OUT, FRAMES = 'ep05s.mp4', 'frames5s'
    VOICE_FILE, SE_FILE = 'voice5s.wav', 'se5s.wav'
else:
    OUT, FRAMES = 'ep05.mp4', 'frames5'
    VOICE_FILE, SE_FILE = 'voice5.wav', 'se5.wav'

render.CHAPTERS = {'hook': '', 's1': '冷たい風', 's2': '熱はどこへ',
                   's3': '扉を開けると', 'ans': '', 'next': ''}
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
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep05.txt'))

n = int(render.DURATION * render.FPS)
ansat = [s['t'] for s in render.SHOTS if s.get('sec') == 'ans']
print('実写: %s' % ('あり' if HAS_CLIP else 'まだ無い（黒板で代用）'))
print('尺 %.1f秒 / %dショット / 平均 %.2f秒'
      % (render.DURATION, len(render.SHOTS), render.DURATION / len(render.SHOTS)))
if ansat:
    print('答えを出すのは %.1f秒（尺の%.0f%%）。実測の上位10本は中央値44.5秒'
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
    if i % 100 == 0:
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
