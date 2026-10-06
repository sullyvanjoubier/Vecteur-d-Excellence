"""« La vitrine a changé de place » — scène vectorielle 2D (Cairo).

Tout est défini dans un repère « scène » portrait 1080×1920 ; le Layout le
projette en 9:16 (1080×1920) ou en 16:9 (1920×1080).  Le trait garde la même
épaisseur (LW px) dans les deux formats et d'un plan à l'autre.
"""
import json, math, os
import cairo

# ── Charte ─────────────────────────────────────────────────────────────────
NAVY = (0x1A / 255, 0x00 / 255, 0x89 / 255)
ORANGE = (0xD4 / 255, 0x63 / 255, 0x3F / 255)
CREAM = (0xEF / 255, 0xE7 / 255, 0xD3 / 255)
INK = (0x1F / 255, 0x1F / 255, 0x1F / 255)
LW = 3.0
FPS = 30
DUR = 78.0
SERIF = "Cormorant Garamond"
SANS = "Inter"

HERE = os.path.dirname(os.path.abspath(__file__))


# ── Outils ─────────────────────────────────────────────────────────────────
def c01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def e_io(u):
    return 0.5 - 0.5 * math.cos(math.pi * c01(u))


def e_out(u):
    return 1 - (1 - c01(u)) ** 3


def mix(a, b, k):
    k = c01(k)
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def arc(cx, cy, r, a0, a1, n=28):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def circle(cx, cy, r, n=40):
    return arc(cx, cy, r, -math.pi / 2, 1.5 * math.pi, n)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def rrect(x0, y0, x1, y1, r, n=8):
    p = []
    p += arc(x1 - r, y0 + r, r, -math.pi / 2, 0, n)
    p += arc(x1 - r, y1 - r, r, 0, math.pi / 2, n)
    p += arc(x0 + r, y1 - r, r, math.pi / 2, math.pi, n)
    p += arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi, n)
    p.append(p[0])
    return p


def cote(x0, y0, x1, y1, tick=7):
    """Ligne de cote : trait + deux ticks d'architecte à 45°."""
    return [[(x0, y0), (x1, y1)],
            [(x0 - tick, y0 + tick), (x0 + tick, y0 - tick)],
            [(x1 - tick, y1 + tick), (x1 + tick, y1 - tick)]]


class Layout:
    def __init__(self, kind):
        self.kind = kind
        if kind == "portrait":
            self.W, self.H, self.s, self.ox, self.oy = 1080, 1920, 1.0, 0.0, 0.0
        else:
            self.W, self.H, self.s = 1920, 1080, 0.96
            self.ox, self.oy = 1330 - 0.96 * 540, 540 - 0.96 * 750

    def P(self, x, y):
        return self.ox + self.s * x, self.oy + self.s * y


