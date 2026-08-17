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
 # ---- 0〜3秒。実測した人気ショート8本すべてが、ここで実写＋巨大文字＋強い音を
 # 同時に出していた。問いかけではなく、いきなり結論を殴りつける。
 dict(sec='hook', dur=1.5, kind='screen', clip='plane', face='surprise',
      roll=False, se='impact', tele='{9割が勘違いしてる}'),
 dict(dur=1.5, kind='stage', scene='cold', face='serious',
      se='reveal', fig=('invert/', 1.02, None), add='翼の形は{関係ない}',
      say='飛行機、翼の形で飛んでないねん。'),

 # ---- 問い。カットは1〜2秒で切る
 dict(sec='setup', dur=1.5, kind='screen', clip='plane2', face='point',
      se='whoosh', tele='これ{何百トン}ある。'),
 dict(dur=1.4, kind='face', face='surprise', tele='{なんで落ちない}？'),

 # ---- 勘違いを名指しして、すぐ潰す。
 # 40本を数えたら、誤解の否定をやっているのは16本で、うち1〜3秒が10本、
 # 一番長いものでも10秒だった（docs/decide.md）。ここに15秒使っていたのは
 # 明らかに長い。3ショット・約6秒に畳んで、浮いた分をオチと予告に回す。
 dict(sec='how', dur=1.8, kind='stage', scene='wrong', face='serious',
      fig=('wingrace/', 1.02, 'hold'), add='上の空気が{速いから}',
      say='翼の形のおかげ、って習うやろ。'),
 dict(dur=1.5, kind='stage', scene='wrong', face='serious', beat=True,
      se='reveal', flash=True, add=dict(text='{×} これ、ウソ', color=CRIMSON),
      voice='punch', say='あれ、ウソやねん。'),
 dict(sec='proof', dur=1.9, kind='stage', scene='inv', face='surprise',
      se='rise', flash=True, fig=('invert/', 1.02, None), add='{逆さま}でも飛ぶ',
      say='戦闘機、逆さまでも飛ぶやろ。'),

 # ---- 本当の理由
 dict(sec='example', dur=1.2, kind='face', face='point',
      tele='{これ}見て。'),
 # ここは実写にした。もらった素材3本を Gemini に見せて選ばせたところ、
 # 「風で腕が持ち上がる」は線画より実写のほうが伝わる、と出た。
 # clip があるショットには環境音（風）が自動で乗るので、絵と音も揃う。
 dict(dur=1.9, kind='screen', clip='carhand', face='explain',
      se='whoosh', tele='手を{下}に傾ける',
      say='車の窓から手を出して、下に傾ける。'),
 dict(dur=1.6, kind='stage', scene='hand', face='explain', beat=True,
      se='reveal', fig=('hand/', 1.02, None),
      add=dict(text='{腕が上に}！', color=MUSTARD),
      voice='punch', say='腕、上に持ってかれるやろ。'),

 # ---- 橋。ここで実写の翼を1.2秒だけ差し込んで視覚を変える
 dict(sec='bridge', dur=1.2, kind='screen', clip='wing', face='point',
      se='whoosh', tele='飛行機の{翼}も、'),
 dict(dur=2.0, kind='stage', scene='same', face='explain',
      fig=('same/', 1.02, None), add='{これと全く同じ}',
      say='これと全く同じ。形やない、傾きや。'),
 # 上の台詞の後半「形やない、傾きや」はこのカットに乗る。
 # 1枚の絵で5秒持たせるより、言葉の切れ目でカットを割るほうが見やすい。
 # 台詞を持たないショットなので、voice.fit がここまで声をまたがせてくれる。
 dict(dur=1.1, kind='stage', scene='same', face='serious', se='reveal',
      add=dict(text='形やない、{傾き}', color=MUSTARD)),

 # ---- 因果を3段。1.5〜2秒で切る
 dict(sec='lift', dur=1.5, kind='stage', scene='lift', face='explain',
      fig=('aoa/', 1.02, 'hold'), add='翼は{上向き}',
      say='翼はほんの少し上向き。'),
 # 空気が流れ出したあとも音が続くように、途中でもう一発入れる。
 # ここは絵が動いているのに無音に近いと、目と耳がばらばらに感じる。
 dict(dur=2.0, kind='stage', scene='lift', face='explain',
      fig=('airflow/', 1.02, None), add='空気を{下}に押す',
      se_more=[(0.95, 'whoosh')], shake=True,
      say='当たった空気を下に押し返す。'),
 # ここだけ3行。上向き→下に押す→上へ の3つが並んでいること自体が説明の
 # 中身なので、2行にすると話の筋が画面から消える。
 dict(dur=1.9, kind='stage', scene='lift', face='proud', stack=3,
      se='rise', fig=('airlift/', 1.02, None),
      se_more=[(1.05, 'reveal')],
      add=dict(text='翼は{上}へ', color=MUSTARD),
      say='その分だけ、翼は上に持ち上がる。'),

 # ---- オチ
 # 「つまり」の暗転は外した。翼が持ち上がった勢いのまま結論へ直結させる。
 # 動画を見せたら、ここの1.5秒で「終わった」と錯覚して離脱すると指摘された。
 dict(sec='punch', dur=2.0, kind='board', se='dodon', flash=True, hush=0.30,
      board=[dict(text='空気を\n下に殴ってる', size=160, color=MUSTARD)],
      voice='punch', say='飛行機は、空気を下に殴って飛んでる。'),
 dict(dur=1.4, kind='face', face='proud', tele='{普通にすごくね？}'),

 # ---- 予告。問いを残して終える
 dict(sec='next', dur=1.5, kind='board',
      board=[dict(text='次は\n{電子レンジ}', size=130)],
      say='次は電子レンジ。'),
 dict(dur=1.6, kind='board', se='reveal', shake=True,
      board=[dict(text='食べ物を\n温めてない', size=130, color=CRIMSON)],
      voice='punch', say='あれ、食べ物を温めてない。'),
 dict(dur=1.6, kind='face', face='surprise',
      voice='punch', tele='{じゃあ何温めてる}？'),
]

# 章タイトルは左上に出しっぱなしにする。参考動画はこれで「いまどの話か」を
# 常に示していた。ショットが変わっても迷子にならない。
# 章タイトルは短く。読ませるものではなく、いまどの話かの目印
render.CHAPTERS = {'hook': '', 'setup': '', 'how': '習ったやつ',
                   'proof': '逆さま', 'example': '車の窓',
                   'bridge': '手と翼', 'lift': '翼', 'punch': '', 'next': ''}
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
    # 動画を見せたら「BGMが小さくて疾走感が出ていない」と言われた。
    # ナレーションを邪魔しない範囲で少し上げる。
    # 声も効果音もモノラルなので、そのまま混ぜると全体の左右差が3%しかなく
    # 「BGMがモノラル」と聞こえる。BGMだけ広げると、真ん中に声、両脇に音楽、
    # という置き方になって、音量を上げずに聞き取りやすさが上がる。
    filt.append("[%d:a]extrastereo=m=1.8,volume='%s':eval=frame[b]"
                % (idx, sound.volume_expr(0.64 if nar else 1.0)))
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
