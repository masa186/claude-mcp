"""第10話「なぜ飛行機の窓には、わざと穴が開いているのか」

第7話までで1,200回の天井に2回続けて当たったので、作りを全部入れ替える。

■ 題材の選び方
    「見たことはあるけど、理由を考えたことがない」を狙う。
    缶詰の1810年は他人事だが、あの穴は自分が見たもの。
    陰キャの憧れ707本で伸びた10本は全部「人が変なことをしている。なぜか」。
    ここでは「設計者がわざと穴を開けた」を人の変な行動として立てる。

■ 題名 ── 陰キャの憧れ707本
    「なぜ」63本 1.77倍／数字を含む118本 0.89倍。数字は題名に入れない。

■ 尺 ── 陰キャは61秒超えが0本、本体は25〜35秒（397本・中央値54万）
    第6話79秒・第7話84秒はどちらも1,200回で頭打ち。第7話は答えが83%で、
    平均視聴0:48から逆算すると答えに届くのは35%だった。
    ショートはループ分も再生時間に数えるので、短いほど完走扱いになる。

■ 答えの位置
    題名の問い（なぜ穴か）を尺の5割で返す。残りは「割れたらどうなる」。

■ 裏取り（ねとらぼ／TABIZINE／知力空間）
    客室の窓はガラス3枚。穴は中央の1枚に開いていて、ブリードホールという。
    機内と窓の隙間の気圧を揃えることで、外側のガラスに与圧を受け持たせる。
    巡航中の気圧差 0.52気圧（客室75kPa 対 外22.6kPa。外は地上の1/4.5）。
    23×33cmの楕円で 318kgf。窓80枚で25.5トン。

  python3 ep10.py           YouTube用
  SHORT=1 python3 ep10.py   TikTok用
  python3 ep10.py --script  ナレーション原稿
"""
import os, sys, time, subprocess
os.environ.setdefault('GEMINI_TTS_MODEL', 'gemini-2.5-flash-preview-tts')
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

