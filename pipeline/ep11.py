"""第11話「電子レンジに入れたらあかんもん3選」

同じ形（顔出し無しの解説）888本を数えて決めた。

■ 題材 ── 危ない×家・道具
    危ない   43本 547,060回 3.65倍   ← 最強
    家・道具  46本 442,177回 2.99倍   ← 今までの企画そのもの
    地理・国 235本 204,595回 1.46倍
    体・健康  61本  47,963回 0.27倍
    生き物   80本  29,067回 0.15倍
    掛け算にする。ジャンルは変えず、「危ない」を足すだけ。

■ 型 ── デカデカ!デカボー（開設6ヶ月・102本・登録11.4万・中央160万回）
    伸びた12本が全部「◯◯3選」。尺の中央は82秒。1日1.0本。
      500万 お風呂でしてはいけないこと3選
      489万 捨てるな！無限に増える野菜3選
      474万 実は虫が使われている食べ物3選
    伸びなかったのは生き物・環境系（外来生物3選 9.9万）。

■ こちらにしか無いもの
    他は「危ない」で終わる。こちらは**なぜ危ないかを数字で出す**。
    第8話で16kg、第10話で300kgを実際に計算した。ここが差別化。
      卵    2.7気圧 → 殻の断面14cm2に24kgf
      ぶどう 波長12.2cm が果汁の中で13.6mm に縮み、粒の大きさと共振
      突沸  5度過熱した水100gから 0.93g が一瞬で蒸気になり 1,549mL

■ 裏取り（危ない系は間違えると実害が出るので一次資料だけ）
    卵    NITE 製品安全「ゆで卵の破裂」「生卵の破裂」／国民生活センター
    ぶどう PNAS 2019（Trent大）。電子レンジ12台を壊して実験している
    突沸  NITE 製品安全「インスタントコーヒーを入れて突沸」

  python3 ep11.py           YouTube用
  SHORT=1 python3 ep11.py   TikTok用
  python3 ep11.py --script  ナレーション原稿
"""
import os, sys, time, subprocess
os.environ.setdefault('GEMINI_TTS_MODEL', 'gemini-2.5-flash-preview-tts')
import imageio_ffmpeg as ie
import render, sound, fig
from render import MUSTARD, CRIMSON
from mkanim import GOLD, HEAT

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

# ---- 使い回しの図。引数を渡すだけ。描き直していない
# 丸数字（①②③）は Mplus1-Bold に無く、豆腐（□）になった。
# 図の注釈フォントは GOTHIC＝Mplus1-Bold なので、丸数字は使わない。
F_LIST = fig.steps(['1  卵', '2  ぶどう', '3  温めた飲み物'], head='入れたらあかん')
F_EGG  = fig.huge('24kg', sub='殻を内側から押す力')
F_WAVE = fig.bar([('空気の中', 122, None), ('ぶどうの中', 14, GOLD)],
                 unit='mm', head='電波の波長')
F_BOIL = fig.bar([('元の水', 100, None), ('出てくる蒸気', 1549, HEAT)],
                 unit='mL', head='突沸で飛び出す量')
F_SUM  = fig.steps(['卵は24kgで破裂', 'ぶどうは火花', '飲み物は突沸'],
                   head='入れたらあかん')

