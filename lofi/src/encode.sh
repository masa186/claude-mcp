#!/usr/bin/env bash
# フレームと曲から耐久動画を書き出す。 使い方: src/encode.sh <秒数> <出力ファイル>
set -euo pipefail
DUR="${1:-600}"
OUT="${2:-out/otter_lofi_10min.mp4}"
LOOPSEC=24

# 1) 24秒のループ素材を作る
ffmpeg -y -loglevel error -framerate 24 -i out/frames/%04d.jpg \
  -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p -g 48 out/segment.mp4

# 2) 尺のぶんだけ繰り返す（再エンコードなし）
REPS=$(( (DUR + LOOPSEC - 1) / LOOPSEC ))
ffmpeg -y -loglevel error -stream_loop $((REPS - 1)) -i out/segment.mp4 -c copy out/video_long.mp4

# 3) 曲をループさせて合成し、最後をフェードアウト
ffmpeg -y -loglevel error -i out/video_long.mp4 -stream_loop -1 -i out/loop.wav \
  -map 0:v -map 1:a -c:v copy \
  -af "afade=t=out:st=$((DUR - 6)):d=6" \
  -c:a aac -b:a 192k -ar 44100 -t "$DUR" -movflags +faststart "$OUT"

ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
