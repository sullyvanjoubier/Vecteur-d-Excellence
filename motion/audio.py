#!/usr/bin/env python3
"""Synthèse de la bande son « Invisible. » (aucune IA externe, numpy seul).
 - piste instrumentale 72 s : nappe de cordes tenues + piano feutré (2 voix), ~76 BPM,
   intensité constante, aucune percussion, extinction sur les 2 dernières secondes
 - montage 68 s : plan 1 muet · musique dès 0:07, très bas, jamais modifiée
   · UN son mat et grave à 0:30 (bascule crème -> bleu) · extinction sur le plan 6 · signature muette
Sortie : music_72s.wav, soundtrack_68s.wav (stéréo 48 kHz, 16 bits)
"""
import numpy as np, wave, sys, pathlib
SR = 48000
rng = np.random.default_rng(7)
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def write(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())

BPM = 76.0; BEAT = 60 / BPM
DUR = 72.0
N = int(DUR * SR)
t_all = np.arange(N) / SR

# ---------- Voix 1 : nappe de cordes tenues ----------
# Dm9 -> Bbmaj7 -> Gm9 -> Am7/11 ... accords de 8 temps, longs fondus enchaînés (aucune attaque audible)
chords = [
    [50, 57, 65, 69, 76],   # Dm9 (D3 A3 F4 A4 E5)
    [46, 58, 65, 69, 74],   # Bbmaj7 (Bb2 Bb3 F4 A4 D5)
    [43, 55, 62, 65, 72],   # Gm9-ish (G2 G3 D4 F4 C5)
    [45, 57, 64, 67, 72],   # Am7(11) (A2 A3 E4 G4 C5)
]
CH_LEN = 8 * BEAT * 2          # 16 temps par accord (~12,6 s)
XF = 5.0                       # fondu enchaîné

