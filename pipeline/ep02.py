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
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

# tele … 画面に出すテロップ（黒板が主役のショットでは自動で出ない）
# say  … ナレーションだけの台詞。画面には出さない
render.SHOTS = [
 # ---- フック。ここはカワウソを見る時間
 dict(sec='hook', dur=1.8, kind='face', face='surprise', se='don',
      tele='bro、{飛行機ってなんで飛ぶ}？'),
 dict(dur=1.0, kind='title', title='学校の説明\n実は{間違い}'),

 # ---- 疑問を完成させる。「何百トン」だけだと問いが半分で終わる
 dict(sec='setup', dur=2.2, kind='screen', clip='plane', face='point',
      tele='これ、{何百トン}ある。'),
 dict(dur=2.0, kind='screen', clip='plane2', face='explain', roll=False,
      tele='そんな重いのに、{なんで落ちない}？'),

 # ---- 学校の説明。図を読むこと自体が勉強にならないよう、結論だけ置く
 dict(sec='how', dur=2.6, kind='stage', scene='wrong', face='serious',
      fig=('wingrace/', 1.02, 'hold'), add='{同時にゴール}？',
      say='上と下の空気が、後ろで同時に合流する。そう習った。'),
 dict(dur=1.6, kind='stage', scene='wrong', face='serious',
      add=dict(text='× そうはならない', color=CRIMSON),
      say='でも、そうはならない。'),

 # ---- 体の記憶。いきなり腕の話になると迷子になるので、一言で渡す
 dict(sec='example', dur=1.6, kind='face', face='point', se='whoosh',
      tele='じゃあ、{これ}で見て。'),
 dict(dur=2.2, kind='stage', scene='hand', face='explain',
      fig=('hand/', 1.02, 'hold'), add='手を{下}に傾ける',
      say='車の窓から手を出して、手のひらを少し下に傾ける。'),
 dict(dur=2.0, kind='stage', scene='hand', face='explain', beat=True,
      add=dict(text='腕が{上}へ', color=MUSTARD),
      say='そうすると、腕が上にぐっと持っていかれる。'),

 # ---- 橋。手と翼を1枚に並べて、同じことだと目で分からせる
 dict(dur=1.5, kind='face', face='explain', tele='これ、{翼も同じ}。'),
 dict(sec='bridge', dur=2.6, kind='stage', scene='same', face='explain',
      fig=('same/', 1.02, None), add='空気を{下}へ → {上}へ',
      say='どっちも、空気を下に押して、その分だけ上に押し返されてる。'),

 # ---- 本題。原因 → 効果 → 結果 を3段に分けて、1つの舞台の上で積む
 dict(sec='lift', dur=2.0, kind='screen', clip='wing', face='point',
      tele='翼で同じことを、やってみる。'),
 dict(dur=2.0, kind='stage', scene='lift', face='explain',
      fig=('aoa/', 1.02, 'hold'), add='翼 {↗}',
      say='実は翼、ほんの少しだけ上を向いてる。'),
 dict(dur=2.8, kind='stage', scene='lift', face='explain',
      fig=('airflow/', 1.02, None), add='空気 {↓}',
      say='そこに空気が当たると、翼に沿って下へ曲がって出ていく。'),
 dict(dur=2.6, kind='stage', scene='lift', face='proud', beat=True, beat_at=0.5,
      fig=('airlift/', 1.02, None), add=dict(text='翼 {↑}', color=MUSTARD),
      say='空気を下に押した分だけ、翼は上に押し返される。'),
 # 名前は最後につける。先に「揚力とは」から入ると、そこで聞くのをやめる
 dict(dur=2.0, kind='stage', scene='lift', face='proud', se='don',
      add=dict(text='これが{揚力}', color=MUSTARD),
      say='この上向きの力が、揚力。'),

 # ---- オチ。まとめではなく感想で終わる
 dict(sec='punch', dur=1.6, kind='face', face='proud',
      tele='{普通にすごくね？}'),

 # ---- 予告
 dict(sec='next', dur=1.9, kind='wide', face='proud',
      board=['次は','{電子レンジ}'], tele='次は電子レンジ。'),
 dict(dur=2.0, kind='board',
      board=[dict(text='食べ物を\n温めてない', size=130, color=CRIMSON)],
      say='あれ、食べ物を温めてない。'),
]

# 章タイトルは左上に出しっぱなしにする。参考動画はこれで「いまどの話か」を
# 常に示していた。ショットが変わっても迷子にならない。
render.CHAPTERS = {'hook': '', 'setup': 'なんで落ちないのか',
                   'how': '学校の説明', 'example': '手を出してみる',
                   'bridge': '手と翼は同じ', 'lift': 'なぜ浮くのか',
                   'punch': '', 'next': '次回'}
render.DURATION = render.build()
render.OUT = FRAMES

# ---- 声を先に用意する。
# 絵より先に音を決めないと、(1) 尺に収まらない行を早口にするしかなくなり、
# (2) クチパクを波形に合わせられない。順番はここが肝。
import voice
VOICE = 'voice2.wav'
NAR = 'narration2.wav'          # 自分で録ったものがあれば最優先
if os.path.exists(NAR):
    print('声: %s（自分で録ったもの）' % NAR)
    nar = NAR
else:
    audio = voice.collect(render.SHOTS)
    if audio:
        voice.fit(render.SHOTS, audio)          # 収まらない行はショットを伸ばす
        render.DURATION = render.build()        # 伸ばしたぶん位置を計算し直す
        voice.write(VOICE, render.SHOTS, audio, render.DURATION)
    nar = VOICE if os.path.exists(VOICE) else None
if nar:
    render.MOUTH_ENV = voice.envelope(nar, render.FPS, render.DURATION)
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep02.txt'))

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
