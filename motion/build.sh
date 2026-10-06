#!/usr/bin/env bash
# Usage: ./build.sh   (nécessite python3 + playwright + ffmpeg ; polices dans fonts/)
set -e
cd "$(dirname "$0")"; W=${TMPDIR:-/tmp}/invisible_build; mkdir -p "$W/fv" "$W/fh" "$W/au" out
python3 audio.py "$W/au"
python3 render.py v "$W/fv"; python3 render.py h "$W/fh"
for f in v h; do n=$([ $f = v ] && echo vertical_9x16 || echo horizontal_16x9)
  ffmpeg -y -f concat -safe 0 -i "$W/f$f/frames.txt" -i "$W/au/soundtrack_68s.wav" \
   -vf "fps=30,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" -c:v libx264 -preset slow -crf 14 \
   -color_primaries bt709 -color_trc bt709 -colorspace bt709 -c:a aac -b:a 192k -ar 48000 -t 68 -movflags +faststart "out/invisible_$n.mp4"
done
