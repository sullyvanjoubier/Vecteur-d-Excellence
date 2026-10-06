#!/usr/bin/env bash
# Mixage final : voix traitée + musique + crayon/déclics → mix.wav (≈ −16 LUFS)
set -euo pipefail
D="$1"
ffmpeg -y -loglevel error -i "$D/voice_timeline.wav" -i "$D/music.wav" -i "$D/fx.wav" -filter_complex "
[0:a]highpass=f=85,equalizer=f=220:t=q:w=1:g=-1.5,equalizer=f=3000:t=q:w=1.1:g=2.5,acompressor=threshold=0.12:ratio=2.8:attack=12:release=160:makeup=2.5,aformat=sample_fmts=fltp:channel_layouts=stereo[v];
[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo[m];
[2:a]aformat=sample_fmts=fltp:channel_layouts=stereo[f];
[v][m][f]amix=inputs=3:normalize=0:duration=longest[x]" -map "[x]" -ar 44100 -c:a pcm_f32le "$D/mix_raw.wav"
# loudness : mesure puis gain pour viser −16 LUFS intégrés, crête ≤ −1.5 dBTP
LUFS=$(ffmpeg -nostats -i "$D/mix_raw.wav" -af ebur128=peak=true -f null - 2>&1 | grep -A1 "Integrated loudness" | grep "I:" | awk '{print $2}')
GAIN=$(python3 -c "print(round(-16 - float('$LUFS'),2))")
echo "mesuré $LUFS LUFS → gain $GAIN dB"
ffmpeg -y -loglevel error -i "$D/mix_raw.wav" -af "volume=${GAIN}dB,alimiter=limit=0.84:level=false:attack=3:release=60" -ar 44100 -c:a pcm_s16le "$D/mix.wav"
ffmpeg -nostats -i "$D/mix.wav" -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|LRA:|Peak:" | tail -4
