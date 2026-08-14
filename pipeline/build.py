import os, time, subprocess, sys
import imageio_ffmpeg as ie
import render, sound

FF = ie.get_ffmpeg_exe()
os.makedirs('frames', exist_ok=True)
n = int(render.DURATION * render.FPS)
t0 = time.time()
for i in range(n):
    render.render_frame(i / render.FPS).save('frames/%05d.png' % i)
    if i % 100 == 0:
        print('  %d/%d  %.0fs' % (i, n, time.time()-t0), flush=True)
print('frames done %.0fs' % (time.time()-t0), flush=True)

sound.write_wav('se.wav', sound.build_track(render.DURATION))

cmd = [FF, '-y', '-framerate', str(render.FPS), '-i', 'frames/%05d.png',
       '-i', 'se.wav',
       '-map', '0:v', '-map', '1:a',
       '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
       '-pix_fmt', 'yuv420p', '-r', str(render.FPS),
       '-c:a', 'aac', '-b:a', '192k', '-shortest', 'ep01.mp4']
r = subprocess.run(cmd, capture_output=True, text=True)
print('ENCODE', 'OK' if r.returncode == 0 else r.stderr[-800:], flush=True)
print('size %.1f MB' % (os.path.getsize('ep01.mp4')/1e6))
