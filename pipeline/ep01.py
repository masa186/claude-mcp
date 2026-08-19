"""第1話「電子レンジは何を温めてる」を書き出す。

第2話（飛行機）の実データが、どこを直すかを教えてくれた:
  ・43.2%が冒頭で消える。残った56.8%は75%見て、さらにループしている
  → 中身は効いている。弱いのは冒頭だけ。

なので構成は飛行機と同じ骨（誤解 → 否定 → 身近な例え → 因果 → オチ）を
使い、密度だけ上げる。飛行機より濃くするために足したのは3つ:

  1. 図を全部動かす（前は静止画8枚だった。動く図が飛行機の効いた理由）
  2. 「お皿は温まらないはず」という予言を先に置いて、あとで回収する
     飛行機の「逆さまでも飛ぶ」と同じ、確かめられる反証
  3. 24億回という数字。実測で上位120本中50本が数字を入れていた

  python3 ep01.py           全部書き出し
  python3 ep01.py --script  ナレーション原稿を出す
  python3 ep01.py --sheet   全ショットの確認シート
"""
import os, sys, time, subprocess, math
import imageio_ffmpeg as ie
import render, sound
from render import MUSTARD, CRIMSON

FF = ie.get_ffmpeg_exe()
OUT = 'ep01.mp4'
FRAMES = 'frames1'
HERE_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

