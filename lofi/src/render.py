# -*- coding: utf-8 -*-
"""ループ用のフレームを書き出す"""
import os, sys, time
sys.path.insert(0, "src")
import scene

os.makedirs("out/frames", exist_ok=True)
scene.build_overlays()
bg = scene.build_background()
t0 = time.time()
for i in range(scene.NF):
    scene.render_frame(i, bg).save(f"out/frames/{i:04d}.jpg", quality=94)
    if i % 96 == 0:
        el = time.time() - t0
        print(f"{i}/{scene.NF}  {el:.0f}s elapsed", flush=True)
print(f"done {scene.NF} frames in {time.time()-t0:.0f}s")
