#!/usr/bin/env python3
"""Bande son dynamique « Invisible. » (synthèse numpy, 120 BPM, 40 s).
Chaque coupe visuelle tombe sur un temps : kick, hats, clap, basse, pizzicati, nappe,
risers avant les coupes, grosse bascule grave à 15,5 s, retour au calme à 31 s, signature à 36,5 s.
Sortie : <dossier>/soundtrack_40s.wav (stéréo 48 kHz)
"""
import numpy as np, wave, sys, pathlib
SR = 48000; BPM = 120.0; BEAT = 60 / BPM; DUR = 40.0
N = int(DUR * SR); rng = np.random.default_rng(11)
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, x, t0, g=1.0):
    i = int(round(t0 * SR));
    if i >= len(buf) or i + len(x) <= 0: return
    a = max(i, 0); b = min(i + len(x), len(buf)); buf[a:b] += g * x[a - i:b - i]
def tt(d): return np.arange(int(d * SR)) / SR
def hp(x, fc):                                   # passe-haut 1er ordre (suffisant pour les hats)
    a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); p = 0.0; q = 0.0
    # filtre RC vectorisé approximatif : différence du signal lissé
    from numpy import cumsum
    k = int(SR / fc / 2) or 1
    sm = np.convolve(x, np.ones(k) / k, 'same'); return x - sm
def lp_fft(x, fc, order=2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); return np.fft.irfft(X / (1 + (f / fc) ** (2 * order)), len(x))
def bp_noise(d, lo, hi):
    n = rng.standard_normal(int(d * SR)); X = np.fft.rfft(n); f = np.fft.rfftfreq(len(n), 1 / SR)
    X *= ((f > lo) & (f < hi)); return np.fft.irfft(X, len(n))

# ---------- instruments ----------
def kick(g=1.0):
    t = tt(.32); f = 46 + 110 * np.exp(-t / .035); ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / .13) + .25 * np.sin(2 * ph) * np.exp(-t / .03)
    y[:int(.002 * SR)] *= np.linspace(0, 1, int(.002 * SR)); return g * y
def hat(g=1.0, d=.05):
    t = tt(d); n = bp_noise(d, 6500, 16000); return g * n / (np.max(np.abs(n)) + 1e-9) * np.exp(-t / (d / 4))
def clap(g=1.0):
    d = .22; t = tt(d); n = bp_noise(d, 900, 3800); y = np.zeros_like(n)
    for k, off in enumerate([0, .011, .023, .036]):
        i = int(off * SR); y[i:] += n[:len(y) - i] * np.exp(-np.arange(len(y) - i) / SR / (.012 if k < 3 else .07))
    return g * y / (np.max(np.abs(y)) + 1e-9)
def bass(n, d=.45, g=1.0):
    t = tt(d); f = midi(n); y = np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)
    y *= np.minimum(1, t / .006) * np.exp(-t / .3); return g * y
def pluck(n, g=1.0, d=.9):
    t = tt(d); f = midi(n); y = np.zeros_like(t)
    for k, a in enumerate([1, .55, .3, .18, .1], 1): y += a * np.sin(2 * np.pi * f * k * t + k) * np.exp(-t / (.5 / (1 + .5 * (k - 1))))
    y *= np.minimum(1, t / .004); return g * y / 2
def pad_note(n, d):
    t = tt(d); y = np.zeros_like(t)
    for det in (-7, 0, 7):
        f = midi(n) * 2 ** (det / 1200); k = 1
        while k * f < 2800:
            y += np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6.28)) / k ** 1.3 / (1 + (k * f / 1300) ** 4) ** .5; k += 1
    y *= np.minimum(1, t / .6) * np.minimum(1, (d - t) / .8); return y / 6
def riser(d, g=1.0):
    n = rng.standard_normal(int(d * SR)); t = tt(d); X = np.fft.rfft(n); f = np.fft.rfftfreq(len(n), 1 / SR)
    # balayage de fréquence approximé par somme de bandes ouvertes progressivement
    y = np.zeros_like(n)
    for k in range(10):
        lo = 300 * 1.45 ** k; band = np.fft.irfft(X * ((f > lo) & (f < lo * 1.8)), len(n))
        y += band * np.clip((t / d) * 10 - k * .6, 0, 1)
    y *= (t / d) ** 2.2; return g * y / (np.max(np.abs(y)) + 1e-9)