render.SHOTS = [
 # ============ つかみ（0〜5秒）実写だけ。黒板は出さない
 dict(short=True, sec='hook', dur=2.0, kind='screen', clip='wing', full=True,
      face='surprise', roll=False, se='impact', head=0.0, hush=0.0,
      voice='punch', tele='窓に{小さい穴}',
      say='飛行機の窓、小さい穴が開いてるん知ってるか。'),
 dict(short=True, dur=1.8, kind='face', face='point',
      voice='punch', tele='高度{1万メートル}やで',
      say='高度一万メートルやで。なんで穴開けんねん。'),

 # ============ 段1：かかっている力（5〜11秒）
 dict(short=True, sec='s1', tame=0.30, dur=1.8, kind='screen', clip='plane', full=True,
      face='explain', se='whoosh',
      tele='外の気圧は地上の{4分の1}', say='外の気圧は、地上の四分の一しかない。'),
 dict(short=True, dur=2.0, kind='board', se='dodon', flash=True,
      fig=('win_panes/', 0.80, None),
      board=[dict(text='窓1枚に{300キロ}', size=112, color=MUSTARD)],
      voice='punch', say='窓一枚に、約三百キロかかっとる。'),

 # ============ 段2：3枚ある（11〜16秒）
 dict(short=True, sec='s2', tame=0.30, dur=1.8, kind='board', se='pa',
      fig=('win_panes/', 1.02, None),
      board=[dict(text='ガラスは{3枚}', size=124)],
      say='あの窓、ガラスが三枚ある。'),
 # 黒板が17秒続くと、文字と矢印しか変わらず画が止まる（実測でカット7回）。
 # 顔アップは埋まり47%で黒板とは全く違う画になるので、間に挟んで割る。
 # 声は前の行がまたぐので、合成の枠を使わない。
 dict(short=True, dur=1.2, kind='face', face='surprise', se='pa',
      tele='{3枚}もあるん？'),
 dict(short=True, dur=2.2, kind='board', se='warn',
      fig=('win_nohole/', 1.14, None),
      board=[dict(text='穴が無いと{決まらない}', size=88, color=CRIMSON)],
      say='穴が無かったら、どの一枚が支えとるか決まらへん。'),

 # ============ 答え（16〜23秒）題名の問いをここで返す
 dict(short=True, sec='ans', tame=0.30, dur=2.4, kind='board', se='reveal',
      fig=('win_hole/', 1.02, None),
      board=[dict(text='穴を開けると', size=104, color=MUSTARD)],
      voice='punch', say='そこで中央の一枚に、穴を開けた。'),
 dict(short=True, dur=2.2, kind='board', se='pa',
      fig=('win_hole/', 1.02, None),
      board=[dict(text='中央は{力ゼロ}', size=118, color=MUSTARD)],
      say='中央の窓には、力がかからんようになる。'),
 dict(short=True, dur=1.2, kind='face', face='surprise', se='pa',
      tele='{ゼロ}？'),

 # ============ 落ち（23〜31秒）
 dict(short=True, sec='end', tame=0.30, dur=2.2, kind='board', se='impact',
      flash=True, shake=True, fig=('win_break/', 1.02, None),
      board=[dict(text='外側が{割れても}', size=110, color=CRIMSON)],
      voice='punch', say='やから、外側が割れても、'),
 dict(short=True, dur=2.2, kind='board', se='dodon',
      fig=('win_break/', 1.14, None),
      board=[dict(text='無傷の{中央}が支える', size=92, color=MUSTARD)],
      say='無傷の中央が、そのまま代わりに支える。'),
 dict(dur=1.6, kind='face', face='serious',
      tele='あの穴な、', say='あの穴な、'),
 dict(short=True, dur=2.2, kind='screen', clip='wing', full=True, face='proud',
      se='reveal', voice='punch', tele='{割れる前提}で開けてある',
      say='割れる前提で開けてあんねん。'),
]

for _s in render.SHOTS:
    if not _s.get('say'):
        _s['mute'] = True

if os.environ.get('SHORT') == '1':
    render.SHOTS = [x for x in render.SHOTS if x.get('short')]
    OUT, FRAMES = 'ep10s.mp4', 'frames10s'
    VOICE_FILE, SE_FILE = 'voice10s.wav', 'se10s.wav'
else:
    OUT, FRAMES = 'ep10.mp4', 'frames10'
    VOICE_FILE, SE_FILE = 'voice10.wav', 'se10.wav'

render.STAGGER = 0.13
render.POP = 0.08
render.CARD_ON = True
render.TELOP_SIZE = 104
render.CHAPTERS = {'hook': '', 's1': '', 's2': '', 'ans': '', 'end': ''}
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
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep10.txt'))

n = int(render.DURATION * render.FPS)
board = sum(s['dur'] for s in render.SHOTS if s['kind'] in ('board', 'stage'))
fb = next((s['t'] for s in render.SHOTS if s['kind'] in ('board', 'stage')), 0)
ans = next((s['t'] for s in render.SHOTS if s.get('sec') == 'ans'), 0)
chars = sum(len(s.get('say', '')) for s in render.SHOTS)
print('尺 %.1f秒 / %dショット / %d文字 = %.2f文字/秒'
      % (render.DURATION, len(render.SHOTS), chars, chars/render.DURATION))
print('黒板 %.1f秒(%.0f%%) 最初は%.1f秒 / 答えは%.1f秒(%.0f%%) / 0:48で%.2f周'
      % (board, 100*board/render.DURATION, fb, ans,
         100*ans/render.DURATION, 48/render.DURATION))

if '--script' in sys.argv:
    for s in render.SHOTS:
        if s.get('say'):
            print('%5.1fs  %s' % (s['t'], s['say']))
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
