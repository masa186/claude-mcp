"""第2話「飛行機はなぜ飛ぶ」を書き出す。

前の版は「空気を下に曲げる → 作用・反作用 → 揚力」と言葉で繋いでいたが、
それだと『で？なんで機体が上がるの？』が残る。
今回は、視聴者が体で知っている「車の窓から手を出すと腕が持っていかれる」を
先に見せてから翼に戻す。因果はここで繋がる。

  python3 ep02.py           全部書き出し
  python3 ep02.py --audio   フレームはそのままで音だけ組み直す
  python3 ep02.py --sheet   全ショットの確認シート
  python3 ep02.py --script  ナレーション原稿を出す
"""
import os, sys, time, subprocess, math
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
OUT = 'ep02.mp4'
FRAMES = 'frames2'

# tele … 画面に出すテロップ（黒板が主役のショットでは自動で出ない）
# say  … ナレーションだけの台詞。画面には出さない
render.SHOTS = [
 # ---- フック
 dict(sec='hook', dur=1.8, kind='face', face='surprise', se='don',
      tele='bro、{飛行機ってなんで飛ぶ}？'),
 dict(dur=1.0, kind='title', title='学校の説明\n実は{間違い}'),

 # ---- 実物
 dict(sec='setup', dur=2.2, kind='screen', clip='plane', face='point',
      tele='これ、{何百トン}ある。'),
 dict(dur=1.8, kind='screen', clip='plane2', face='explain', roll=False,
      tele='それが浮いてる。'),

 # ---- 学校の説明は成り立たない
 dict(sec='how', dur=1.4, kind='wide', face='serious',
      board=[dict(text='学校の説明', size=118)], tele='学校ではこう習う。'),
 # 図を止めたまま置くと「矢印がある」としか読めなかったので、
 # 上下の空気を実際に走らせて、着かないところまで見せる
 dict(dur=2.4, kind='board', fig=('wingrace/', 1.15, None),
      board=[dict(text='上と下、同時に着く？', size=94)],
      say='上と下に分かれた空気が、後ろで同時に出会うから浮く、と。'),
 dict(dur=1.5, kind='board',
      board=[dict(text='実際は\n上が先に着く', size=124, color=CRIMSON)],
      say='実際は、上のほうが先に着く。'),
 dict(dur=1.3, kind='face', face='explain', tele='この説明、{成り立たない}。'),

 # ---- ここで体の記憶に繋げる（前の版で抜けていたところ）
 dict(sec='example', dur=1.9, kind='face', face='point', se='whoosh',
      tele='{車の窓}から手、出したことある？'),
 dict(dur=1.6, kind='board',
      board=[dict(text='手を{下}に傾ける', size=112)],
      say='手のひらを、少し下に傾ける。'),
 dict(dur=1.7, kind='board', beat=True,
      board=[dict(text='腕が{上}に\n持っていかれる', size=120, color=MUSTARD)],
      say='そうすると、腕が上にぐっと持っていかれる。'),
 dict(dur=1.4, kind='face', face='explain', tele='{あれと同じ}ことしてる。'),

 # ---- 翼に戻す
 dict(dur=2.0, kind='screen', clip='wing', face='point',
      tele='翼も、やってることは同じ。'),
 # 「なぜ空気が下に曲がるのか」を飛ばすと、次の反作用が宙に浮く
 dict(dur=1.6, kind='board',
      board=[dict(text='翼は少し\n上を向いてる', size=118)],
      say='翼は、ほんの少しだけ上を向いている。'),
 dict(dur=2.4, kind='board', fig=('airflow/', 1.15, None),
      board=[dict(text='空気が{下}へ曲がる', size=104)],
      say='ぶつかった空気は、翼に沿って下へ曲がって出ていく。'),
 dict(dur=2.4, kind='board', fig=('airlift/', 1.15, None), beat=True, beat_at=0.6,
      board=[dict(text='だから翼は{上}へ', size=104, color=MUSTARD)],
      say='空気を下に押した分だけ、翼は上に押し返される。'),
 dict(dur=1.7, kind='board',
      board=['空気を{下へ}', '翼が{上へ}'],
      say='空気が下、翼が上。'),

 # ---- オチ
 dict(sec='punch', dur=1.6, kind='face', face='proud', se='don',
      tele='これが{揚力}。'),
 dict(dur=1.0, kind='title', title='つまり'),
 dict(dur=2.0, kind='board',
      board=[dict(text='空気を\n下に殴ってる', size=148, color=MUSTARD)],
      say='飛行機は、空気を下に殴って進んでる。'),
 dict(dur=1.5, kind='face', face='proud', tele='{普通にすごくね？}'),

 # ---- 予告
 dict(sec='next', dur=1.9, kind='wide', face='proud',
      board=['次は','{電子レンジ}'], tele='次は電子レンジ。'),
 dict(dur=2.0, kind='board',
      board=[dict(text='食べ物を\n温めてない', size=130, color=CRIMSON)],
      say='あれ、食べ物を温めてない。'),
]
render.DURATION = render.build()
render.OUT = FRAMES

n = int(render.DURATION * render.FPS)
print('尺 %.1f秒 / %dショット / 平均 %.2f秒'
      % (render.DURATION, len(render.SHOTS), render.DURATION / len(render.SHOTS)))
long = [(i+1, s['dur']) for i, s in enumerate(render.SHOTS) if s['dur'] > 2.4]
print('2.4秒超のショット:', long if long else 'なし')
ev = sound.se_events()
print('効果音 %d個 / 平均 %.2f秒に1回' % (len(ev), render.DURATION / max(len(ev), 1)))

if '--script' in sys.argv:
    for s in render.SHOTS:
        line = s.get('say') or s.get('tele', '')
        if line:
            print('%5.1fs  %s' % (s['t'], line.replace('{', '').replace('}', '')))
    sys.exit()

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

# 自分で録った narration2.wav があればそれを使う。無ければ合成する。
import voice
if '--voice' in sys.argv or not os.path.exists('voice2.wav'):
    voice.build('voice2.wav')
nar = sound.narration_path('narration2.wav', 'voice2.wav')

cmd = [FF, '-y', '-framerate', str(render.FPS), '-i', FRAMES + '/%05d.png', '-i', 'se2.wav']
labels, filt, idx = ['[1:a]'], [], 1
if nar:
    idx += 1; cmd += ['-i', nar]; labels.append('[%d:a]' % idx)
if os.path.exists('bgm.mp3'):
    idx += 1; cmd += ['-stream_loop', '-1', '-i', 'bgm.mp3']
    # 声が乗るぶんBGMを下げる。ここを下げないと台詞が埋もれる
    filt.append("[%d:a]volume='%s':eval=frame[b]"
                % (idx, sound.volume_expr(0.55 if nar else 1.0)))
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
