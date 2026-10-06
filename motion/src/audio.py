"""Bande-son synthétisée : piste instrumentale, crayon sur papier, trois déclics.

  python audio.py <timings.json> <out_dir>
Écrit music.wav (stéréo, 78 s, fin en fondu de 2 s) et fx.wav (crayon + déclics).
Aucune voix, aucun échantillon externe : tout est calculé (NumPy).
"""
import json, math, sys, wave
import numpy as np
from scene import Scene, DUR

SR = 44100
OUT = sys.argv[2]
N = int(DUR * SR)
rng = np.random.default_rng(11)
TWO_PI = 2 * np.pi


def write_wav(path, x):
    x = np.atleast_2d(x)
    peak = np.abs(x).max()
    if peak > 0.98:
        x = x / peak * 0.98
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[0]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x.T * 32767).astype(np.int16).tobytes())


def fft_filter(x, lo=None, hi=None, soft=0.15):
    """Filtre passe-bande par masque spectral à bords doux."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + np.exp(-(f - lo) / (lo * soft)))
    if hi:
        m *= 1 / (1 + np.exp((f - hi) / (hi * soft)))
    return np.fft.irfft(X * m, n=len(x))


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ── Musique : 76 BPM, deux voix (cordes tenues + piano feutré) ─────────────
BPM = 76
BEAT = 60 / BPM
CHORD = 8 * BEAT                      # deux mesures par accord
N_MUS = int(82 * SR)
# Si mineur → Sol maj9 → Ré maj9 → Mi m9 : accords voisins, aucune montée ni résolution
CHORDS = [
    dict(pad=[50, 57, 62, 64, 69], pno=[71, 74, 78, 69, 76]),        # Bm11
    dict(pad=[43, 50, 59, 62, 69], pno=[71, 74, 78, 69, 67]),        # Gmaj9 (ré, si, fa#, la)
    dict(pad=[50, 57, 61, 64, 66], pno=[69, 73, 78, 76, 74]),        # Dmaj9
    dict(pad=[52, 59, 62, 66, 67], pno=[67, 71, 74, 78, 76]),        # Em9
]


def pad_note(f, dur, pan):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    vib = 1 + 0.0018 * np.sin(TWO_PI * 4.7 * t + rng.uniform(0, 6.28))
    for det in (-0.0030, 0.0, 0.0030):
        ph = rng.uniform(0, 6.28)
        for h in range(1, 11):
            fh = f * h * (1 + det)
            if fh > 5200:
                break
            y += (1 / h ** 1.15) * math.exp(-h / 6.0) * np.sin(TWO_PI * fh * t * vib + ph * h)
    a, r = 1.7, 1.9
    env = np.minimum(1, t / a) ** 2 * np.minimum(1, (dur - t) / r) ** 2
    y *= env * 0.05
    return np.stack([y * (1 - pan), y * (1 + pan)])


def piano_note(f, vel, pan, dur=4.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for h in range(1, 10):
        fh = f * h * math.sqrt(1 + 0.00025 * h * h)
        if fh > 5500:
            break
        amp = (1 / h ** 1.35) * math.exp(-(f * h) / 3000.0)
        tau = 1.7 / (1 + 0.55 * (h - 1))
        y += amp * np.sin(TWO_PI * fh * t + rng.uniform(0, 6.28)) * np.exp(-t / tau)
    y *= (1 - np.exp(-t / 0.006)) * np.minimum(1, (dur - t) / 0.4)
    felt = rng.standard_normal(n) * np.exp(-t / 0.012) * 0.02
    y = (y + fft_filter(felt, hi=1500)) * vel * 0.19
    return np.stack([y * (1 - pan), y * (1 + pan)])


def build_music():
    mus = np.zeros((2, N_MUS))
    n_chords = int(math.ceil(82 / CHORD)) + 1
    for k in range(n_chords):
        c = CHORDS[k % 4]
        t0 = k * CHORD
        for j, m in enumerate(c["pad"]):
            seg = pad_note(midi(m), CHORD + 3.4, pan=(-0.35 + 0.17 * j))
            i0 = int((t0 - 1.7) * SR)
            a, b = max(i0, 0), min(i0 + seg.shape[1], N_MUS)
            if b > a:
                mus[:, a:b] += seg[:, a - i0: b - i0]
        eighth = BEAT / 2
        for idx, step in enumerate([0, 3, 6, 8, 11, 14]):
            note = c["pno"][[0, 2, 1, 3, 2, 4][idx]]
            vel = 0.78 + 0.10 * math.sin(k * 1.7 + idx * 2.3)
            seg = piano_note(midi(note), vel, pan=rng.uniform(-0.3, 0.3))
            i0 = int((t0 + step * eighth) * SR)
            a, b = i0, min(i0 + seg.shape[1], N_MUS)
            if b > a:
                mus[:, a:b] += seg[:, : b - a]
    # réverbération douce (la musique peut avoir une salle ; le crayon, non)
    ir_n = int(2.2 * SR)
    tt = np.arange(ir_n) / SR
    wet = np.zeros_like(mus)
    for ch in range(2):
        ir = rng.standard_normal(ir_n) * np.exp(-tt / 0.32)
        ir = fft_filter(ir, hi=3800)
        size = 1 << int(np.ceil(np.log2(N_MUS + ir_n)))
        conv = np.fft.irfft(np.fft.rfft(mus[ch], size) * np.fft.rfft(ir, size), size)[:N_MUS]
        wet[ch] = conv * (0.30 / np.abs(ir).sum() * 18)
    mus = mus + wet
    for ch in range(2):
        mus[ch] = fft_filter(mus[ch], lo=95, hi=7000)
    # niveau constant : on aplatit lentement l'enveloppe RMS
    win = int(2.0 * SR)
    env = np.sqrt(np.convolve((mus ** 2).mean(0), np.ones(win) / win, mode="same")) + 1e-9
    target = np.median(env[int(4 * SR): -int(4 * SR)])
    gain = np.clip(target / env, 0.6, 1.6)
    mus *= gain
    mus = mus[:, :N]
    rms = np.sqrt((mus ** 2).mean())
    mus *= 10 ** (-34 / 20) / rms                          # ≈ −34 dBFS RMS, sous la voix
    fade = int(2.0 * SR)
    mus[:, -fade:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fade)))
    mus[:, :int(0.4 * SR)] *= np.linspace(0, 1, int(0.4 * SR))
    return mus


# ── Crayon : frottement sec, calé sur la vitesse réelle du tracé ───────────
def build_pencil(scene):
    rate = 200
    env = np.array(scene.pencil_envelope(rate))
    t = np.arange(N) / SR
    sp = np.interp(t, np.arange(len(env)) / rate, env)
    sp = fft_filter(sp, hi=30)                              # lisse l'enveloppe
    amp = np.clip(sp / 2200.0, 0, 1) ** 0.75
    noise = fft_filter(rng.standard_normal(N), lo=1500, hi=7500)
    grain = fft_filter(np.abs(rng.standard_normal(N)), hi=180)
    grain = 0.55 + 0.45 * (grain - grain.mean()) / (grain.std() + 1e-9) * 0.5
    y = noise * np.clip(grain, 0.2, 1.4) * amp
    y *= 0.060 / (np.abs(y).max() + 1e-9)                   # ≈ −24 dBFS crête : très bas, presque subliminal
    return y


# ── Trois déclics mats, un par élément substitué ───────────────────────────
def build_clicks(times=(39.0, 39.5, 40.0), freqs=(165, 185, 210)):
    y = np.zeros(N)
    for t0, f in zip(times, freqs):
        n = int(0.12 * SR)
        t = np.arange(n) / SR
        body = np.sin(TWO_PI * f * t) * np.exp(-t / 0.016)
        tick = fft_filter(rng.standard_normal(n), hi=2600) * np.exp(-t / 0.0025) * 1.2
        c = (body * 0.9 + tick) * 0.17
        i0 = int(t0 * SR)
        y[i0:i0 + n] += c
    return y


if __name__ == "__main__":
    import os
    scene = Scene(sys.argv[1])
    if os.environ.get("KEEP_MUSIC") and os.path.exists(f"{OUT}/music.wav"):
        mus = np.zeros((2, 1))
    else:
        mus = build_music()
        write_wav(f"{OUT}/music.wav", mus)
    pen = build_pencil(scene)
    clk = build_clicks()
    fx = pen + clk
    write_wav(f"{OUT}/fx.wav", np.stack([fx, fx]))
    print("music rms dBFS", 20 * np.log10(np.sqrt((mus ** 2).mean())), " pencil peak", np.abs(pen).max(),
          " clicks peak", np.abs(clk).max())
