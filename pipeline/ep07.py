"""第7話「48年間、誰も開けられなかった缶詰」

994本＋18本を測って決めた作りで組む（docs/reference.md）。

タイトル
  化け学のふしぎ250本で「◯年間」が入ると1.78倍（741,597 対 416,971）。
  「天才」は0.95倍で効いていなかったので、第6話の「天才的な形」はやめる。
  ゆっくり生き物語110本では「〜してはいけない」が28.25倍だったが、
  この題材には乗らないので、数字＋不可能のほうを使う。

構成
  無限の机の中で、10万回/日超の5本は全部「失敗→改良」を2〜4回やっていて、
  1万回に届かなかった4本は1回もやっていない。5対0。
  裏取りで実在した失敗が4つ見つかったので、そのまま3つ使う。
    分厚くて開かない → 銃で撃つと中身が飛ぶ → てこ式は危険 → 回転刃で完成

尺
  化け学の直近1年で 45〜60秒 396,332回 対 60〜90秒 610,112回（1.54倍）。
  同一チャンネル・同一年の比較。75秒前後を狙う。

画面の埋まり
  参考6本は66〜85%、第6話は30.1%だった。内訳では board が11.6%。
  実写のショットは全画面を使えるので、冒頭と答えに実写を置く。
  黒板の側は render.CARD_ON で図の下に板を敷く。

次回予告
  6本中0本がやっていないので入れない。

  python3 ep07.py           全部書き出し
  SHORT=1 python3 ep07.py   TikTok用の短縮版
  python3 ep07.py --script  ナレーション原稿を出す
"""
import os, sys, time, subprocess
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