def saw_pad(freq, length, cutoff=1100.0):
    n = int(length * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    vib = 1 + 0.0018 * np.sin(2 * np.pi * (4.6 + rng.uniform(-.4, .4)) * t + rng.uniform(0, 6.28))
    for det in (-6, 0, 6):
        f = freq * 2 ** (det / 1200) * vib
        ph = 2 * np.pi * np.cumsum(f) / SR + rng.uniform(0, 6.28)
        k = 1
        while k * freq < 6000:
            roll = 1 / np.sqrt(1 + (k * freq / cutoff) ** 4)
            y += np.sin(k * ph) * roll / k
            k += 1
    return y / 3

pad = np.zeros(N)
nseg = int(np.ceil((DUR + XF) / CH_LEN)) + 1
for s in range(nseg):
    ch = chords[s % len(chords)]
    t0 = s * CH_LEN - XF / 2
    length = CH_LEN + XF
    seg = sum(saw_pad(midi(n) * (1 if n > 52 else 1), length) * (0.75 if n < 52 else 1.0) for n in ch)
    n = len(seg); tt = np.arange(n) / SR
    env = np.minimum(1, tt / XF) * np.minimum(1, (length - tt) / XF)
    env = np.sin(env * np.pi / 2) ** 2
    i0 = int(t0 * SR)
    a, b = max(i0, 0), min(i0 + n, N)
    if b > a: pad[a:b] += (seg * env)[a - i0:b - i0]
pad *= 0.9 / np.max(np.abs(pad))

# ---------- Voix 2 : piano feutré, une note tous les 2 temps ----------
def piano(freq, vel):
    length = 4.5; n = int(length * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for k in range(1, 9):
        fk = freq * k * np.sqrt(1 + 0.0004 * k * k)
        amp = vel / k ** 1.7
        tau = 2.8 / (1 + 0.55 * (k - 1))
        y += amp * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t / tau)
    y *= np.minimum(1, t / 0.012)                      # attaque douce (feutre)
    y *= np.exp(-np.maximum(0, t - 3.8) * 6)
    return y

scale = [62, 65, 67, 69, 72, 74, 77, 79]   # D4 F4 G4 A4 C5 D5 F5 G5 (ré dorien/éolien, sans sensible)
pno = np.zeros(N)
t = 0.4
i = 0
prev = 3
while t < DUR - 1:
    step = rng.choice([-2, -1, 1, 2], p=[.2, .3, .3, .2])
    prev = int(np.clip(prev + step, 0, len(scale) - 1))
    vel = rng.uniform(0.55, 0.8)
    nt = piano(midi(scale[prev]), vel)
    a = int(t * SR); b = min(a + len(nt), N)
    pno[a:b] += nt[:b - a]
    t += 2 * BEAT * rng.choice([1, 1, 1, 1.5, 2])        # rythme posé, légèrement irrégulier
    i += 1
pno *= 0.9 / np.max(np.abs(pno))

# ---------- Réverbération (réponse impulsionnelle synthétique, stéréo) ----------
def ir(seed, length=3.2):
    r = np.random.default_rng(seed); n = int(length * SR); tt = np.arange(n) / SR
    x = r.standard_normal(n) * np.exp(-tt / 0.75)
    # passe-bas progressif
    X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    X *= 1 / (1 + (f / 3500) ** 2)
    x = np.fft.irfft(X, n); x[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    return x / np.sqrt(np.sum(x ** 2))

def conv(x, h):
    n = len(x) + len(h) - 1; m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[:len(x)]

def mix_voice(x, wet, pan):
    L = x * (1 - wet) * (1 - pan * .3) + wet * conv(x, ir(1)) * 0.9
    R = x * (1 - wet) * (1 + pan * .3) + wet * conv(x, ir(2)) * 0.9
    return np.stack([L, R], 1)

music = 0.55 * mix_voice(pad, 0.35, -0.2) + 0.50 * mix_voice(pno, 0.40, 0.3)
# intensité constante : on lisse l'enveloppe lente pour éviter toute « montée »
win = int(3 * SR)
env = np.sqrt(np.convolve(np.mean(music ** 2, 1), np.ones(win) / win, 'same')) + 1e-6
tgt = np.median(env[int(4 * SR):int(-4 * SR)])
gain = np.clip(tgt / env, 0.6, 1.6)
gain = np.convolve(gain, np.ones(win) / win, 'same')
music *= gain[:, None]
# extinction progressive sur les 2 dernières secondes (piste de campagne)
fo = np.clip((DUR - t_all) / 2.0, 0, 1) ** 2
music *= fo[:, None]
# départ doux (piste cut-anywhere) : 0,3 s
music *= np.clip(t_all / 0.3, 0, 1)[:, None]
music *= 0.89 / np.max(np.abs(music))
write(out / 'music_72s.wav', music)

# ---------- Montage 68 s ----------
TOT = 68.0; M = int(TOT * SR)
mt = np.arange(M) / SR
track = np.zeros((M, 2))
T0 = 7.0                                   # entrée au plan 2
seg = music[:M - int(T0 * SR)].copy()
track[int(T0 * SR):] = seg
ramp_in = np.clip((mt - T0) / 2.5, 0, 1) ** 2                 # entrée très progressive
ramp_out = np.clip((64.0 - mt) / 8.0, 0, 1) ** 1.6            # extinction sur tout le plan 6 (0:56 -> 1:04)
track *= (ramp_in * ramp_out)[:, None]
track *= 10 ** (-17 / 20)                                       # « très bas »

# UN seul événement sonore : son mat et grave, très court, à 0:30,00 (sec, sans réverb)
def thud():
    n = int(0.6 * SR); tt = np.arange(n) / SR
    f = 42 + 36 * np.exp(-tt / 0.06)                 # 78 Hz -> 42 Hz
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-tt / 0.11)
    y += 0.35 * np.sin(2 * ph) * np.exp(-tt / 0.05)   # tient sur petits haut-parleurs
    y += 0.18 * np.sin(3 * ph) * np.exp(-tt / 0.03)
    nz = rng.standard_normal(n); X = np.fft.rfft(nz); fr = np.fft.rfftfreq(n, 1 / SR)
    nz = np.fft.irfft(X / (1 + (fr / 220) ** 2), n)
    y += 0.5 * nz / np.max(np.abs(nz)) * np.exp(-tt / 0.012)
    y *= np.minimum(1, tt / 0.002) * np.minimum(1, (0.6 - tt) / 0.08)
    return y / np.max(np.abs(y))
th = thud() * 10 ** (-6.5 / 20)
i0 = int(30.0 * SR)
track[i0:i0 + len(th)] += th[:, None]
write(out / 'soundtrack_68s.wav', track)
print('ok', np.max(np.abs(track)))
