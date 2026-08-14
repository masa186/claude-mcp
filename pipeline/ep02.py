"""第2話「飛行機はなぜ飛ぶ」を書き出す。

第1話との違いは、黒板が「スクリーン」になって実写が流れること。
  python3 ep02.py           全部書き出し
  python3 ep02.py --audio   フレームはそのままで音だけ組み直す
  python3 ep02.py --sheet   全ショットの確認シート
"""
import os, sys, time, subprocess, math
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
OUT = 'ep02.mp4'
FRAMES = 'frames2'

render.SHOTS = [
 # ---- フック 0〜2.6
 dict(sec='hook', dur=1.6, kind='face', face='surprise',
      tele='bro、{飛行機ってなんで飛ぶ}？'),
 dict(dur=1.0, kind='title', title='学校の説明\n実は{間違い}'),

 # ---- 実物を見せる 2.6〜6.8
 dict(sec='setup', dur=2.2, kind='screen', clip='plane', face='point',
      tele='これ。今も{どこかで飛んでる}。'),
 dict(dur=2.0, kind='screen', clip='plane2', face='explain', roll=False,
      tele='なんで{何百トンの鉄}が浮く？'),

 # ---- 翼にズーム 6.8〜12.8
 dict(sec='how', dur=1.6, kind='wide', face='point',
      board=['カギは','{翼}だけ'], tele='ここ見て。カギは{翼}。'),
 dict(dur=2.2, kind='screen', clip='wing', face='explain',
      tele='これが翼。'),
 dict(dur=2.2, kind='screen', clip='wing', face='serious', roll=False,
      tele='この板だけで{全部}持ち上げる。'),

 # ---- 間違った説明 12.8〜19.3
 dict(dur=1.5, kind='wide', face='serious',
      board=[dict(text='学校の説明', size=120)], tele='学校ではこう習う。'),
 dict(dur=2.0, kind='board', fig=('10_wing_wrong.png', 1.00, 'pulse:1.2'),
      tele='{上の空気が速くなる}から浮く、と。'),
 dict(dur=1.6, kind='board',
      board=[dict(text='同時に\nゴールしない', size=124, color=CRIMSON)],
      tele='でもこの2つ、{同時に着かない。}'),
 dict(dur=1.4, kind='face', face='explain', tele='つまりこの説明、{成り立たない。}'),

 # ---- 反例 19.3〜22.6
 dict(sec='example', dur=2.2, kind='screen', clip='prop', face='point',
      tele='じゃあこれ、どう説明する？'),
 dict(dur=1.1, kind='title', title='答えは\n{もっと単純}'),

 # ---- 正しい説明 22.6〜29.6
 dict(dur=2.2, kind='board', fig=('11_wing_lift.png', 1.00, 'pulse:0.9'),
      tele='翼は空気を{下に曲げてる}。'),
 dict(dur=1.8, kind='board',
      board=['空気を{下へ}', 'その反作用で{上へ}'],
      tele='下に押した分、{上へ返る}。'),
 dict(dur=1.6, kind='wide', face='arms',
      board=[dict(text='作用・反作用', size=124, color=MUSTARD)],
      tele='ただの{作用・反作用}。'),
 dict(dur=1.4, kind='face', face='explain', tele='だから{背面飛行}でも飛べる。'),

 # ---- オチ 29.6〜34.2
 dict(sec='punch', dur=1.0, kind='title', title='つまり'),
 dict(dur=2.0, kind='board',
      board=[dict(text='空気を\n下に殴ってる', size=150, color=MUSTARD)],
      tele='飛行機は{空気を下に殴ってる}。'),
 dict(dur=1.6, kind='face', face='proud', tele='飛行機、{普通にすごくね？}'),

 # ---- 予告 34.2〜38.4
 dict(sec='next', dur=2.0, kind='wide', face='proud',
      board=['次は','{電子レンジ}'], tele='次は電子レンジ。'),
 dict(dur=2.2, kind='board',
      board=[dict(text='食べ物を\n温めてない', size=132, color=CRIMSON)],
      tele='あれ、{食べ物を温めてない}。'),
]
render.DURATION = render.build()
render.OUT = FRAMES

n = int(render.DURATION * render.FPS)
print('尺 %.1f秒 / %dショット / 平均 %.2f秒'
      % (render.DURATION, len(render.SHOTS), render.DURATION / len(render.SHOTS)))
long = [(i+1, s['dur']) for i, s in enumerate(render.SHOTS) if s['dur'] > 2.3]
print('2.3秒を超えるショット:', long if long else 'なし')

if '--sheet' in sys.argv:
    from PIL import Image
    cols = 6; rows = math.ceil(len(render.SHOTS)/cols); tw, th = 180, 320
    sheet = Image.new('RGB', (cols*tw, rows*th), (24, 26, 24))
    for i, s in enumerate(render.SHOTS):
        im = render.render_frame(s['t'] + s['dur']*0.6).resize((tw-4, th-4), Image.LANCZOS)
        sheet.paste(im, ((i % cols)*tw+2, (i//cols)*th+2))
    os.makedirs(FRAMES, exist_ok=True)
    sheet.save(FRAMES + '/shotsheet.png')
    print(FRAMES + '/shotsheet.png')
    sys.exit()

os.makedirs(FRAMES, exist_ok=True)
AUDIO_ONLY = '--audio' in sys.argv and len(os.listdir(FRAMES)) >= n
t0 = time.time()
for i in range(n if AUDIO_ONLY else 0, n):
    render.render_frame(i / render.FPS).save('%s/%05d.png' % (FRAMES, i))
    if i % 100 == 0:
        print('  %d/%d  %.0fs' % (i, n, time.time()-t0), flush=True)

sound.write_wav('se2.wav', sound.build_track(render.DURATION))

cmd = [FF, '-y', '-framerate', str(render.FPS), '-i', FRAMES + '/%05d.png', '-i', 'se2.wav']
labels, filt, idx = ['[1:a]'], [], 1
if os.path.exists('narration2.wav'):
    idx += 1; cmd += ['-i', 'narration2.wav']; labels.append('[%d:a]' % idx)
if os.path.exists('bgm.mp3'):
    idx += 1; cmd += ['-stream_loop', '-1', '-i', 'bgm.mp3']
    filt.append("[%d:a]volume='%s':eval=frame[b]" % (idx, sound.volume_expr()))
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