render.SHOTS = [
 # ---- 冒頭2秒。ここだけが弱点だと実データで分かっている。
 # 飛行機は「実写＋巨大文字＋一撃音」で始めて43.2%に消えられた。
 # 今回は最初の一言を問いではなく断定にして、1秒以内に2回画面を変える。
 # 0秒から図を動かす。伸びているショート21本を測ったら、0秒の時点で
 # 既に何かが動いているのが18本、止まっているのは3本だけだった。
 # 最初これを board（動かない黒板に文字だけ）にしていて、
 # 一番多い項目を外していた。head=0 で声も0秒から出す（20/21がそう）。
 dict(sec='hook', dur=1.1, kind='stage', scene='cold', face='surprise',
      se='dodon', flash=True, shake=True, head=0.0,
      fig=('spin/', 1.02, None), add='電子レンジは{温めてない}',
      voice='punch', say='電子レンジ、温めてへん。'),
 # 台詞を持たないビート。1行目の声はここへまたがる（voice.fit がやる）。
 # この行は「オチの読み方」にしたら声が2.3秒になり、1枚で持たせると
 # 2秒まで一度も画が変わらなくなった。実測では21本中18本が0〜2秒に
 # 1回は切り替えている。文の途中でカットが変わるのは編集としてふつう。
 dict(dur=1.4, kind='board', se='whoosh', fig=('spin/', 1.02, None),
      board=[dict(text='{温めてない}', size=132, color=MUSTARD)]),
 # 1本目の台詞を18文字で書いたら、声に合わせてショットが3.34秒に伸び、
 # 2秒までに一度も切り替わらなくなった。実測は中央値1回。12文字に詰めて、
 # 2つ目の言葉をこちらに回すと、1.5秒あたりで切り替わる。
 dict(dur=1.6, kind='face', face='surprise', se='reveal',
      voice='punch', tele='{食べ物}ちゃうねん'),
 # ここから視聴者役（who='viewer'）。別の声で、テロップも色と位置を変える。
 # 表情は口を閉じたもの（serious）にする。surprise の絵は元から口が開いていて、
 # 別の声が喋っているのに先生が喋っているように見えていた。
 # 読み方を指示で分けると声そのものが別人になってしまったので、
 # だったら初めから別人にする。実測でも41本中20本が2人以上だった。
 dict(dur=1.5, kind='face', face='serious', who='viewer',
      voice='ask', tele='{え、なんで}？', solo=dict(tele='{えっ}てなるやろ')),

 # ---- 誤解を名指しする
 dict(sec='how', dur=1.7, kind='stage', scene='wrong', face='serious',
      fig=('spin/', 1.02, 'hold'), add='中で{火}を使ってる？',
      voice='ask', say='中で火が出てる、と思うやろ。'),
 dict(dur=1.5, kind='stage', scene='wrong', face='serious', beat=True,
      se='reveal', flash=True, fig=('spin/', 1.02, None),
      add=dict(text='{×} 火は使ってない', color=CRIMSON),
      voice='punch', tame=0.45, say='あれ、火もヒーターも使てへん。'),
 # 決め台詞の前に0.45秒のタメを置いたぶん、この行は1枚で3.7秒になった。
 # 台詞のないビートへまたがせて、言い終わりで切り替える。
 dict(dur=1.6, kind='face', face='surprise', se='whoosh',
      mute=True, tele='{火もヒーターも}使てへん'),

 # ---- 本当に起きていること。図は動かす
 dict(sec='what', dur=1.9, kind='stage', scene='wave', face='explain',
      fig=('spin/', 1.02, None), add='出てるのは{電波}',
      say='出てるのは電波や。マイクロ波。'),
 dict(dur=2.0, kind='stage', scene='wave', face='explain',
      se_more=[(0.95, 'whoosh')], add='{水と油}が反応する',
      say='これ、水と油に効くねん。'),

 # ---- 数字。上位120本中50本が数字を入れていた
 dict(sec='num', dur=1.3, kind='face', face='point',
      tele='水の分子が、'),
 dict(dur=2.0, kind='stage', scene='num', face='surprise', se='rise',
      fig=('spin/', 1.02, None), add='1秒に{24億回}',
      say='一秒間に、二十四億回。'),
 dict(dur=1.4, kind='face', face='serious', beat=True, who='viewer',
      voice='ask', tele='{多すぎるやろ}', solo=dict(tele='{多すぎる}')),

 # ---- 因果。ここが密度の山
 dict(sec='heat', dur=1.8, kind='stage', scene='heat', face='explain',
      fig=('bump/', 1.02, None), add='隣と{ぶつかる}',
      say='そんだけ動いたら、隣とぶつかる。'),
 dict(dur=1.9, kind='stage', scene='heat', face='explain', beat=True,
      se='reveal', add=dict(text='こすれて{熱くなる}', color=MUSTARD),
      voice='punch', say='こすれ合って、熱が出るんや。'),

 # ---- 予言を置く。飛行機の「逆さまでも飛ぶ」と同じ確かめられる反証
 dict(sec='test', dur=1.3, kind='face', face='point', se='whoosh',
      voice='ask', tele='ほな{お皿}は？'),
 dict(dur=2.0, kind='stage', scene='plate', face='serious',
      fig=('plate/', 1.02, 'hold'), add='お皿は{水も油も}ない',
      say='お皿には、その水も油もない。'),
 dict(dur=1.7, kind='stage', scene='plate', face='serious', beat=True,
      se='reveal', flash=True, fig=('plate/', 1.02, 'hold'),
      add=dict(text='なら{温まらんはず}', color=CRIMSON),
      voice='punch', tame=0.45, say='ほな、温まらんはずやろ。'),

 # ---- 回収。誰もが経験している矛盾を解く
 dict(sec='ans', dur=1.5, kind='face', face='serious', who='viewer',
      voice='ask', tele='でも{熱いやん}'),
 dict(dur=2.0, kind='stage', scene='ans', face='explain',
      fig=('plate/', 1.02, 'hold'), add='食べ物から{移っただけ}',
      say='あれ、食べ物から熱が移っただけや。'),

 # ---- オチ
 # 一番の山なのに2.1秒まったく動いていなかった（コマ間の変化 0.5）。
 # 揺れは0.22秒しか続かないので、後ろで分子を暴れさせ続ける。
 # 「水を暴れさせてる」と言いながら画が止まっているのが一番おかしい。
 dict(sec='punch', dur=2.1, kind='board', se='dodon', flash=True, shake=True,
      hush=0.30, fig=('spin/', 0.86, None),
      board=[dict(text='水を\n暴れさせてる', size=160, color=MUSTARD)],
      voice='punch', tame=0.45, say='電子レンジは、水を暴れさせてるだけ。'),
 # ここが一番の山。1枚だと4.6秒あった。言い切ったところで引きの画に変える。
 # 引きの画（wide）にすると、この話に1回しか出ない画面の作りになり、
 # 下半分が白い床で空いた。顔の寄りに変える。
 # mute=True は、読まずに字だけ出す指定。声は前の行がまたいでくるので、
 # 決め台詞の途中でカットが変わっても、読む字が画面に残る。
 dict(dur=1.8, kind='face', face='point', se='whoosh',
      mute=True, tele='{暴れさせてる}だけ'),
 # ---- おまけの一撃。数字を出しているのは実測で18/21本、こちらは24億回の
 # 1つだけだった。笑い・軽口があるのも8/21本で、こちらは0だった。
 # 「ポケットのチョコが溶けた」は有名だがピーナッツバー説もあり諸説ある。
 # 溶けた物は断定せず「お菓子」にして、確かな1945年だけ数字で出す。
 dict(sec='bonus', dur=2.4, kind='board', se='reveal', flash=True,
      board=[dict(text='{1945年}\nポケットの\nお菓子が溶けた', size=104)],
      mute=True, say='これ見つかったん、お菓子が溶けたからやで。'),  # TODO 枠が戻ったら mute を外す
 dict(dur=1.4, kind='face', face='serious', who='viewer', viewer_only=True,
      voice='ask', tele='{そんな理由で}？'),
 dict(dur=1.4, kind='face', face='proud',
      voice='ask', tele='{知らんかったやろ}'),

 # ---- 予告。第3話へ。飛行機はもう出しているので、そこには戻さない
 dict(sec='next', dur=1.5, kind='board',
      board=[dict(text='次は\n{冷蔵庫}', size=130)],
      say='次は冷蔵庫。'),
 dict(dur=1.6, kind='board', se='reveal', shake=True,
      board=[dict(text='冷やしてない', size=140, color=MUSTARD)],
      voice='punch', tame=0.45, say='あれ、冷やしてないねん。'),
]

