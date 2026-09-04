"""第4話「冷蔵庫は冷やしてない」を書き出す。

3本ぶんの実データで、足し算をやめる。

  第2話 飛行機    継続 60.5%   視聴者役0 / タメ0 / mute0
  第1話 電子レンジ 継続 28.9%   視聴者役4 / タメ4 / mute3
  第3話 ペンギン   継続 20.8%   視聴者役2 / タメ2 / mute3

良かったのは第2話だけで、第2話だけが後から足した仕掛けを1つも
持っていない。実写でも尺でも説明がつかない（第3話は実写ありで
一番短くて一番悪い）。なのでここでは第2話の構成に完全に戻す。

  ・声は1種類だけ。視聴者役を作らない
  ・決め台詞の前の「タメ」を入れない
  ・読まないテロップ（mute）を使わない
  ・0秒は実写＋「9割が勘違いしてる」＋一撃音

変えるのは題材だけ。これで戻れば原因は足した仕掛け、戻らなければ
題材かチャンネルの評価、と切り分けられる。

科学は先に確認した。「冷やしてない」は教育的な言い方としては通るが、
「冷却の定義は温度を下げること」なので厳密には突かれ得る。だから
3秒以内に「熱を外に捨ててる」に着地させて、意味を取り違えられないようにする。

  python3 ep04.py           全部書き出し
  SHORT=1 python3 ep04.py   TikTok用の短縮版
  python3 ep04.py --script  ナレーション原稿を出す
"""
import os, sys, time, subprocess
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

# 冷蔵庫の実写がまだ無い。素材サイトはこの環境から取れない（組織ポリシーで403）。
# 届くまでは黒板で始める。届いたら clips/src9.mp4 に置いて prep_clips.py を
# 走らせれば、ここが実写に変わる。
HAS_CLIP = os.path.isdir('clips/fridge') and os.listdir('clips/fridge')
HOOK = (dict(sec='hook', dur=1.5, kind='screen', clip='fridge', face='surprise',
             roll=False, se='impact', head=0.0,
             voice='punch', tele='{9割が勘違いしてる}',
             say='冷蔵庫、冷やしてへんねん。')
        if HAS_CLIP else
        dict(sec='hook', dur=1.5, kind='stage', scene='cold', face='surprise',
             se='impact', flash=True, shake=True, head=0.0,
             fig=('pump/', 1.02, None), add='冷蔵庫は{冷やしてない}',
             voice='punch', say='冷蔵庫、冷やしてへんねん。'))

render.SHOTS = [
 HOOK,
 # 「冷やしてない」だけで置くと言葉遊びに聞こえる。すぐ着地させる。
 dict(short=True, dur=1.6, kind='stage', scene='cold', face='explain',
      se='reveal', fig=('pump/', 1.02, None), add='熱を外に{捨ててる}',
      voice='punch', say='中の熱を、外に捨ててるだけや。'),

 # ---- 誤解を名指しする
 dict(short=True, sec='how', dur=1.7, kind='face', face='serious',
      tele='{冷気}を作ってる？'),
 dict(short=True, dur=1.8, kind='stage', scene='wrong', face='serious',
      se='reveal', flash=True, fig=('pump/', 1.02, None),
      add=dict(text='{×} 冷たさは作れへん', color=CRIMSON),
      voice='punch', say='冷たさっちゅうもんは、作られへん。'),

 # ---- 身近な例え。実測で40本中の多くが例えを使っていた
 dict(short=True, sec='mizu', dur=1.7, kind='face', face='point',
      tele='{打ち水}したら？'),
 dict(short=True, dur=2.0, kind='stage', scene='mizu', face='explain',
      fig=('pump/', 1.02, None), add='水が{蒸発}すると涼しい',
      say='打ち水したら、涼しなるやろ。'),
 dict(short=True, dur=2.1, kind='stage', scene='mizu', face='explain',
      # 「→」はこのフォントに無くて □ になった。字で書く
      se='reveal', add='液体が気体になると{熱を奪う}',
      voice='punch', say='液体が気体になるとき、熱を奪うねん。'),

 # ---- 本体
 dict(short=True, sec='how2', dur=2.0, kind='stage', scene='pump', face='explain',
      fig=('pump/', 1.02, None), add='管が{熱を拾う}',
      say='冷蔵庫は、それを管の中でやってる。'),
 dict(short=True, dur=2.0, kind='stage', scene='pump', face='explain',
      fig=('pump/', 1.02, None), add='拾った熱を{外へ}',
      say='拾った熱を、そのまま外へ運ぶ。'),

 # ---- 数字と、確かめられる証拠
 dict(short=True, sec='num', dur=1.6, kind='face', face='point',
      tele='だから{裏}が'),
 dict(short=True, dur=1.9, kind='stage', scene='num', face='surprise', se='rise',
      fig=('pumpb/', 1.02, None), add='裏は{40〜50度}',
      voice='punch', say='裏は、四十度から五十度ある。'),
 dict(dur=1.5, kind='face', face='surprise',
      voice='punch', tele='{触ってみ}、熱いから'),

 # ---- オチ
 dict(short=True, sec='punch', dur=2.1, kind='board', se='dodon', flash=True,
      shake=True, hush=0.30, fig=('pump/', 0.86, None),
      board=[dict(text='熱を運び出す\nポンプ', size=132, color=MUSTARD)],
      voice='punch', say='冷蔵庫は、熱を運び出すポンプや。'),
 dict(dur=1.4, kind='face', face='proud', tele='{知らんかったやろ}'),

 # ---- 予告。動物は実測で3.1倍の帯なので、そちらへ寄せる
 dict(sec='next', dur=1.5, kind='board',
      board=[dict(text='次は\n{ラクダ}', size=130)],
      say='次はラクダ。'),
 dict(dur=1.6, kind='board', se='reveal', shake=True,
      board=[dict(text='水をためてない', size=126, color=MUSTARD)],
      voice='punch', say='あのコブ、水ちゃうねん。'),
]

if os.environ.get('SHORT') == '1':
    render.SHOTS = [render.SHOTS[0]] + [x for x in render.SHOTS[1:] if x.get('short')]
    OUT, FRAMES = 'ep04s.mp4', 'frames4s'
    VOICE_FILE, SE_FILE = 'voice4s.wav', 'se4s.wav'
else:
    OUT, FRAMES = 'ep04.mp4', 'frames4'
    VOICE_FILE, SE_FILE = 'voice4.wav', 'se4.wav'

render.CHAPTERS = {'hook': '', 'how': '習ったやつ', 'mizu': '打ち水',
                   'how2': '正体', 'num': '裏を触る', 'punch': '', 'next': ''}
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
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep04.txt'))

n = int(render.DURATION * render.FPS)
print('%s実写: %s' % ('', 'あり' if HAS_CLIP else 'まだ無い（黒板で代用）'))
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
