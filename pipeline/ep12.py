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
# 2.5-flash / 2.5-pro とも今日の枠が尽きている（両方 429 を確認）。
# 声は Charon のままだが、第11話までの 2.5-flash とは別モデルなので
# 声質がわずかに変わる。枠が戻ったら 2.5-flash に戻して録り直す。
os.environ.setdefault('GEMINI_TTS_MODEL', 'gemini-3.1-flash-tts-preview')
import imageio_ffmpeg as ie
import render, sound, fig
from render import MUSTARD, CRIMSON
from mkanim import GOLD, HEAT

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

# 図の揺れを止める。数字は止まっていないと読めない。
# 動きが足りないと思って揺らしたが、参考6本を測り直したら
# 向こうの普段の動きは 1.55〜1.91 でこちらの 1.58 と同じだった。
# 違うのは変化の大きさで、揺らして埋まるものではなかった。
fig.LIVE = 0.0

# 図は描き直さない。引数を変えるだけ
F_HOOK = fig.bar([('交通事故', 2547, None), ('お風呂', 19000, HEAT)],
                 unit='人', head='1年で亡くなる人')
F_LIST = fig.steps(['熱すぎる湯', '長風呂', '飲酒後'], head='してはいけない')
# 危ないほうを指すので赤。金色は他の図で「これが答え」に使っている
F_TEMP = fig.versus('41度まで', '42度で\n10分', win='r', head='湯の温度', col=HEAT)
F_TIME = fig.huge('38度', sub='体温がここまで上がる')
F_SUM  = fig.steps(['湯は41度まで', 'つかるのは10分', '飲んだら入らない'],
                   head='これだけ')

render.SHOTS = [
 # ============ フック（0〜4秒）数字を画面いっぱいに置く
 # フラッシュはここでは使わない。apply_flash は頭が一番白いので、
 # 1コマ目が真っ白に飛ぶ。一覧に出るのはその1コマ目で、
 # この回はそこに数字を置くために作っている。白飛びさせたら本末転倒。
 dict(sec='hook', dur=1.8, kind='board', se='impact',
      roll=False, head=0.0, hush=0.0,
      fig=(fig.huge('7.5倍', sub='交通事故より多い', sub_at=0.0), 1.02, None),
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
      fig=(F_TEMP, 1.02, None), tele='{消費者庁}の目安',
      board=[dict(text='目安は{41度まで}', size=104, color=MUSTARD)],
      say='目安は、四十一度まで。'),
 dict(dur=2.2, kind='board', se='dodon', flash=True,
      fig=(F_TIME, 1.02, None),
      board=[dict(text='42度で10分\n{体温38度}', size=104, color=CRIMSON)],
      voice='punch', say='四十二度で、体温が三十八度まで上がる。'),

 # ============ 2つ目 長風呂（12〜17秒）
 dict(sec='s2', dur=1.6, kind='face', face='point',
      se='ton', voice='punch', tele='{2つ目}　長風呂',
      say='二つ目、長風呂。'),
 dict(dur=2.2, kind='face', face='serious',
      tele='つかるのは{10分}まで', say='つかるのは十分まで。'),

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
]

for _s in render.SHOTS:
    if not _s.get('say'):
        _s['mute'] = True

OUT, FRAMES = 'ep12.mp4', 'frames12'
VOICE_FILE, SE_FILE = 'voice12.wav', 'se12.wav'
SE_VOL, NAR_VOL, LUFS = 0.42, 1.0, -12.0

# 顔のカットで画面の84%を横切って振っていた。1.6秒のカットの中で
# カワウソの面積が2.3〜4.3倍に変わる量で、「ドアップで右左に動く意味が
# 分からん」と言われた所。寄りも振りも大きく落とす。
render.FACE_Z, render.FACE_PAN, render.FACE_DRIFT = 1.10, 0.14, 0.0
render.TEXT_Z, render.TEXT_PAN, render.TEXT_DRIFT = 1.06, 0.10, 0.0
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
# 効果音を下げ、声を上げる。実測で、200msごとの音量が中央値より
# 6dB以上大きい区間が 13.9% あった（参考5本の中央値は4.5%）。
# しかも全体は -13.9LUFS と参考(-12.0)より小さい。
# 「効果音がうるさい」と「ナレーションが小さい」が同時に起きていた。
filt = ["[1:a]volume=%.2f[se]" % SE_VOL]
labels, idx = ['[se]'], 1
if nar:
    idx += 1; cmd += ['-i', nar]
    filt.append("[%d:a]volume=%.2f[nar]" % (idx, NAR_VOL))
    labels.append('[nar]')
if os.path.exists('bgm.mp3'):
    idx += 1; cmd += ['-stream_loop', '-1', '-i', 'bgm.mp3']
    filt.append("[%d:a]extrastereo=m=1.8,volume='%s':eval=frame[b]"
                % (idx, sound.volume_expr(0.64 if nar else 1.0)))
    labels.append('[b]')
mix = ''.join(labels) + 'amix=inputs=%d:duration=first:normalize=0[m]' % len(labels)
lim = ('[m]alimiter=limit=0.90:level=disabled:attack=3:release=60[lm];'
       '[lm]loudnorm=I=%.1f:TP=-1.5:LRA=9[a]' % LUFS)
cmd += ['-filter_complex', ';'.join(filt + [mix, lim]), '-map', '0:v', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
        '-r', str(render.FPS), '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT]
r = subprocess.run(cmd, capture_output=True, text=True)
print('ENCODE', 'OK' if r.returncode == 0 else r.stderr[-900:], flush=True)
if r.returncode == 0:
    print('size %.1f MB' % (os.path.getsize(OUT)/1e6))