def boom(g=1.0, d=1.1, f0=70, f1=36):
    t = tt(d); f = f1 + (f0 - f1) * np.exp(-t / .12); ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / .38) + .3 * np.sin(2 * ph) * np.exp(-t / .1)
    nz = lp_fft(rng.standard_normal(len(t)), 400); y += .35 * nz / np.max(np.abs(nz)) * np.exp(-t / .02)
    y *= np.minimum(1, t / .002) * np.minimum(1, (d - t) / .2); return g * y / np.max(np.abs(y))
def tick(g=1.0):                                  # petit « tac » mat pour les coupes secondaires
    t = tt(.2); f = 60 + 90 * np.exp(-t / .02); ph = 2 * np.pi * np.cumsum(f) / SR
    return g * np.sin(ph) * np.exp(-t / .07)

# ---------- partition ----------
chords = [([50, 57, 62, 65, 69], 38), ([46, 53, 58, 62, 65], 34), ([43, 50, 55, 58, 62], 31), ([45, 52, 57, 60, 64], 33)]   # Dm9 / Bbmaj7 / Gm7 / A7sus-ish
arp = [0, 2, 3, 2, 4, 3, 2, 1]
bar = 4 * BEAT
drums = np.zeros(N); bassb = np.zeros(N); mel = np.zeros(N); pad = np.zeros(N); fx = np.zeros(N)
kicks = []                                        # pour le sidechain

def kick_at(t, g=1.0): add(drums, kick(g), t, 1); kicks.append(t)

# sections (secondes)
T_A, T_B, T_BASC, T_QUIET, T_SIG = 0.0, 2.5, 15.5, 31.0, 36.5
# nappe : un accord par mesure de 2 s, sur toute la durée utile, fondus enchaînés
for b in range(int(DUR / bar)):
    ch, root = chords[b % 4]; t0 = b * bar
    for n in ch: add(pad, pad_note(n, bar + 1.2), t0 - .3, 1)
# intro : pad seul + riser + hats naissants
add(fx, riser(1.5, .22), 1.0)
for k in range(int((2.5 - 1.0) / (BEAT / 2))): add(drums, hat(.08 + .03 * k), 1.0 + k * BEAT / 2)
# section B : groove A (2,5 → 15,5)
def groove(t_start, t_end, heavy, clap_from=None):
    t = t_start
    while t < t_end - 1e-6:
        b = int((t - 0) / bar); ch, root = chords[b % 4]; bt = (t % bar) / BEAT
        # kick sur chaque temps (« four on the floor »), sauf dernier temps avant bascule
        if abs(t % BEAT) < 1e-6 and not (t_end - t < BEAT + 1e-6 and t_end == T_BASC): kick_at(t, .95 if heavy else .8)
        # hats sur les contretemps + croches
        if abs((t % BEAT) - BEAT / 2) < 1e-6: add(drums, hat(.32 if heavy else .22, .06), t, 1)
        if heavy and abs((t % (BEAT / 2))) < 1e-6 and abs(t % BEAT) < 1e-6: add(drums, hat(.12, .03), t, 1)
        if clap_from is not None and t >= clap_from and bt in (1.0, 3.0) and abs((t % BEAT)) < 1e-6: add(drums, clap(.55 if heavy else .4), t, 1)
        # basse : fondamentale sur le 1 et la croche après le 2
        if abs(t % bar) < 1e-6: add(bassb, bass(root, .9, 1.0), t, 1)
        if abs((t % bar) - 2.5 * BEAT) < 1e-6: add(bassb, bass(root, .4, .8), t, 1)
        # pizzicati en croches
        if abs((t % (BEAT / 2))) < 1e-6:
            i = int(round((t % bar) / (BEAT / 2))); n = ch[arp[i % 8]] + (12 if heavy and i % 4 == 3 else 0) + 12
            add(mel, pluck(n, .55 if heavy else .42), t, 1)
        t = round(t + BEAT / 2, 6)
