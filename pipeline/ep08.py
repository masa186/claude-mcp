"""第8話「そのフタ、16kgで押さえられてる」TikTok用の20秒

TikTokの実測から作りを決めた（docs/tiktok_plan.md）。

尺
  同じ「平均6.0秒見られた」でも継続率は尺で割り算される。
  43秒で14%、84秒なら7%、20秒なら30%。TikTokは20秒で別に作る。

冒頭
  第5話は0.8秒で実写（埋まり47%）から黒板（埋まり8%）へ落としていて、
  そこが離脱点だった（TikTokが「多くが0:02で停止」と明示）。
  この回は0〜5秒に黒板を出さない。実写と顔だけで持たせる。

型
  参考59本の1位は71.15%の二択型。裏ワザ・方法型は中央値34.7%で、
  ライフスタイル(29.9%)よりテクノロジー(34.8%)が上。
  仕組みを数字で語って、最後に明日使える1行を置く。

保存
  いいね0・シェア0・保存0が本当の詰まりだった。保存されるのは
  「あとで使うもの」。歴史の話には保存する理由が無い。

物理
  力＝大気圧×真空度×面積。径82mm・0.3気圧で16.4kgf。
  この式は材質に依存しないので確かめられる。
  「温めると膨張して開く」は採らない。ソーダ石灰ガラス(9.0e-6)と
  鋼(12e-6)の差は1.3倍しかなく、60度上げても0.015mmにしかならない。
  フタがアルミかブリキかで結論が変わってしまう。

  python3 ep08.py          書き出し
  python3 ep08.py --script ナレーション原稿
"""
import os, sys, time, subprocess
os.environ.setdefault('GEMINI_TTS_MODEL', 'gemini-2.5-flash-preview-tts')
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

render.SHOTS = [
 # ============ つかみ（0〜5秒）黒板は出さない
 # 0秒はフィードのサムネ。画の変化量が最大の10.1秒付近を頭に置く。
 dict(sec='hook', dur=1.6, kind='screen', clip='jaropenV', full=True,
      face='surprise', roll=False, se='impact', head=0.0, hush=0.0,
      voice='punch', tele='力で回したら{あかん}',
      say='このフタ、力で回したらあかん。'),
 dict(dur=2.0, kind='screen', clip='jarV', full=True, face='serious',
      se='don', voice='punch', tele='{16kg}で押さえられてる',
      say='十六キロで押さえられとるからな。'),
 dict(dur=1.4, kind='face', face='point',
      voice='punch', tele='{なんで}か分かる？', say='なんでや思う？'),

 # ============ 仕組み（5〜13秒）
 dict(sec='why', dur=3.0, kind='board', se='pa', fig=('jar/', 0.62, None),
      board=[dict(text='冷えると中は{真空}', size=96)],
      say='熱いまま詰めて、冷めたら中が真空になる。'),
 dict(dur=2.5, kind='board', se='dodon', flash=True, fig=('jar/', 1.02, None),
      board=[dict(text='大気圧が{上から}', size=96, color=MUSTARD)],
      voice='punch', say='そこへ大気圧が、上から押しつけとる。'),
 dict(dur=2.5, kind='board', se='reveal', fig=('jarfix/', 1.02, None),
      board=[dict(text='{空気}を入れるだけ', size=96, color=MUSTARD)],
      say='やることは一つ。空気を入れたるだけや。'),

 # ============ 答え（13〜20秒）実写に戻す
 dict(sec='ans', dur=2.8, kind='screen', clip='jarV', full=True, face='explain',
      se='ton', tele='縁を{少し起こす}',
      say='縁をちょっと起こすか、柄で叩く。'),
 dict(dur=2.2, kind='screen', clip='jaropenV', full=True, face='surprise',
      se='pssh', voice='punch', tele='{ポン}って鳴ったら開く',
      say='ポンって鳴ったら、もう開く。'),
 dict(dur=2.0, kind='face', face='proud',
      voice='punch', tele='{力}やない。{空気}や', say='力やない。空気や。'),
]

for _s in render.SHOTS:
    if not _s.get('say'):
        _s['mute'] = True

OUT, FRAMES = 'ep08.mp4', 'frames8'
VOICE_FILE, SE_FILE = 'voice8.wav', 'se8.wav'

render.STAGGER = 0.13
render.POP = 0.08
render.CARD_ON = True
render.TELOP_SIZE = 104
render.CHAPTERS = {'hook': '', 'why': '', 'ans': ''}
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
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep08.txt'))

n = int(render.DURATION * render.FPS)
board = sum(s['dur'] for s in render.SHOTS if s['kind'] in ('board', 'stage'))
first_board = next((s['t'] for s in render.SHOTS if s['kind'] in ('board', 'stage')), None)
print('尺 %.1f秒 / %dショット' % (render.DURATION, len(render.SHOTS)))
print('黒板 %.1f秒（尺の%.0f%%）／最初に出るのは %.1f秒'
      % (board, 100*board/render.DURATION, first_board))
ev = sound.se_events()
print('効果音 %d個' % len(ev))

if '--script' in sys.argv:
    for s in render.SHOTS:
        line = s.get('say') or ''
        if line:
            print('%5.1fs  %s' % (s['t'], line))
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
