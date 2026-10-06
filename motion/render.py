#!/usr/bin/env python3
"""Rend video.html image par image (Chromium headless) -> PNG uniques + liste de durées.
Usage: render.py <v|h> <outdir> [t1 t2 ...]   (t=… : ne rend que ces instants, pour contrôle visuel)
"""
import sys, os, pathlib, hashlib
from playwright.sync_api import sync_playwright

fmt, outdir = sys.argv[1], pathlib.Path(sys.argv[2])
only = [float(x) for x in sys.argv[3:]]
FPS = 30
W, H = (1080, 1920) if fmt == 'v' else (1920, 1080)
outdir.mkdir(parents=True, exist_ok=True)
here = pathlib.Path(__file__).resolve().parent

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome' if os.path.exists('/opt/pw-browsers/chromium-1194/chrome-linux/chrome') else None,
                          args=['--force-color-profile=srgb', '--disable-lcd-text', '--font-render-hinting=none', '--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    pg.goto(f'file://{here}/video.html?f={fmt}')
    pg.wait_for_function('window.READY === true')
    pg.wait_for_timeout(300)
    print(pg.evaluate('overflowReport()'))
    if only:
        for t in only:
            pg.evaluate(f'render({t})')
            pg.screenshot(path=str(outdir / f'check_{t:06.2f}.png'))
        b.close(); sys.exit(0)

    t_end = pg.evaluate('T_END')
    n = int(round(t_end * FPS))
    last_sig, last_file, runs = None, None, []   # runs: [file, nframes]
    shots = 0
    for i in range(n):
        t = i / FPS
        sig = pg.evaluate(f'render({t!r})')
        if sig != last_sig:
            last_file = outdir / f'f_{i:05d}.png'
            pg.screenshot(path=str(last_file))
            runs.append([last_file, 1]); last_sig = sig; shots += 1
        else:
            runs[-1][1] += 1
    b.close()

with open(outdir / 'frames.txt', 'w') as f:
    for fn, k in runs:
        f.write(f"file '{fn.resolve()}'\nduration {k / FPS:.6f}\n")
    f.write(f"file '{runs[-1][0].resolve()}'\n")   # concat demuxer : dernière image répétée
print(f'{n} images vidéo, {shots} captures uniques')
