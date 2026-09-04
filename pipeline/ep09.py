"""第9話「なぜ兵隊は缶詰を銃で撃っていたのか」

参考4チャンネルの実測を全部載せた回（docs/reference.md, docs/inkya.md）。

■ 題名 ── 陰キャの憧れ707本
    「なぜ」63本 1.77倍 ／「理由」135本 1.65倍  ← 一番強い
    数字を含む 118本 0.89倍 ← 第7話の「48年間」はここで不利側だった
    伸びた10本は全部「人が変なことをしている。なぜか」で人が主語。
    こちらは物が主語で人がいなかった。兵隊を主語に立てる。

■ 尺 ── 陰キャの憧れは61秒超えが0本。本体は25〜35秒（397本・中央値54万）
    第6話79秒・第7話84秒はどちらも1,200回で頭打ちになった。
    さらに第7話は平均視聴0:48で、答えの69.6秒に届くのは推定35%。
    6割が答えを見ずに去っていた。
    ショートは最後まで行くとループし、ループ分も再生時間に数えられる。
      84.2秒で0:48 → 0.57周（一度も完走していない）
      30秒で0:48   → 1.60周（完走扱い）
    YouTube版40秒前後、TikTok版28秒前後の2本に割る。

■ 構成 ── 無限の机18本
    10万回/日超の5本は失敗→改良を2〜4回、1万回未満の4本は0回（5対0）。
    [無音]は全部が段と段の継ぎ目にあり、説明の途中では切れていない。
    → 段の頭に tame=0.3 を置く。

■ 文字の量 ── 化け学のふしぎ／無限の机 6本
    6.21〜9.96 文字/秒、中央値6.59。第7話は6.14。

■ 画面 ── 自分の実測
    埋まりは screen 47% / face 47% / board 8% / stage 12%。
    第5話は0.8秒で黒板に落ちてそこが離脱点だった（TikTokが明示）。
    → 0〜5秒に黒板を出さない。

  python3 ep09.py           YouTube用
  SHORT=1 python3 ep09.py   TikTok用
  python3 ep09.py --script  ナレーション原稿
"""
import os, sys, time, subprocess
os.environ.setdefault('GEMINI_TTS_MODEL', 'gemini-2.5-flash-preview-tts')
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

