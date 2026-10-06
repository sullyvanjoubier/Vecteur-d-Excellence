"""Rendu des images (Cairo, multiprocessus) → H.264 via ffmpeg.

  python render.py still  <timings.json> <out_dir> <portrait|landscape> t1 t2 ...
  python render.py video  <timings.json> <out.mp4> <portrait|landscape> [workers]
"""
import subprocess, sys
from multiprocessing import Pool

import cairo
from scene import Scene, Layout, FPS, DUR

_state = {}


def _init(timings, kind):
    lay = Layout(kind)
    _state["scene"] = Scene(timings)
    _state["lay"] = lay
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, lay.W, lay.H)
    _state["surf"] = s
    _state["ctx"] = cairo.Context(s)


def _frame(i):
    ctx = _state["ctx"]
    ctx.identity_matrix()
    ctx.set_dash([])
    _state["scene"].render(ctx, i / FPS, _state["lay"])
    _state["surf"].flush()
    return bytes(_state["surf"].get_data())


def main():
    mode, timings, out, kind = sys.argv[1:5]
    if mode == "still":
        _init(timings, kind)
        for t in sys.argv[5:]:
            ctx = _state["ctx"]
            _state["scene"].render(ctx, float(t), _state["lay"])
            _state["surf"].write_to_png(f"{out}/{kind[0]}_{float(t):05.1f}.png")
        return
    workers = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    lay = Layout(kind)
    n = int(DUR * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{lay.W}x{lay.H}",
         "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-colorspace", "bt709", "-color_primaries", "bt709",
         "-color_trc", "bt709", out],
        stdin=subprocess.PIPE)
    with Pool(workers, initializer=_init, initargs=(timings, kind)) as pool:
        for k, buf in enumerate(pool.imap(_frame, range(n), chunksize=2)):
            ff.stdin.write(buf)
            if k % 150 == 0:
                print(f"{k}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main()