render.SHOTS = [
 # ============ つかみ（0〜4.5秒）
 # 0秒はフィードのサムネになる。cans（棚と紙袋）は白っぽくて何の動画か
 # 分からなかったので、缶がぎっしり詰まった cans2 と入れ替えた。
 dict(sec='hook', dur=1.5, kind='screen', clip='cans2V', full=True, face='surprise',
      roll=False, se='impact', head=0.0, hush=0.0,
      voice='punch', tele='{48年間}開けられへん',
      say='これな、四十八年間、開けられへんかってん。'),
 # ここだけ声を置かない。前の行が2.6秒まで伸びて、このショットを覆う。
 # 声の無い1.4秒なので、画のほうで持たせる。cansV は棚を舐めるだけで
 # 手前に瓶が来てしまい、缶に見えなかった。缶を充填している canlineV と
 # 入れ替えた（液が落ちるので動きもある）。
 dict(dur=1.4, kind='screen', clip='canlineV', full=True, face='serious', se='pa',
      tele='{48年間}'),
 dict(short=True, dur=1.6, kind='face', face='point',
      voice='punch', tele='{なんで}か分かる？', say='なんでか分かるか。'),

 # ============ 段1：缶詰が先にできた（4.5〜16秒）
 dict(short=True, sec='s1', dur=1.6, kind='screen', clip='cansV',
      full=True, face='explain', se='whoosh',
      tele='缶詰は{1810年}', say='缶詰ができたんが、千八百十年。'),
 dict(short=True, dur=1.4, kind='board', se='pa', fig=('years/', 0.76, None),
      board=[dict(text='{1810年}', size=126, color=MUSTARD)],
      say='戦争に持っていく食べ物のためや。'),
 dict(short=True, dur=1.5, kind='face', face='explain', se='pa',
      tele='{イギリス海軍}が使うてた', say='イギリスの海軍が使うてた。'),
 dict(short=True, dur=1.8, kind='board', se='tick',
      fig=('years/', 1.00, None),
      board=[dict(text='缶切りは{1858年}', size=104, color=MUSTARD)],
      say='ほんで、缶切りができたんが千八百五十八年。'),
 dict(short=True, dur=1.7, kind='stage', scene='s1', face='surprise',
      se='dodon', flash=True, fig=('years/', 1.02, None),
      add=dict(text='{48年}あいてる', color=CRIMSON),
      voice='punch', say='あいだが、四十八年。'),
 dict(short=True, dur=1.6, kind='face', face='serious',
      tele='中身が先、{開け方}が後', say='中身が先にできて、開け方が後やねん。'),

 # ============ 段2：失敗その1（16〜28秒）叩いても開かない
 # 図は「途中」と「結末」で連番を分ける。ナレーションが結末を言う前に
 # 図が答えを出すと、絵のほうが先にオチを割ってしまう（第6話で踏んだ穴）。
 dict(short=True, sec='s2', dur=1.7, kind='screen', clip='oldcan',
      face='explain', se='whoosh',
      tele='昔の缶は{分厚い鉄}', say='昔の缶は、分厚い鉄でできてた。'),
 dict(short=True, dur=1.8, kind='board', se='clang',
      fig=('thick/', 1.00, None),
      board=[dict(text='{ハンマーとノミ}で', size=100)],
      say='缶に、ハンマーとノミで開けろ、と書いてあった。'),
 dict(short=True, dur=1.5, kind='board', se='clang', fig=('thick/', 1.02, None),
      board=[dict(text='ふちを{ぐるっと}切れ', size=96)],
      say='ふちを、ぐるっと切れと。'),
 dict(short=True, dur=1.5, kind='face', face='surprise', se='pa',
      tele='{道具}は付いてへん', say='道具は付いてへんかった。'),
 dict(short=True, dur=1.8, kind='stage', scene='s2', face='serious',
      se='warn', flash=True, fig=('thick2/', 1.02, None),
      add=dict(text='{開かない}', color=CRIMSON),
      voice='punch', say='それでも、なかなか開かん。'),
 dict(short=True, dur=1.6, kind='face', face='serious',
      tele='兵隊が{怪我}をした', say='兵隊が怪我をするほどやった。'),

 # ============ 段3：失敗その2（28〜37秒）銃で撃つ
 dict(short=True, sec='s3', dur=1.6, kind='face', face='point',
      tele='ほな{撃ったろ}', say='ほな、撃ったろ、いうことになる。'),
 dict(short=True, dur=1.7, kind='screen', clip='rustyV', full=True, face='surprise',
      se='gun', tele='銃剣で刺して、{銃で撃つ}',
      say='銃剣で刺したり、銃で撃ったりした。'),
 dict(short=True, dur=1.4, kind='board', se='gun', fig=('shoot/', 1.00, None),
      board=[dict(text='{石}で叩き割る者も', size=104)],
      say='石で叩き割る者もおった。'),
 dict(short=True, dur=1.8, kind='board', se='gun',
      fig=('shoot2/', 1.00, None),
      board=[dict(text='穴は{開く}', size=110)],
      say='穴は開く。開くけど、'),
 dict(short=True, dur=1.7, kind='stage', scene='s3', face='serious',
      se='warn', flash=True, fig=('shoot2/', 1.02, None),
      add=dict(text='{中身が飛び散る}', color=CRIMSON),
      voice='punch', say='中身が飛び散ってまう。'),

 # ============ 段4：失敗その3（37〜50秒）てこ式の缶切り
 dict(short=True, sec='s4', dur=1.9, kind='board', se='rise',
      fig=('lever/', 1.00, None),
      board=[dict(text='{1858年}やっと', size=108, color=MUSTARD)],
      say='千八百五十八年。やっと缶切りができた。'),
 dict(short=True, dur=1.5, kind='face', face='surprise', se='pa',
      tele='{ウォーナー}が作った', say='アメリカの、ウォーナーが作った。'),
 dict(short=True, dur=1.6, kind='face', face='explain', se='pa',
      tele='刃の形は{銃剣}と同じ', say='刃の形は、銃剣とほぼ同じや。'),
 dict(short=True, dur=1.8, kind='stage', scene='s4', face='surprise',
      se='tear', fig=('lever2/', 1.02, None), add='縁が{ギザギザ}になる',
      say='刃を刺して、ぐいっとこじ開ける。'),
 dict(short=True, dur=1.7, kind='board', se='warn', flash=True,
      fig=('lever2/', 1.00, None),
      board=[dict(text='{危なすぎる}', size=118, color=CRIMSON)],
      voice='punch', say='けど、これが危なすぎた。'),
 dict(short=True, dur=1.8, kind='face', face='serious',
      tele='家では使えず{店員}が開けた',
      say='家では使えん。店の人が開けてくれてた。'),

 # ============ 段5：解決（50〜62秒）回転刃
 dict(short=True, sec='s5', dur=1.7, kind='face', face='point',
      tele='{刺す}んやなくて', say='そこで、刺すんやなくて、'),
 dict(short=True, dur=1.8, kind='board', se='ratchet',
      fig=('wheel/', 1.00, None),
      board=[dict(text='刃を{転がす}', size=112, color=MUSTARD)],
      say='刃を、縁の上で転がしたらどうや。'),
 dict(short=True, dur=1.5, kind='face', face='explain', se='pa',
      tele='ふちに{引っ掛けて}', say='缶のふちに、引っ掛けて。'),
 dict(short=True, dur=1.6, kind='face', face='surprise', se='pa',
      tele='刃が{ふちの上}を走る', say='刃が、ふちの上を走る。'),
 dict(short=True, dur=1.9, kind='stage', scene='s5', face='surprise',
      se='ratchet', fig=('wheel2/', 1.02, None), add='ぐるっと{一周}',
      say='ぐるっと一周、缶を回すだけ。'),

 # ============ 答え（62〜73秒）。参考4本の中央値は尺の88%
 dict(short=True, sec='ans', dur=1.5, kind='board',
      fig=('wheel2/', 0.78, None),
      board=[dict(text='結果', size=132)],
      say='結果。'),
 dict(short=True, dur=2.0, kind='board', se='dodon', flash=True, shake=True,
      hush=0.30, fig=('wheel2/', 1.00, None),
      board=[dict(text='{きれいに開く}', size=136, color=MUSTARD)],
      voice='punch', say='誰でも、きれいに開けられる。'),
 # 実写のプルタブは缶切りではない。ここで「これが今の缶切りの形」と
 # 言うと、答えに出した回転刃と画が食い違う。台詞は黒板の回転刃の上で言う。
 dict(short=True, dur=1.8, kind='board', se='pa', fig=('wheel2/', 1.02, None),
      board=[dict(text='これが{今の缶切り}の形', size=104, color=MUSTARD)],
      voice='punch', say='これが、今の缶切りの形や。'),
 dict(dur=1.9, kind='face', face='explain',
      tele='{1870年}・回転刃の発明', say='千八百七十年、回転刃の発明やった。'),
 dict(dur=1.7, kind='screen', clip='pulltabV', full=True, face='proud',
      se='pssh', tele='今は{片手}でも開く',
      say='今は、片手でも開けられる。'),
 # 締め。参考6本は6本とも次回予告をせず、その回の中で完結していた
 dict(dur=2.0, kind='screen', clip='pulltab2V', full=True, face='proud', se='reveal',
      tele='開け方は{60年}かかって完成した',
      say='開け方が決まるまで、六十年かかってん。'),
 # 声を置かないのは、この最後の1枚と冒頭の1枚だけ。参考1本目も、
 # 黙るのは落ちの絵の上だけだった（書き起こしの[無音]は2回、どちらも落ち）。
 dict(dur=1.7, kind='board', se='dodon', shake=True,
      fig=('years/', 0.86, None),
      board=[dict(text='開け方だけで\n{60年}', size=120, color=MUSTARD)]),
]

