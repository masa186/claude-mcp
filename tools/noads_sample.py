"""ベリティの動画の最強版（docs/noads/best.md）の見本動画を作る。

    python3 tools/noads_sample.py <元の noads.mp4> <ナレーションの wav> <作業フォルダ> <出力.mp4>

- 切り方・字幕の秒は tools/noads_cut.py の SEG / LINES を使う
- 最初の区間の速さは、ナレーションの長さに合わせて決める（0.7秒の元の画をナレーションの長さに伸ばす）
- 文字は PIL で透明な PNG に描き、ffmpeg で重ねる
- ナレーションの声は仮（Open JTalk）。本番は VOICEVOX 四国めたんに差し替える
"""
import os, sys, subprocess, json
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noads_cut

SRC, NARR, WORK, OUT = sys.argv[1:5]
os.makedirs(WORK, exist_ok=True)
FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
W, H = 720, 1280

narr_dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', NARR],
                                capture_output=True, text=True).stdout)
seg = list(noads_cut.SEG)
if getattr(noads_cut, 'FIT_FIRST', True):
    a0, b0, _, what0 = seg[0]
    seg[0] = (a0, b0, (b0 - a0) / narr_dur, what0)
    noads_cut.SEG[:] = seg
ZOOM = getattr(noads_cut, 'ZOOM_FIRST', True)
DUCK = getattr(noads_cut, 'DUCK', False)
total = sum((b - a) / sp for a, b, sp, _ in seg)
FREEZE = noads_cut.FREEZE

# 文字の表（新しい秒）。最初のナレーションは2つに割り、「世界が消えます」を赤にする
cut1 = narr_dur * 0.36
texts = [('narr', 0.0, cut1, '3秒後、', 'white'), ('narr', cut1, narr_dur, '世界が消えます', 'red')]
for kind, orig, new, text in noads_cut.LINES:
    if kind == 'ナレーション':
        continue
    s, e = noads_cut.to_new(orig[0]), noads_cut.to_new(orig[1])
    texts.append(('head' if kind == '見出し' else 'verity', s, e, text, 'red' if kind == '見出し' else 'yellow'))
texts.append(('quote', total, total + FREEZE, noads_cut.END, 'red'))
COL = {'white': '#FFFFFF', 'red': '#FF2D2D', 'yellow': '#FFE600'}


def png(name, draw_fn):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im))
    p = os.path.join(WORK, name)
    im.save(p)
    return p


def put(d, y, s, size, col, stroke):
    f = ImageFont.truetype(FONT, size)
    if d.textlength(s, font=f) > W - 40 and '、' in s[:-1]:
        # 長い字幕は「、」で2行に分ける
        k = s.index('、') + 1
        s = s[:k] + '\n' + s[k:]
    while max(d.textlength(x, font=f) for x in s.split('\n')) > W - 40 and size > 30:
        size -= 2; f = ImageFont.truetype(FONT, size)
    d.multiline_text((W // 2, y), s, font=f, fill=col, stroke_width=stroke, stroke_fill='black', anchor='mm',
                     align='center', spacing=10)


def top(d):
    d.rectangle([0, 0, W, 322], fill='black')
    put(d, 175, 'ベリティに核は意味ない', 58, COL['yellow'], 6)
    put(d, 262, '最後の1秒で絶叫', 70, COL['red'], 7)


overlays = [(png('top.png', top), 0, total + FREEZE)]
for i, (kind, s, e, text, col) in enumerate(texts):
    y, size = {'narr': (900, 64), 'verity': (900, 52), 'head': (430, 48), 'quote': (700, 64)}[kind]
    overlays.append((png('t%02d.png' % i, lambda d, t=text, y=y, z=size, c=col: put(d, y, t, z, COL[c], 7)), s, e))

# 映像と音をつなぐ
fc = ['[0:v]split=%d%s' % (len(seg), ''.join('[vs%d]' % i for i in range(len(seg)))),
      ('[0:a]asplit=%d%s' % (len(seg), ''.join('[as%d]' % i for i in range(len(seg)))) if DUCK else
       '[0:a]asplit=%d%s' % (len(seg) - 1, ''.join('[as%d]' % i for i in range(1, len(seg)))))]  # 前の版は最初の区間の音を使わない
vlabels, alabels = [], []
for i, (a, b, sp, _) in enumerate(seg):
    d = (b - a) / sp
    v = '[vs%d]trim=%.3f:%.3f,setpts=(PTS-STARTPTS)/%.4f' % (i, a, b, sp)
    if i == 0 and ZOOM:
        # 核とベリティが並ぶ左上を切り出し、少しずつ寄りながら拡大する
        v += (",crop=400:403:50:430,scale=w='trunc(720*(1+0.2*t/%.3f)/2)*2':h='trunc(726*(1+0.2*t/%.3f)/2)*2':eval=frame"
              ",crop=720:726,pad=720:1280:0:324:black" % (d, d))
    if i == len(seg) - 1:
        v += ',tpad=stop_mode=clone:stop_duration=%.2f' % FREEZE
    fc.append(v + ',fps=30,format=yuv420p,setsar=1[v%d]' % i)
    if i == 0 and not DUCK:
        fc.append('anullsrc=r=44100:cl=stereo,atrim=0:%.3f[a%d]' % (d, i))   # 最初は元の音を消す（前の版）
    else:
        aa = '[as%d]atrim=%.3f:%.3f,asetpts=PTS-STARTPTS,aformat=sample_rates=44100:channel_layouts=stereo' % (i, a, b)
        if i == len(seg) - 1:
            aa += ',apad=pad_dur=%.2f' % FREEZE
        fc.append(aa + '[a%d]' % i)
    vlabels.append('[v%d]' % i); alabels.append('[a%d]' % i)
fc.append(''.join(v + a for v, a in zip(vlabels, alabels)) + 'concat=n=%d:v=1:a=1[bv][ba]' % len(seg))
# ナレーションを0秒から重ねる
fc.append('[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=1.6[na]')
if DUCK:
    # ナレーションの間だけ元の音を小さくする
    fc.append("[ba]volume=0.3:enable='between(t,0,%.3f)'[bd]" % (narr_dur + 0.15))
    fc.append('[bd][na]amix=inputs=2:duration=first:normalize=0[aout]')
else:
    fc.append('[ba][na]amix=inputs=2:duration=first:normalize=0[aout]')
# 文字を重ねる
last = 'bv'
for j, (p, s, e) in enumerate(overlays):
    nxt = 'o%d' % j
    fc.append("[%s][%d:v]overlay=0:0:enable='between(t,%.3f,%.3f)'[%s]" % (last, j + 2, s, e, nxt))
    last = nxt
cmd = ['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-i', NARR]
for p, _, _ in overlays:
    cmd += ['-i', p]
cmd += ['-filter_complex', ';'.join(fc), '-map', '[%s]' % last, '-map', '[aout]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
        '-movflags', '+faststart', '-t', '%.3f' % (total + FREEZE), OUT]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode:
    print(r.stderr[-3000:]); sys.exit(1)
print('出来た：%s（%.1f秒。カット %d 回）' % (OUT, total + FREEZE, len(seg) - 1))
print(json.dumps([(round(s, 2), round(e, 2), t) for _, s, e, t, _ in texts], ensure_ascii=False))