# 視聴者役を別の声にする版は、声を録り直せる日に TWO_VOICES=1 で入れる。
# 今日は新しい3つの台詞の音がまだ無い（TTSは3モデルとも枠切れ）ので、
# 音がある言い方に戻し、ツッコミの1カットは外しておく。
if os.environ.get('TWO_VOICES') != '1':
    render.SHOTS = [x for x in render.SHOTS if not x.get('viewer_only')]
    for x in render.SHOTS:
        x.pop('who', None)
        x.update(x.pop('solo', {}))

render.CHAPTERS = {'hook': '', 'how': '習ったやつ', 'what': '正体',
                   'num': '24億回', 'heat': '熱の正体',
                   'test': 'お皿', 'ans': 'お皿', 'punch': '',
                   'bonus': '', 'next': ''}
render.DURATION = render.build()
render.OUT = FRAMES

import voice
VOICE = 'voice1.wav'
NAR = 'narration1.wav'
if os.path.exists(NAR):
    print('声: %s（自分で録ったもの）' % NAR)
    nar = NAR
else:
    audio = voice.collect(render.SHOTS)
    if audio:
        voice.fit(render.SHOTS, audio)
        render.DURATION = render.build()
        voice.write(VOICE, render.SHOTS, audio, render.DURATION)
    nar = VOICE if os.path.exists(VOICE) else None
if nar:
    render.MOUTH_ENV = voice.envelope(nar, render.FPS, render.DURATION)
    # 視聴者役が喋っているあいだは先生の口を閉じておく。
    # 波形は1本にまとめてあるので、これが無いと誰の声でも口が動く。
    render.MOUTH_MUTE = voice.mouth_mute(render.SHOTS)
voice.dump_text(render.SHOTS, os.path.join(HERE_DOCS, 'narration_ep01.txt'))

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
t0 = time.time()
for i in range(n):
    render.render_frame(i / render.FPS).save('%s/%05d.png' % (FRAMES, i))
    if i % 100 == 0:
        print('  %d/%d  %.0fs' % (i, n, time.time()-t0), flush=True)

sound.write_wav('se1.wav', sound.build_track(render.DURATION))

cmd = [FF, '-y', '-framerate', str(render.FPS), '-i', FRAMES + '/%05d.png', '-i', 'se1.wav']
labels, filt, idx = ['[1:a]'], [], 1
if nar:
    idx += 1; cmd += ['-i', nar]; labels.append('[%d:a]' % idx)
if os.path.exists('bgm.mp3'):
    idx += 1; cmd += ['-stream_loop', '-1', '-i', 'bgm.mp3']
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
