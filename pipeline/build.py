"""フレームを全部書き出して、音を混ぜて MP4 にする。

混ぜるもの（あるものだけ・無ければ飛ばす）:
  frames/       映像
  se.wav        効果音（sound.py が作る）
  narration.wav ナレーション
  bgm.mp3       BGM。音量は sound.volume_expr() で自動で上下する
"""
import os, time, subprocess, sys
import imageio_ffmpeg as ie
import render, sound

FF = ie.get_ffmpeg_exe()
OUT = 'ep01.mp4'

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')

# ---------------------------------------------------------------- 声（先に）
# 絵より先に音を決める。そうしないと尺に収まらない行を早口にするしかなく、
# クチパクも波形に合わせられない。
import voice
VOICE, NAR = 'voice.wav', 'narration.wav'
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
voice.dump_text(render.SHOTS, os.path.join(DOCS, 'narration_ep01.txt'))
print('尺 %.1f秒' % render.DURATION, flush=True)

# ---------------------------------------------------------------- 映像
os.makedirs('frames', exist_ok=True)
n = int(render.DURATION * render.FPS)
AUDIO_ONLY = '--audio' in sys.argv and len(os.listdir('frames')) >= n
if AUDIO_ONLY:
    print('フレームは既にあるので音だけ組み直す', flush=True)
t0 = time.time()
for i in range(0 if not AUDIO_ONLY else n, n):
    render.render_frame(i / render.FPS).save('frames/%05d.png' % i)
    if i % 100 == 0:
        print('  %d/%d  %.0fs' % (i, n, time.time() - t0), flush=True)
print('frames done %.0fs' % (time.time() - t0), flush=True)

# ---------------------------------------------------------------- 音
sound.write_wav('se.wav', sound.build_track(render.DURATION))

cmd = [FF, '-y', '-framerate', str(render.FPS), '-i', 'frames/%05d.png',
       '-i', 'se.wav']
labels = ['[1:a]']
filt = []
idx = 1

if nar:
    idx += 1
    cmd += ['-i', nar]
    labels.append('[%d:a]' % idx)

if os.path.exists('bgm.mp3'):
    idx += 1
    # 動画より短ければ繰り返す
    cmd += ['-stream_loop', '-1', '-i', 'bgm.mp3']
    # 声が乗るぶんBGMを下げる。ここを下げないと台詞が埋もれる
    filt.append("[%d:a]volume='%s':eval=frame[b]"
                % (idx, sound.volume_expr(0.55 if nar else 1.0)))
    labels.append('[b]')

mix = ''.join(labels) + 'amix=inputs=%d:duration=first:normalize=0[m]' % len(labels)
# 効果音とBGMが重なるとピークが1を超える。level=disabled にしないと
# alimiter が上限まで持ち上げ直してしまい、かえって大きくなる。
lim = '[m]alimiter=limit=0.85:level=disabled:attack=3:release=60[a]'
cmd += ['-filter_complex', ';'.join(filt + [mix, lim]), '-map', '0:v', '-map', '[a]']
cmd += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
        '-pix_fmt', 'yuv420p', '-r', str(render.FPS),
        '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT]

print('音: 効果音' + ('＋声(%s)' % nar if nar else '') +
      ('＋BGM' if os.path.exists('bgm.mp3') else ''), flush=True)

r = subprocess.run(cmd, capture_output=True, text=True)
print('ENCODE', 'OK' if r.returncode == 0 else r.stderr[-900:], flush=True)
if r.returncode == 0:
    print('size %.1f MB' % (os.path.getsize(OUT) / 1e6))