render.SHOTS = [
 # ============ つかみ（0〜5秒）人の変な行動を先に出す。黒板は出さない
 dict(short=True, sec='hook', dur=1.8, kind='screen', clip='rustyV', full=True,
      face='surprise', roll=False, se='gun', head=0.0, hush=0.0,
      voice='punch', tele='兵隊が缶詰を{銃で撃った}',
      say='なぜ兵隊は、缶詰を銃で撃ってたんか。'),
 dict(short=True, dur=1.6, kind='face', face='point',
      voice='punch', tele='{ふざけてへん}', say='ふざけとるんちゃう。真面目にやってた。'),

 # ============ 段1：缶が開かない（5〜16秒）
 dict(short=True, sec='s1', tame=0.30, dur=1.8, kind='screen', clip='oldcan',
      face='explain', se='whoosh',
      tele='昔の缶は{分厚い鉄}', say='昔の缶は、分厚い鉄でできてた。'),
 dict(short=True, dur=2.0, kind='board', se='clang', fig=('thick/', 1.00, None),
      board=[dict(text='{ハンマーとノミ}で', size=100)],
      say='缶に、ハンマーとノミで開けろ、と書いてあった。'),
 dict(dur=1.5, kind='face', face='surprise', se='pa',
      tele='{道具}は付いてへん', say='道具は付いてへんかった。'),
 dict(short=True, dur=1.8, kind='stage', scene='s1', face='serious',
      se='warn', flash=True, fig=('thick2/', 1.02, None),
      add=dict(text='{開かない}', color=CRIMSON),
      voice='punch', say='それでも、なかなか開かん。'),
 dict(dur=1.6, kind='face', face='serious',
      tele='兵隊が{怪我}をした', say='兵隊が怪我をするほどやった。'),

 # ============ 段2：ほな撃つ（16〜24秒）題名の答え
 dict(short=True, sec='s2', tame=0.30, dur=1.6, kind='face', face='point',
      tele='ほな{撃ったろ}', say='ほな、撃ったろ、いうことになる。'),
 dict(short=True, dur=1.8, kind='board', se='gun', fig=('shoot/', 1.00, None),
      board=[dict(text='穴は{開く}', size=110)],
      say='穴は開く。開くけど、'),
 dict(short=True, dur=1.8, kind='stage', scene='s2', face='serious',
      se='warn', flash=True, fig=('shoot2/', 1.02, None),
      add=dict(text='{中身が飛び散る}', color=CRIMSON),
      voice='punch', say='中身が飛び散ってまう。'),

 # ============ 段3：そもそも48年あいてた（24〜32秒）二の矢。TikTok版では落とす
 # 1行で言うと5.26秒に伸びて画が止まる。第7話で使った台詞2つに割る
 # （どちらもキャッシュ済みなので合成の枠を使わない）。
 dict(sec='s3', tame=0.30, dur=1.8, kind='board', se='pa',
      fig=('years/', 0.76, None),
      board=[dict(text='缶詰は{1810年}', size=104, color=MUSTARD)],
      say='缶詰ができたんが、千八百十年。'),
 dict(dur=2.0, kind='board', se='tick',
      fig=('years/', 1.00, None),
      board=[dict(text='缶切りは{1858年}', size=104, color=MUSTARD)],
      say='ほんで、缶切りができたんが千八百五十八年。'),
 dict(dur=1.8, kind='stage', scene='s3', face='surprise',
      se='dodon', flash=True, fig=('years/', 1.02, None),
      add=dict(text='{48年}あいてる', color=CRIMSON),
      voice='punch', say='あいだが、四十八年。'),
 dict(dur=1.6, kind='face', face='serious',
      tele='中身が先、{開け方}が後', say='中身が先にできて、開け方が後やねん。'),

 # ============ 答え（32〜40秒）
 dict(short=True, sec='ans', tame=0.30, dur=2.2, kind='board', se='ratchet',
      fig=('wheel/', 1.00, None),
      board=[dict(text='刃を{転がす}', size=112, color=MUSTARD)],
      say='刃を転がす缶切りができて、やっと終わった。'),
 dict(short=True, dur=1.8, kind='board', se='dodon', flash=True, shake=True,
      hush=0.30, fig=('wheel2/', 1.00, None),
      board=[dict(text='{きれいに開く}', size=136, color=MUSTARD)],
      voice='punch', say='誰でも、きれいに開けられる。'),
 dict(short=True, dur=2.0, kind='screen', clip='opencanV', full=True,
      face='proud', se='pssh', voice='punch',
      tele='今は{指一本}', say='今は指一本で開く。'),
 dict(short=True, dur=1.8, kind='face', face='proud',
      voice='punch', tele='もう{撃たんでええ}', say='もう、撃たんでええ。'),
]

for _s in render.SHOTS:
    if not _s.get('say'):
        _s['mute'] = True

if os.environ.get('SHORT') == '1':
    render.SHOTS = [x for x in render.SHOTS if x.get('short')]
    OUT, FRAMES = 'ep09s.mp4', 'frames9s'
    VOICE_FILE, SE_FILE = 'voice9s.wav', 'se9s.wav'
else:
    OUT, FRAMES = 'ep09.mp4', 'frames9'
    VOICE_FILE, SE_FILE = 'voice9.wav', 'se9.wav'

render.STAGGER = 0.13
render.POP = 0.08
render.CARD_ON = True
render.TELOP_SIZE = 104
render.CHAPTERS = {'hook': '', 's1': '', 's2': '', 's3': '', 'ans': ''}
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
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep09.txt'))

n = int(render.DURATION * render.FPS)
board = sum(s['dur'] for s in render.SHOTS if s['kind'] in ('board', 'stage'))
fb = next((s['t'] for s in render.SHOTS if s['kind'] in ('board', 'stage')), 0)
ans = next((s['t'] for s in render.SHOTS if s.get('sec') == 'ans'), 0)
import re as _re
chars = sum(len(s.get('say', '')) for s in render.SHOTS)
print('尺 %.1f秒 / %dショット / %d文字 = %.2f文字/秒'
      % (render.DURATION, len(render.SHOTS), chars, chars/render.DURATION))
print('黒板 %.1f秒(%.0f%%) 最初は%.1f秒 / 答えは%.1f秒(%.0f%%) / 0:48で%.2f周'
      % (board, 100*board/render.DURATION, fb, ans, 100*ans/render.DURATION,
         48/render.DURATION))

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
