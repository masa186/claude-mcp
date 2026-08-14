"""フレームを全部書き出して、音を混ぜて MP4 にする。

混ぜるもの（あるものだけ・無ければ飛ばす）:
  frames/       映像
  se.wav        効果音（sound.py が作る）
  narration.wav ナレーション
  bgm.mp3       BGM。音量は sound.volume_expr() で自動で上下する
"""
import os, time, subprocess
import imageio_ffmpeg as ie
import render, sound

FF = ie.get_ffmpeg_exe()
OUT = 'ep01.mp4'

# ---------------------------------------------------------------- 映像
os.makedirs('frames', exist_ok=True)
n = int(render.DURATION * render.FPS)
t0 = time.time()
for i in range(n):
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

if os.path.exists('narration.wav'):
    idx += 1
    cmd += ['-i', 'narration.wav']
    labels.append('[%d:a]' % idx)

if os.path.exists('bgm.mp3'):
    idx += 1
    # 動画より短ければ繰り返す
    cmd += ['-stream_loop', '-1', '-i', 'bgm.mp3']
    filt.append("[%d:a]volume='%s':eval=frame[b]" % (idx, sound.volume_expr()))
    labels.append('[b]')

mix = ''.join(labels) + 'amix=inputs=%d:duration=first:normalize=0[a]' % len(labels)
cmd += ['-filter_complex', ';'.join(filt + [mix]), '-map', '0:v', '-map', '[a]']
cmd += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
        '-pix_fmt', 'yuv420p', '-r', str(render.FPS),
        '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT]

print('音: 効果音' +
      ('＋ナレーション' if os.path.exists('narration.wav') else '') +
      ('＋BGM' if os.path.exists('bgm.mp3') else ''), flush=True)

r = subprocess.run(cmd, capture_output=True, text=True)
print('ENCODE', 'OK' if r.returncode == 0 else r.stderr[-900:], flush=True)
if r.returncode == 0:
    print('size %.1f MB' % (os.path.getsize(OUT) / 1e6))