render.SHOTS = [
 # ============ つかみ（0〜5秒）
 dict(short=True, sec='hook', dur=2.0, kind='face', face='surprise',
      roll=False, se='impact', head=0.0, hush=0.0,
      voice='punch', tele='レンジに入れたら{あかん}もん',
      say='電子レンジに入れたら、あかんもん三つ。'),
 dict(short=True, dur=1.8, kind='board', se='pa', fig=(F_LIST, 1.02, None),
      board=[dict(text='{3つ}', size=136, color=MUSTARD)],
      say='知らんかったら、たぶんやってる。'),

 # ============ ① 卵（5〜18秒）
 dict(short=True, sec='s1', tame=0.30, dur=1.8, kind='face', face='point',
      se='ton', voice='punch', tele='{1つ目}　卵', say='一つ目、卵。'),
 dict(short=True, dur=2.2, kind='face', face='explain',
      tele='殻の中で{水蒸気}になる', say='中の水が、水蒸気になる。'),
 dict(short=True, dur=2.4, kind='face', face='serious',
      tele='体積が{1700倍}', say='水蒸気になると、体積が千七百倍や。'),
 dict(short=True, dur=2.6, kind='board', se='dodon', flash=True,
      fig=(F_EGG, 1.02, None),
      board=[dict(text='殻に{24キロ}', size=124, color=CRIMSON)],
      voice='punch', say='逃げ場が無いから、殻に二十四キロかかる。'),
 dict(short=True, dur=2.2, kind='face', face='serious',
      tele='{出した後}に破裂する', say='しかも、出した後に破裂することがある。'),

 # ============ ② ぶどう（18〜31秒）
 dict(short=True, sec='s2', tame=0.30, dur=1.8, kind='face', face='point',
      se='ton', voice='punch', tele='{2つ目}　ぶどう', say='二つ目、ぶどう。'),
 dict(short=True, dur=2.2, kind='face', face='surprise',
      tele='2粒並べると{火花}', say='二粒並べると、火花が出る。'),
 dict(short=True, dur=2.6, kind='board', se='warn',
      fig=(F_WAVE, 1.02, None),
      board=[dict(text='波長が{14mm}に縮む', size=96, color=MUSTARD)],
      say='電波はぶどうの中で、波長が十四ミリまで縮む。'),
 dict(short=True, dur=2.4, kind='face', face='explain',
      tele='粒の大きさと{ぴったり}', say='それが、粒の大きさとちょうど合う。'),
 dict(short=True, dur=2.4, kind='face', face='serious',
      se='impact', voice='punch', tele='実験で{12台}壊れた',
      say='研究では、電子レンジが十二台壊れた。'),

 # ============ ③ 突沸（31〜44秒）
 dict(short=True, sec='s3', tame=0.30, dur=2.0, kind='face', face='point',
      se='ton', voice='punch', tele='{3つ目}　温めた飲み物', say='三つ目、温めた飲み物。'),
 dict(short=True, dur=2.4, kind='face', face='explain',
      tele='100度でも{沸かない}', say='レンジは静かに温めるから、百度でも沸かへん。'),
 dict(short=True, dur=2.4, kind='face', face='surprise',
      tele='砂糖を入れた{瞬間}', say='そこへ砂糖を入れた瞬間、'),
 dict(short=True, dur=2.6, kind='board', se='dodon', flash=True, shake=True,
      fig=(F_BOIL, 1.02, None),
      board=[dict(text='{1.5リットル}噴き出す', size=100, color=CRIMSON)],
      voice='punch', say='一気に沸いて、一・五リットルぶん噴き上がる。'),

 # ============ 締め（44〜52秒）
 dict(short=True, sec='end', tame=0.30, dur=2.4, kind='board', se='reveal',
      fig=(F_SUM, 1.02, None),
      board=[dict(text='この{3つ}', size=128, color=MUSTARD)],
      say='卵と、ぶどうと、温めた飲み物。'),
 dict(short=True, dur=2.2, kind='face', face='proud',
      voice='punch', tele='{全部}うちにある', say='全部、うちにあるやつやで。'),
]

for _s in render.SHOTS:
    if not _s.get('say'):
        _s['mute'] = True

if os.environ.get('SHORT') == '1':
    render.SHOTS = [x for x in render.SHOTS if x.get('short')]
    OUT, FRAMES = 'ep11s.mp4', 'frames11s'
    VOICE_FILE, SE_FILE = 'voice11s.wav', 'se11s.wav'
else:
    OUT, FRAMES = 'ep11.mp4', 'frames11'
    VOICE_FILE, SE_FILE = 'voice11.wav', 'se11.wav'

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
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep11.txt'))

n = int(render.DURATION * render.FPS)
board = sum(s['dur'] for s in render.SHOTS if s['kind'] in ('board', 'stage'))
chars = sum(len(s.get('say', '')) for s in render.SHOTS)
print('尺 %.1f秒 / %dショット / %d文字 = %.2f文字/秒'
      % (render.DURATION, len(render.SHOTS), chars, chars/render.DURATION))
print('黒板 %.1f秒(%.0f%%) / 0:48で%.2f周'
      % (board, 100*board/render.DURATION, 48/render.DURATION))

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
