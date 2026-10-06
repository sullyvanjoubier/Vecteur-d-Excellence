#!/usr/bin/env bash
# Rend les deux formats (images vectorielles → H.264, sans son).
set -euo pipefail
PY="${PY:-python3}"; T="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
"$PY" render.py video "$T" "$OUT/silent_9x16.mp4" portrait 4 > "$OUT/render_p.log" 2>&1
"$PY" render.py video "$T" "$OUT/silent_16x9.mp4" landscape 4 > "$OUT/render_l.log" 2>&1
echo done > "$OUT/render.done"