# say を持たないショットは読ませない。前の行の声がここへまたがってくる。
for _s in render.SHOTS:
    if not _s.get('say'):
        _s['mute'] = True

if os.environ.get('SHORT') == '1':
    render.SHOTS = [render.SHOTS[0]] + [x for x in render.SHOTS[1:] if x.get('short')]
    OUT, FRAMES = 'ep07s.mp4', 'frames7s'
    VOICE_FILE, SE_FILE = 'voice7s.wav', 'se7s.wav'
else:
    OUT, FRAMES = 'ep07.mp4', 'frames7'
    VOICE_FILE, SE_FILE = 'voice7.wav', 'se7.wav'

# 1ショット1.7秒前後に詰めるので、要素の出し方も詰める。
# 既定（STAGGER 0.40／POP 0.22）だと板の文字が出そろうまで0.62秒かかり、
# カットの頭に「何も無い黒板」が入る。
render.STAGGER = 0.13
render.POP = 0.08
# 図と文字の下に板を敷く。参考6本の画面の埋まりは66〜85%、第6話は30.1%で、
# 内訳では board のショットが11.6%だった。
render.CARD_ON = True

render.CHAPTERS = {'hook': '', 's1': '中身が先にできた', 's2': '一度目の失敗',
                   's3': '二度目の失敗', 's4': '三度目の失敗',
                   's5': '', 'ans': ''}
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
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep07.txt'))

n = int(render.DURATION * render.FPS)
ansat = [s['t'] for s in render.SHOTS if s.get('sec') == 'ans']
print('尺 %.1f秒 / %dショット / 平均 %.2f秒'
      % (render.DURATION, len(render.SHOTS), render.DURATION / len(render.SHOTS)))
if ansat:
    print('答えを出すのは %.1f秒（尺の%.0f%%）。参考4本の中央値は88%%'
          % (ansat[0], 100*ansat[0]/render.DURATION))
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