# ── Éléments dessinés ──────────────────────────────────────────────────────
class El:
    """Un ou plusieurs tracés. Apparition par tracé progressif (« draw ») ou
    fondu (« fade ») ; disparition par effacement (« retract ») ou fondu."""

    def __init__(self, polys, t_in=0.0, d_in=0.0, t_out=None, d_out=0.0, out="retract",
                 inmode="draw", color=NAVY, alpha=1.0, xf=None, amul=None, pencil=False,
                 tip=False, ease=e_io, dash=None, dash_v=0.0, fill=None, rot=None, lw=LW):
        if polys and isinstance(polys[0], tuple):
            polys = [polys]
        self.polys = polys
        self.t_in, self.d_in, self.t_out, self.d_out = t_in, d_in, t_out, d_out
        self.out, self.inmode, self.color, self.alpha = out, inmode, color, alpha
        self.xf, self.amul, self.pencil, self.tip, self.ease = xf, amul, pencil, tip, ease
        self.dash, self.dash_v, self.fill, self.rot, self.lw = dash, dash_v, fill, rot, lw
        self.cum = []
        tot = 0.0
        for p in polys:
            c = [0.0]
            for i in range(1, len(p)):
                c.append(c[-1] + math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]))
            self.cum.append((tot, c))
            tot += c[-1]
        self.L = max(tot, 1e-6)

    # progression d'entrée / de sortie
    def u_in(self, t):
        if t < self.t_in:
            return 0.0
        if self.d_in <= 0:
            return 1.0
        return self.ease((t - self.t_in) / self.d_in)

    def u_out(self, t):
        if self.t_out is None or t < self.t_out:
            return 0.0
        if self.d_out <= 0:
            return 1.0
        return e_io((t - self.t_out) / self.d_out)

    def speed(self, t):
        """Vitesse de tracé (px/s) — sert à synchroniser le bruit de crayon."""
        if not self.pencil or self.d_in <= 0 or not (self.t_in < t < self.t_in + self.d_in):
            return 0.0
        u = (t - self.t_in) / self.d_in
        d = 0.5 * math.pi * math.sin(math.pi * u) if self.ease is e_io else 1.0
        return self.L * d / self.d_in

    def _sub(self, s, e):
        """Points entre les abscisses curvilignes s et e (en px, scène)."""
        out = []
        for (off, c), p in zip(self.cum, self.polys):
            a, b = max(s - off, 0.0), min(e - off, c[-1])
            if b <= a:
                continue
            sub = []
            for i in range(1, len(p)):
                if c[i] < a or c[i - 1] > b:
                    continue
                seg = c[i] - c[i - 1]
                if seg <= 0:
                    continue
                ta, tb = max((a - c[i - 1]) / seg, 0.0), min((b - c[i - 1]) / seg, 1.0)
                x0, y0 = p[i - 1]
                x1, y1 = p[i]
                if not sub:
                    sub.append((x0 + (x1 - x0) * ta, y0 + (y1 - y0) * ta))
                sub.append((x0 + (x1 - x0) * tb, y0 + (y1 - y0) * tb))
            if sub:
                out.append(sub)
        return out

    def draw(self, ctx, t, lay, g=1.0):
        ui, uo = self.u_in(t), self.u_out(t)
        if ui <= 0 or uo >= 1:
            return
        a = self.alpha * g
        if self.amul:
            a *= self.amul(t)
        if self.inmode == "fade":
            a *= ui
            s, e = 0.0, self.L
        else:
            s, e = 0.0, ui * self.L
        if self.out == "fade":
            a *= 1 - uo
        else:
            s = uo * self.L
        if a <= 0.003 or e <= s:
            return
        col = self.color(t) if callable(self.color) else self.color
        sx, sy, tx, ty, cx, cy = self.xf(t) if self.xf else (1, 1, 0, 0, 0, 0)
        ang, rcx, rcy = (0.0, 0.0, 0.0)
        if self.rot:
            rcx, rcy, f = self.rot
            ang = f(t)
        ca, sa = math.cos(ang), math.sin(ang)

        def T(pt):
            x, y = pt
            if ang:
                dx, dy = x - rcx, y - rcy
                x, y = rcx + dx * ca - dy * sa, rcy + dx * sa + dy * ca
            x = cx + sx * (x - cx) + tx
            y = cy + sy * (y - cy) + ty
            return lay.P(x, y)

        subs = self._sub(s, e)
        if self.fill is not None:
            fc = self.fill(t) if callable(self.fill) else self.fill
            ctx.set_source_rgba(*fc, a)
            for p in self.polys:
                q = [T(pt) for pt in p]
                ctx.move_to(*q[0])
                for pt in q[1:]:
                    ctx.line_to(*pt)
                ctx.close_path()
                ctx.fill()
        ctx.set_source_rgba(*col, a)
        ctx.set_line_width(self.lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        if self.dash:
            ctx.set_dash(self.dash, self.dash_v * t)
        for sub in subs:
            q = [T(pt) for pt in sub]
            ctx.move_to(*q[0])
            for pt in q[1:]:
                ctx.line_to(*pt)
            ctx.stroke()
        if self.dash:
            ctx.set_dash([])
        if self.tip and self.d_in > 0 and 0 < ui < 1 and subs:
            ex, ey = T(subs[-1][-1])
            ctx.set_source_rgba(*col, min(1.0, a * 1.2))
            ctx.arc(ex, ey, 4.6, 0, 2 * math.pi)
            ctx.fill()


class Text:
    """Texte incrusté, mot à mot, calé sur la voix."""

    def __init__(self, markup_p, markup_l, t_in, word_starts, t_out, d_out=0.7, size_p=84,
                 size_l=74, slot=None, font=SERIF, color=INK, reveal=0.55):
        self.mp, self.ml = markup_p, markup_l
        self.t_in, self.ws, self.t_out, self.d_out = t_in, word_starts, t_out, d_out
        self.sp, self.sl, self.slot, self.font, self.color, self.reveal = size_p, size_l, slot, font, color, reveal

    @staticmethod
    def parse(markup):
        lines = []
        for ln in markup.split("|"):
            ws = []
            for tok in ln.split(" "):
                ws.append((tok.replace("*", ""), tok.startswith("*")))
            lines.append(ws)
        return lines

    def draw(self, ctx, t, lay):
        if t < self.t_in:
            return
        fade = 1.0
        if self.t_out is not None and t > self.t_out:
            fade = 1 - e_io((t - self.t_out) / self.d_out)
            if fade <= 0:
                return
        portrait = lay.kind == "portrait"
        lines = self.parse(self.mp if portrait else self.ml)
        size = self.sp if portrait else self.sl
        lh = size * 1.16
        n_tot, first = self.slot if self.slot else (len(lines), 0)
        if portrait:
            cy = 1560.0
        else:
            cy = 540.0
        y0 = cy - n_tot * lh / 2 + lh * 0.80 + first * lh
        ctx.set_font_size(size)
        # indice global du mot
        widx = 0
        for li, ln in enumerate(lines):
            widths, space = [], 0.0
            for w, it in ln:
                ctx.select_font_face(self.font, cairo.FONT_SLANT_ITALIC if it else cairo.FONT_SLANT_NORMAL,
                                     cairo.FONT_WEIGHT_NORMAL)
                widths.append(ctx.text_extents(w).x_advance)
            ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            space = ctx.text_extents(" ").x_advance if self.font == SERIF else size * 0.26
            total = sum(widths) + space * (len(ln) - 1)
            x = lay.W / 2 - total / 2 if portrait else 110.0
            y = y0 + li * lh
            for (w, it), wd in zip(ln, widths):
                st = self.t_in + (self.ws[widx] if widx < len(self.ws) else 0.0)
                widx += 1
                k = e_out((t - st) / self.reveal)
                if k > 0:
                    ctx.select_font_face(self.font, cairo.FONT_SLANT_ITALIC if it else cairo.FONT_SLANT_NORMAL,
                                         cairo.FONT_WEIGHT_NORMAL)
                    ctx.set_font_size(size)
                    ctx.set_source_rgba(*self.color, k * fade)
                    ctx.move_to(x, y + 16 * (1 - k))
                    ctx.show_text(w)
                x += wd + space


# ── Construction de la scène ───────────────────────────────────────────────
GX0, GX1, GY, TOP = 140, 940, 1110, 330        # façade : x, sol, haut
PT = 470                                        # fond du local en plan
WT = 22                                         # épaisseur de mur
WIN = (180, 660)                                # baie de la vitrine
DOOR = (700, 900)                               # porte
END_FADE = 71.3                                 # fin du dessin → fond crème


def blend_starts(tm):
    """Mélange le minutage issu de la synthèse et une répartition au prorata des lettres."""
    words, dur, ws = tm["words"], tm["dur"], tm["word_starts"]
    cum, acc = [], 0.0
    for w in words:
        cum.append(acc)
        acc += len(w) + (2.5 if w[-1] in ",.:;" else 0.0) + 0.6
    prop = [dur * 0.97 * c / acc for c in cum]
    out = [0.5 * a + 0.5 * b for a, b in zip(ws, prop)]
    for i in range(1, len(out)):
        out[i] = max(out[i], out[i - 1] + 0.12)
    return out


def build(timings_path):
    tm = json.load(open(timings_path))
    els, texts = [], []
    add = els.append

    # ----------------------------------------------------------------- PLAN 1
    s_plan = lambda t: 1 - e_io((t - 10.3) / 1.7)                 # bascule du plan
    xf_plan = lambda t: (1, s_plan(t), 0, 0, 0, GY)
    am_plan = lambda t: max(0.0, s_plan(t)) ** 0.5
    kw = dict(xf=xf_plan, amul=am_plan, pencil=True, tip=True, t_out=None)

    outer = [(180, GY), (GX0, GY), (GX0, PT), (GX1, PT), (GX1, GY), (900, GY)]
    inner = [(180, GY - WT), (GX0 + WT, GY - WT), (GX0 + WT, PT + WT), (GX1 - WT, PT + WT),
             (GX1 - WT, GY - WT), (900, GY - WT)]
    add(El(outer, 0.7, 3.0, **kw))
    add(El(inner, 3.2, 2.5, **kw))
    add(El([[(180, GY), (180, GY - WT)], [(900, GY), (900, GY - WT)],
            [(660, GY), (700, GY), (700, GY - WT), (660, GY - WT), (660, GY)]], 5.4, 0.8, **kw))
    add(El([[(180, GY), (660, GY)], [(180, GY - 11), (660, GY - 11)], [(180, GY - WT), (660, GY - WT)]],
           5.9, 0.9, **kw))
    leaf = [(700, GY - WT), (700, GY - WT - 200)]
    add(El([leaf, arc(700, GY - WT, 200, -math.pi / 2, 0, 36)], 6.5, 1.1, **kw))
    # cloison de l'arrière-boutique
    part_a = [(GX0 + WT, 640), (400, 640)]
    part_b = [(470, 640), (526, 640), (526, PT + WT)]
    part_c = [(GX0 + WT, 654), (400, 654)]
    part_d = [(470, 654), (540, 654), (540, PT + WT)]
    add(El([part_a, part_b, part_c, part_d, [(400, 640), (400, 654)], [(470, 640), (470, 654)],
            [(526, PT + WT), (540, PT + WT)]], 7.0, 1.2, **kw))
    add(El(arc(470, 654, 64, -math.pi / 2, -math.pi, 20) + [], 7.8, 0.6, **kw))
    add(El([(470, 654), (470, 590)], 7.8, 0.4, **kw))
    # cotes (fines)
    add(El(cote(GX0, 432, GX1, 432) + [[(GX0, 440), (GX0, 424)], [(GX1, 440), (GX1, 424)]],
           8.2, 1.0, alpha=0.45, **kw))

    # ----------------------------------------------------------------- PLAN 2
    e_el = lambda t: e_io((t - 11.3) / 1.9)                       # l'élévation se lève
    xf_el = lambda t: (1, max(e_el(t), 1e-4), 0, 0, 0, GY)
    am_el = lambda t: min(1.0, e_el(t) * 3)
    ekw = dict(xf=xf_el, amul=am_el)
    add(El([(GX0, GY), (GX0, TOP), (GX1, TOP), (GX1, GY)], 11.0, 0.0, **ekw))
    # sol
    add(El([(GX0, GY), (100, GY)], 12.6, 0.3, pencil=True, out="retract", t_out=40.9, d_out=0.5))
    add(El([(GX0, GY), (GX1, GY)], 12.6, 0.8, pencil=True))
    add(El([(GX1, GY), (980, GY)], 13.4, 0.3, pencil=True, out="retract", t_out=40.9, d_out=0.5))
    # bandeau d'enseigne — resté vide ; devient orange en P3
    band_col = lambda t: mix(NAVY, ORANGE, (t - 29.8) / 1.0)
    add(El(rect(180, 360, 900, 450), 13.5, 1.1, pencil=True, tip=True, color=band_col, t_out=39.0))
    add(El(rect(192, 372, 888, 438), 14.2, 1.0, pencil=True, color=band_col, t_out=39.0))
    # vitrine
    V = lambda *a, **k: El(*a, t_out=39.5, **k)
    add(V(rect(180, 510, 660, 1050), 14.6, 1.3, pencil=True, tip=True))
    add(V(rect(194, 524, 646, 1036), 15.3, 1.2, pencil=True))
    add(V([[(420, 524), (420, 1036)], [(194, 700), (646, 700)]], 16.0, 0.9, pencil=True))
    # porte + seuil
    D = lambda *a, **k: El(*a, t_out=40.0, **k)
    add(D([(700, GY), (700, 640), (900, 640), (900, GY)], 15.8, 1.2, pencil=True, tip=True))
    add(D([(714, GY - 14), (714, 654), (886, 654), (886, GY - 14)], 16.5, 1.0, pencil=True))
    add(D([rect(736, 690, 864, 900), [(728, 960), (728, 1020)]], 17.1, 0.8, pencil=True))
    add(D(rect(688, GY - 14, 912, GY), 17.6, 0.6, pencil=True))
    # cote de hauteur (fine)
    add(El(cote(100, TOP, 100, GY) + [[(92, TOP), (108, TOP)], [(92, GY), (108, GY)]],
           17.9, 1.0, alpha=0.45, pencil=True, out="retract", t_out=44.2, d_out=0.8))
    add(El(cote(GX0, 296, GX1, 296) + [[(GX0, 304), (GX0, 288)], [(GX1, 304), (GX1, 288)]],
           41.3, 1.0, alpha=0.45, out="retract", t_out=44.6, d_out=0.8))

    # trottoir : joints, bordure (P2) → ligne nue (P3)
    joints = [[(100 + 120 * k, GY), (100 + 120 * k, 1190)] for k in range(8)] + [[(980, GY), (980, 1190)]]
    add(El([(100, 1190), (980, 1190)], 19.0, 1.4, pencil=True, out="retract", t_out=28.9, d_out=1.4))
    add(El(joints, 20.0, 2.4, pencil=True, alpha=0.8, out="retract", t_out=28.2, d_out=1.4))
    # passages (traits pointillés qui défilent) — P3
    for i, (y, v) in enumerate([(1134, 70), (1158, -55), (1176, 85)]):
        add(El([(100, y), (980, y)], 24.2 + 0.3 * i, 0.9, inmode="fade", alpha=0.55, dash=[24, 22],
               dash_v=v, out="fade", t_out=27.7 + 0.25 * i, d_out=1.2))

    # ----------------------------------------------------------------- PLAN 4
    def popxf(t0, cx, cy, k=0.05):
        def f(t):
            s = 1 + k * (1 - e_out((t - t0) / 0.35))
            return (s, s, 0, 0, cx, cy)
        return f
    flash = lambda t0: (lambda t: mix(ORANGE, NAVY, (t - t0 - 0.15) / 0.7))

    t1, t2, t3 = 39.0, 39.5, 40.0                    # trois déclics, une demi-seconde d'écart
    # 1. bandeau → barre d'adresse
    add(El(rrect(330, 376, 880, 434, 29), t1, 0, color=flash(t1), xf=popxf(t1, 605, 405)))
    add(El([circle(216, 405, 9), circle(250, 405, 9), circle(284, 405, 9)], t1, 0, color=flash(t1),
           xf=popxf(t1, 250, 405)))
    add(El([(364, 405), (580, 405)], t1, 0, color=flash(t1), alpha=0.7))
    # 2. vitrine → zone de contenu
    add(El(rrect(180, 510, 660, 1050, 14), t2, 0, color=flash(t2), xf=popxf(t2, 420, 780, 0.03)))
    # 3. seuil → bouton
    btn = rrect(700, 1000, 900, 1076, 38)
    add(El(btn, t3, 0, color=ORANGE, fill=ORANGE, xf=popxf(t3, 800, 1038, 0.08)))
    add(El([[(768, 1038), (832, 1038)], [(816, 1022), (832, 1038), (816, 1054)]], t3, 0, color=CREAM,
           xf=popxf(t3, 800, 1038, 0.08), lw=3.4))
    # filet sous la barre d'adresse (cadre de la fenêtre)
    add(El([(GX0, 470), (GX1, 470)], 41.2, 1.0))

    # ----------------------------------------------------------------- PLAN 5
    def drop(t0, dy=-26.0, d=0.7):
        return lambda t: (1, 1, 0, dy * (1 - e_out((t - t0) / d)), 0, 0)

    def block(polys, t0, d=0.8, t_out=END_FADE + 5, **k):
        return El(polys, t0, d, xf=drop(t0), out="fade", t_out=t_out, ease=e_out, **k)

    tA, tB, tC, tD = 51.2, 52.9, 54.6, 56.1
    R1, R2, R3 = 65.0, 67.6, 70.2                   # instants où les révisions s'appliquent
    # A — l'entrée (bandeau d'accroche) ; le titre est une pièce à part (il sera révisé)
    add(block([rrect(196, 526, 644, 690, 8), rrect(218, 640, 330, 670, 15)], tA, 0.9))
    add(block([(218, 576), (500, 576)], tA + 0.15, 0.7, t_out=R1))
    add(block([(218, 610), (420, 610)], tA + 0.25, 0.7, t_out=R1))
    # B — le parcours (trois cartes) ; l'image de la carte 2 sera révisée
    cards = []
    for k in range(3):
        x = 196 + 155 * k
        cards += [rrect(x, 722, x + 138, 880, 8), [(x + 14, 840), (x + 100, 840)], [(x + 14, 862), (x + 70, 862)]]
        if k != 1:
            cards.append(rect(x + 14, 738, x + 124, 812))
    add(block(cards, tB, 1.0))
    add(block(rect(365, 738, 475, 812), tB + 0.3, 0.7, t_out=R2))
    # C — la raison de rester
    add(block([rrect(196, 912, 644, 1034, 8), circle(232, 952, 16), [(264, 946), (560, 946)],
               [(264, 970), (480, 970)], [(218, 1004), (430, 1004)]], tC, 0.9))
    # D — colonne latérale
    add(block([rrect(700, 510, 900, 940, 8), circle(800, 592, 44), [(728, 680), (872, 680)],
               [(728, 712), (840, 712)], [(728, 744), (860, 744)], rect(728, 790, 872, 910)], tD, 0.9))
    # lignes de cote : apparaissent puis s'effacent
    def cote_el(polys, t0):
        return El(polys, t0, 0.55, alpha=0.8, out="retract", t_out=t0 + 1.55, d_out=0.55)
    add(cote_el(cote(680, 526, 680, 690), tA + 0.9))
    add(cote_el(cote(196, 706, 334, 706), tB + 1.0))
    add(cote_el(cote(680, 912, 680, 1034), tC + 0.9))
    add(cote_el(cote(700, 966, 900, 966), tD + 0.9))
    add(cote_el(cote(180, 1082, 660, 1082), tD + 2.3))

    # ----------------------------------------------------------------- PLAN 6
    # frise de durée sous la fenêtre : un repère par révision
    add(El([(GX0, 1176), (GX1, 1176)], 62.9, 0.9, alpha=0.5))
    for tk, x in zip((R1 + 0.5, R2 + 0.5, R3 + 0.5), (300, 540, 780)):
        add(El([(x, 1160), (x, 1192)], tk, 0, xf=popxf(tk, x, 1176, 0.12),
               color=lambda t, tk=tk: mix(ORANGE, NAVY, (t - tk - 0.2) / 0.6)))

    def calque(t_in, t_out, rev, glyph_xy):
        """Un calque translucide se superpose, marque la révision, puis se retire."""
        sheet = rrect(112, 304, 968, 1142, 6)
        slide = lambda t: (1, 1, 110 * (1 - e_out((t - t_in) / 0.8)) + 80 * e_io((t - t_out) / 0.7), 0, 0, 0)
        gate = lambda t: min(e_out((t - t_in) / 0.6), 1 - e_io((t - t_out) / 0.7))
        add(El(sheet, t_in, 0, fill=CREAM, alpha=0.84, amul=gate, xf=slide, color=NAVY))
        add(El(rev, t_in + 0.7, 0.7, color=ORANGE, amul=gate, xf=slide, ease=e_out))
        gx, gy = glyph_xy
        g = arc(gx, gy, 24, -math.pi * 0.35, math.pi * 1.45, 26)
        head = [(g[-1][0] - 4, g[-1][1] - 15), g[-1], (g[-1][0] + 14, g[-1][1] - 5)]
        add(El([g, head], t_in + 0.8, 0.0, color=ORANGE, amul=gate, xf=slide,
               rot=(gx, gy, lambda t: 2 * math.pi * e_io((t - t_in - 0.8) / 1.0))))

    # révision 1 : l'accroche s'allonge
    add(El([[(218, 576), (580, 576)], [(218, 610), (500, 610)]], R1, 0,
           xf=popxf(R1, 400, 595, 0.03)))
    calque(62.9, R1 - 0.1, rrect(208, 556, 600, 626, 8), (900, 346))
    # révision 2 : une carte change de visuel
    add(El([circle(420, 775, 30), [(368, 812), (472, 812)]], R2, 0, xf=popxf(R2, 420, 775, 0.06)))
    calque(65.6, R2 - 0.1, rrect(356, 730, 486, 820, 6), (900, 346))
    # révision 3 : la colonne s'enrichit
    add(El([(728, 776), (800, 776)], R3, 0, xf=popxf(R3, 760, 776, 0.1)))
    calque(68.2, R3 - 0.1, rrect(716, 764, 884, 790, 6), (900, 346))

    # ------------------------------------------------------------- P7 (texte)
    # ------------------------------------------------------------------ TEXTES
    def ws(lid):
        return blend_starts(tm[lid])

    def T(lid, mp, ml, t_out, **k):
        texts.append(Text(mp, ml, tm[lid]["start"], ws(lid), t_out, **k))

    T("L1", "Un lieu, ça se dessine|avant d'exister.", "Un lieu, ça se dessine|avant d'exister.", 9.3)
    T("L2", "Pendant trois ans,|j'ai appris à dessiner des lieux|où l'on a envie d'entrer.",
      "Pendant trois ans,|j'ai appris à dessiner|des lieux où l'on a|envie d'entrer.", 22.2, size_p=78, size_l=70)
    # Plan 3 : deux phrases, deux temps
    texts.append(Text("Puis j'ai regardé la rue.", "Puis j'ai regardé la rue.", tm["L3a"]["start"],
                      ws("L3a"), 34.2, slot=(2, 0), size_p=80, size_l=70))
    texts.append(Text("Plus personne ne passe devant.", "Plus personne ne|passe devant.", tm["L3b"]["start"],
                      ws("L3b"), 34.2, slot=(2, 1), size_p=80, size_l=70))
    T("L4", "La vitrine|a changé de *place*.", "La vitrine|a changé de *place*.", 46.8, size_p=92, size_l=84)
    # Plan 5 : le titre, puis trois repères qui se substituent
    w5 = ws("L5")
    s5 = tm["L5"]["start"]
    head = "Une page se compose|comme un espace\u00a0:"
    texts.append(Text(head, head, s5, w5[:7], s5 + w5[7] - 0.75, d_out=0.55))
    for k, (txt, wi) in enumerate([("une entrée,", 7), ("un parcours,", 9), ("une raison de rester.", 11)]):
        texts.append(Text(txt, txt, s5 + w5[wi] - 0.05, [0.0] * len(txt.split(" ")), 61.2, slot=(3, k),
                          size_p=84, size_l=76))
    # le premier repère n'apparaît qu'une fois le titre effacé
    T("L6", "Et comme un lieu,|elle s'entretient.", "Et comme un lieu,|elle s'entretient.", 70.8, size_p=84, size_l=78)

    return els, texts, tm


class Signature:
    """Plan 7 : fond crème, logo, une ligne de contact (silencieux)."""

    def draw(self, ctx, t, lay):
        t0 = 72.4
        if t < t0:
            return
        portrait = lay.kind == "portrait"
        cx = lay.W / 2
        cy = 930 if portrait else 470
        size = 124 if portrait else 136
        k = e_out((t - t0) / 1.1)
        ctx.set_font_size(size)
        ctx.select_font_face(SERIF, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        w1 = ctx.text_extents("Vecteur ")
        ctx.select_font_face(SERIF, cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
        w2 = ctx.text_extents("d'excellence")
        total = w1.x_advance + w2.x_advance
        x = cx - total / 2
        y = cy + 14 * (1 - k)
        ctx.set_source_rgba(*NAVY, k)
        ctx.select_font_face(SERIF, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.move_to(x, y)
        ctx.show_text("Vecteur ")
        ctx.select_font_face(SERIF, cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
        ctx.move_to(x + w1.x_advance, y)
        ctx.show_text("d'excellence")
        # filet orange (seul accent)
        u = e_io((t - 73.3) / 0.7)
        if u > 0:
            ctx.set_source_rgba(*ORANGE, 1)
            ctx.set_line_width(LW)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(cx - 40 * u, cy + 56)
            ctx.line_to(cx + 40 * u, cy + 56)
            ctx.stroke()
        k2 = e_out((t - 73.9) / 0.9)
        if k2 > 0:
            ctx.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(38 if portrait else 42)
            txt = "vecteur.excellence@gmail.com"
            ext = ctx.text_extents(txt)
            ctx.set_source_rgba(*INK, k2)
            ctx.move_to(cx - ext.x_advance / 2, cy + 128 + 10 * (1 - k2))
            ctx.show_text(txt)


class Scene:
    def __init__(self, timings_path):
        self.els, self.texts, self.tm = build(timings_path)
        self.sig = Signature()

    def render(self, ctx, t, lay):
        ctx.set_source_rgb(*CREAM)
        ctx.paint()
        g = 1 - e_io((t - END_FADE) / 0.9)
        if g > 0:
            for e in self.els:
                e.draw(ctx, t, lay, g)
        for tx in self.texts:
            tx.draw(ctx, t, lay)
        self.sig.draw(ctx, t, lay)

    def pencil_envelope(self, rate=200):
        n = int(DUR * rate)
        env = [0.0] * n
        for e in self.els:
            if not e.pencil:
                continue
            i0, i1 = int(e.t_in * rate), int((e.t_in + e.d_in) * rate) + 1
            for i in range(max(i0, 0), min(i1, n)):
                env[i] += e.speed(i / rate)
        return env