groove(T_B, T_BASC, False, clap_from=8.5)
# avant la bascule : riser sur le dernier temps et coupure des kicks
add(fx, riser(1.0, .7), T_BASC - 1.0)
for k in range(2): add(drums, hat(.3 + .1 * k, .06), T_BASC - 1.0 + k * BEAT / 2)
# bascule bleue (15,5) : le « son mat et grave » principal
add(fx, boom(1.05, 1.4, 78, 34), T_BASC); kicks.append(T_BASC)
add(fx, tick(.5), 2.5); add(fx, boom(.5, .7, 90, 45), 2.5)
for t in (5.5, 8.5, 10.8, 13.1): add(fx, tick(.55), t)
# section C : groove B, plus lourd (15,5 → 30,0)
groove(T_BASC + BEAT, 30.0, True, clap_from=T_BASC + BEAT)
add(fx, riser(1.5, .55), 19.6 - 1.5); add(fx, tick(.6), 19.5)
add(fx, riser(1.0, .5), 23.0 - 1.0); add(fx, boom(.55, .8, 84, 42), 23.0)
for t in (25.0, 27.0, 29.0): add(fx, tick(.5), t)
# break 30 → 31 : filtre fermé, riser, retour calme
add(fx, riser(1.0, .6), 30.0); add(fx, boom(.8, 1.0, 74, 38), T_QUIET)
# section D : calme (31 → 36,5) : pizzicati espacés, 1 kick sur 2, pas de basse lourde
for k in range(int((T_SIG - T_QUIET) / BEAT)):
    t = T_QUIET + k * BEAT; ch, root = chords[(int(t / bar)) % 4]
    if k % 2 == 0: kick_at(t, .55)
    if k % 2 == 1: add(mel, pluck(ch[arp[(k * 2) % 8]] + 12, .4), t, 1)
    if abs(t % bar) < 1e-6: add(bassb, bass(root, .9, .7), t, 1)
# signature (36,5) : accord ré majeur ouvert, arpège ascendant, résonance
add(fx, boom(.5, 1.2, 70, 36), T_SIG)
for i, n in enumerate([62, 66, 69, 74, 78]): add(mel, pluck(n, .5, 1.6), T_SIG + .15 + i * .22, 1)
for n in (50, 57, 62, 66, 69): add(pad, pad_note(n, 4.2), T_SIG - .2, 1.0)

# ---------- sidechain sur les kicks (nappe + pizzicati « respirent ») ----------
duck = np.ones(N)
for k in kicks:
    i = int(k * SR); L = int(.28 * SR)
    if i < N: seg = duck[i:i + L]; duck[i:i + len(seg)] = np.minimum(seg, 1 - .55 * np.exp(-np.arange(len(seg)) / SR / .09))
pad_d = pad * duck; mel_d = mel * (1 - .5 * (1 - duck))

# ---------- réverbération sur nappe + pizzicati ----------
def ir(seed, length=1.8):
    r = np.random.default_rng(seed); n = int(length * SR); x = r.standard_normal(n) * np.exp(-tt(length) / .45)
    x = lp_fft(x, 4200, 1); return x / np.sqrt(np.sum(x ** 2))
def conv(x, h):
    n = len(x) + len(h) - 1; m = 1 << (n - 1).bit_length(); return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[:len(x)]
wetL = conv(mel_d, ir(1)) * .5 + conv(pad_d, ir(2)) * .35
wetR = conv(mel_d, ir(3)) * .5 + conv(pad_d, ir(4)) * .35
# pan léger sur les pizzicati
L = drums + bassb + fx + pad_d * .5 + mel_d * .55 + wetL
R = drums + bassb + fx + pad_d * .5 + mel_d * .45 + wetR
mix = np.stack([L, R], 1)

# ---------- enveloppes globales : intro douce, calme avant 31, fin ----------
t = np.arange(N) / SR
g = np.ones(N)
g *= np.clip(t / .4, 0, 1)
calm = np.where((t >= T_QUIET) & (t < T_SIG), 1 - .35 * np.clip((t - T_QUIET) / .5, 0, 1), 1)   # section calme plus basse
g *= calm
g *= np.clip((DUR - t) / 1.2, 0, 1) ** 1.5
mix *= g[:, None]
mix *= .92 / np.max(np.abs(mix))
with wave.open(str(out / 'soundtrack_raw.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
print('ok')
