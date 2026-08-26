"""第12話「風呂で死ぬ人は交通事故の7.5倍」

■ 直したい指標
    第7話  視聴を継続 52.7%
    第10話 視聴を継続 44.0%   ← 56%が最初の1秒で消している
    平均視聴/尺は 57.0%→72.7% と直ったが、スワイプ率は手つかずだった。
    この回はフックだけを狙って作る。

■ フックの数字（一次資料）
    入浴中の事故死  年間 約19,000人（消費者庁・東京都健康長寿医療センター）
    交通事故死      2025年 2,547人（警察庁・統計開始以来最少）
    → 7.5倍。1日あたり52人。
    全員が毎日入る。「飛行機の窓の穴」は他人事だったが、これは自分の話。

■ 0秒に何を置くか
    第7話  cans2V（缶がぎっしり）＋数字あり → 52.7%
    第10話 wing（空と翼）＋数字なし・画が平坦 → 44.0%
    実写に頼らず「数字そのもの」を画面いっぱいに置く。
    親指サイズで空や壁は何も言わない。7.5倍なら言う。

■ 中身（消費者庁の注意喚起そのまま）
    湯温は41度以下 ／ つかるのは10分まで ／ 飲酒後は入らない
    42度で10分つかると体温が38度近くまで上がる。

■ 扱いの方針
    人が死ぬ話なので、一次資料の数字と「◯◯を避ける」だけに留める。
    「これで助かる」といった効果の断定はしない。出典は固定コメントに書く。

■ 尺 ── 第10話の実測で較正した見込み
    30秒 約75% ／ 25秒 約78% ／ 20秒 約81%
"""
import os, sys, time, subprocess
os.environ.setdefault('GEMINI_TTS_MODEL', 'gemini-2.5-flash-preview-tts')
import imageio_ffmpeg as ie
import render, sound, fig
from render import MUSTARD, CRIMSON
from mkanim import GOLD, HEAT

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

# 図は描き直さない。引数を変えるだけ
F_HOOK = fig.bar([('交通事故', 2547, None), ('お風呂', 19000, HEAT)],
                 unit='人', head='1年で亡くなる人')
F_LIST = fig.steps(['熱すぎる湯', '長風呂', '飲酒後'], head='してはいけない')
F_TEMP = fig.versus('41度まで', '42度で\n10分', win='r', head='湯の温度')
F_TIME = fig.huge('38度', sub='体温がここまで上がる')
F_SUM  = fig.steps(['湯は41度まで', 'つかるのは10分', '飲んだら入らない'],
                   head='これだけ')

render.SHOTS = [
 # ============ フック（0〜4秒）数字を画面いっぱいに置く
 dict(sec='hook', dur=1.8, kind='board', se='impact',
      roll=False, head=0.0, hush=0.0, flash=True,
      fig=(fig.huge('7.5倍', sub='交通事故より多い'), 1.02, None),
      board=[dict(text='風呂で死ぬ人は', size=104, color=CRIMSON)],
      voice='punch', say='風呂で死ぬ人は、交通事故の七・五倍や。'),
 dict(dur=2.0, kind='board', se='dodon', fig=(F_HOOK, 1.02, None),
      board=[dict(text='年{1万9千人}', size=124, color=CRIMSON)],
      voice='punch', say='年間、一万九千人。'),
 dict(dur=1.6, kind='face', face='serious',
      voice='punch', tele='1日{52人}', say='一日に、五十二人やで。'),

 # ============ 3つ見せる（4〜6秒）
 dict(dur=1.8, kind='board', se='pa', fig=(F_LIST, 1.02, None),
      board=[dict(text='{してはいけない}3つ', size=96, color=MUSTARD)],
      say='してはいけないこと、三つ。'),

 # ============ 1つ目 熱すぎる湯（6〜12秒）
 dict(sec='s1', dur=1.6, kind='face', face='point',
      se='ton', voice='punch', tele='{1つ目}　熱すぎる湯',
      say='一つ目、熱すぎる湯。'),
 dict(dur=2.2, kind='board', se='warn',
      fig=(F_TEMP, 1.02, None),
      board=[dict(text='目安は{41度まで}', size=104, color=MUSTARD)],
      say='消費者庁の目安は、四十一度まで。'),
 dict(dur=2.2, kind='board', se='dodon', flash=True,
      fig=(F_TIME, 1.02, None),
      board=[dict(text='42度で10分\n{体温38度}', size=104, color=CRIMSON)],
      voice='punch', say='四十二度で十分つかると、体温が三十八度近くまで上がる。'),

 # ============ 2つ目 長風呂（12〜17秒）
 dict(sec='s2', dur=1.6, kind='face', face='point',
      se='ton', voice='punch', tele='{2つ目}　長風呂',
      say='二つ目、長風呂。'),
 dict(dur=2.2, kind='face', face='serious',
      tele='つかるのは{10分}まで', say='つかるのは、十分までが目安や。'),
 dict(dur=2.0, kind='face', face='surprise',
      se='warn', voice='punch', tele='急に{立ち上がらない}',
      say='そのあと、急に立ち上がったらあかん。'),

 # ============ 3つ目 飲酒後（17〜22秒）
 dict(sec='s3', dur=1.8, kind='face', face='point',
      se='ton', voice='punch', tele='{3つ目}　飲んだあと',
      say='三つ目、飲んだあとの風呂。'),
 dict(dur=2.2, kind='face', face='serious',
      se='warn', tele='酒で{血圧が下がる}', say='酒で血圧が下がっとる。'),
 dict(dur=2.0, kind='face', face='surprise',
      voice='punch', tele='抜けるまで{入らない}',
      say='抜けるまで、入ったらあかん。'),

 # ============ 締め（22〜26秒）
 # ここが一番大事。ショートは最後まで行くと自動で頭へ戻り、
 # ループぶんも再生時間に数えられる。
 # 「これだけ覚えといて」では戻る理由が無い。冒頭の「1日52人」へ
 # 返して、頭の数字がもう一度意味を持つようにする。
 dict(sec='end', dur=2.0, kind='board', se='reveal',
      fig=(F_SUM, 1.02, None),
      board=[dict(text='この{3つ}だけ', size=116, color=MUSTARD)],
      say='この三つだけ。'),
 dict(dur=2.2, kind='face', face='serious',
      se='dodon', voice='punch', tele='今日、{どれかやってへん}？',
      say='今日、どれかやってへんか。'),
 dict(dur=2.0, kind='board', se='impact', flash=True,
      fig=(fig.huge('52人', sub='今日も、どこかで'), 1.02, None),
      board=[dict(text='1日{52人}', size=120, color=CRIMSON)],
      voice='punch', say='一日、五十二人やからな。'),
]

for _s in render.SHOTS:
    if not _s.get('say'):
        _s['mute'] = True

OUT, FRAMES = 'ep12.mp4', 'frames12'
VOICE_FILE, SE_FILE = 'voice12.wav', 'se12.wav'

render.STAGGER = 0.13
render.POP = 0.08
render.CARD_ON = True
render.TELOP_SIZE = 104
render.CHAPTERS = {'hook': '', 's1': '', 's2': '', 's3': '', 'end': ''}
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
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep12.txt'))

n = int(render.DURATION * render.FPS)
chars = sum(len(s.get('say', '')) for s in render.SHOTS)
D = render.DURATION
print('尺 %.1f秒 / %dショット / %d文字 = %.2f文字/秒'
      % (D, len(render.SHOTS), chars, chars/D))
print('較正後の維持率の見込み %.0f%%'
      % (100 * min(1.0, (67*(1-pow(2.718281828, -D/67)))/D) - 5.5))

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
