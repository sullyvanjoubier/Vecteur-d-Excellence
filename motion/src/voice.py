"""Voix off française (Piper, voix siwis) + minutage mot à mot approximatif.

Sorties (dans OUT) :
  voice_timeline.wav  piste voix mono 44.1 kHz, 78 s, lignes posées à leur minutage
  timings.json        pour chaque ligne : start, dur, word_starts (décalages en s)
"""
import json, os, sys, wave
import numpy as np
from piper import PiperVoice, SynthesisConfig

OUT = sys.argv[1]
MODEL = sys.argv[2]
SR_OUT = 44100
TOTAL = 78.0

# (id, texte dit, début vidéo en secondes)
LINES = [
    ("L1",  "Un lieu, ça se dessine avant d'exister.", 3.2),
    ("L2",  "Pendant trois ans, j'ai appris à dessiner des lieux où l'on a envie d'entrer.", 11.4),
    ("L3a", "Puis j'ai regardé la rue.", 23.6),
    ("L3b", "Plus personne ne passe devant.", 27.7),
    ("L4",  "La vitrine a changé de place.", 36.0),
    ("L5",  "Une page se compose comme un espace : une entrée, un parcours, une raison de rester.", 48.9),
    ("L6",  "Et comme un lieu, elle s'entretient.", 62.7),
]

voice = PiperVoice.load(MODEL)
SR = voice.config.sample_rate
cfg = SynthesisConfig(length_scale=1.16, noise_scale=0.55, noise_w_scale=0.65)


def synth(text):
    parts = [c.audio_float_array for c in voice.synthesize(text, syn_config=cfg)]
    return np.concatenate(parts).astype(np.float32)


def trim(x, thr=0.012):
    m = np.abs(x) > thr * max(1e-6, np.abs(x).max())
    idx = np.nonzero(m)[0]
    return x[max(0, idx[0] - int(0.02 * SR)): idx[-1] + int(0.03 * SR)]


def upsample2(x):
    # 22.05 -> 44.1 kHz par zéro-padding spectral
    X = np.fft.rfft(x)
    Y = np.zeros(len(x) + 1, dtype=complex)
    Y[: len(X)] = X
    return np.fft.irfft(Y, n=2 * len(x)) * 2


timeline = np.zeros(int(TOTAL * SR_OUT), dtype=np.float32)
timings = {}
for lid, text, start in LINES:
    full = trim(synth(text))
    dur = len(full) / SR
    words = text.replace(" :", " :").split(" ")
    starts = [0.0]
    for k in range(1, len(words)):
        pre = " ".join(words[:k]).replace(" ", " ")
        starts.append(len(trim(synth(pre))) / SR)
    # début du mot k ≈ fin du préfixe k-1 ; on recale pour rester dans la durée réelle
    starts = [min(s * 0.98, dur - 0.25) for s in starts]
    for i in range(1, len(starts)):
        starts[i] = max(starts[i], starts[i - 1] + 0.05)
    timings[lid] = dict(text=text, start=start, dur=dur, words=words, word_starts=starts)

    seg = upsample2(full) if SR == 22050 else full
    fade = int(0.03 * SR_OUT)
    seg[:fade] *= np.linspace(0, 1, fade)
    seg[-fade:] *= np.linspace(1, 0, fade)
    i0 = int(start * SR_OUT)
    timeline[i0:i0 + len(seg)] += seg[: len(timeline) - i0]
    print(f"{lid}: {start:6.2f}s → {start + dur:6.2f}s  ({dur:.2f}s)")

peak = np.abs(timeline).max()
timeline = timeline / peak * 0.8
with wave.open(os.path.join(OUT, "voice_timeline.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR_OUT)
    w.writeframes((timeline * 32767).astype(np.int16).tobytes())
json.dump(timings, open(os.path.join(OUT, "timings.json"), "w"), ensure_ascii=False, indent=1)
