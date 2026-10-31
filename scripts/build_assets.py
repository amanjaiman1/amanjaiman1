#!/usr/bin/env python3
"""Generate every animated SVG in assets/ from content.py.

    pip install fonttools brotli pillow
    python3 scripts/build_assets.py

Design rules the output follows, so it renders the same on github.com in every browser:
  * Each SVG is self-contained: fonts are subset and embedded as WOFF2 data URIs, screenshots as
    JPEG data URIs. SVGs shown through <img> cannot load anything external.
  * Every SVG paints its own dark card, so it reads the same on GitHub's light and dark themes.
  * The un-animated state is the finished state. Animations only run *towards* it, so a renderer
    without animation support, or a visitor with "reduce motion" switched on, still sees everything.
  * Only CSS keyframes and SMIL are used. No scripts (GitHub strips them anyway).
"""
from __future__ import annotations

import base64
import html
import io
import math
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from fontTools import subset as ftsubset
from fontTools.ttLib import TTFont
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = ROOT / "assets"
sys.path.insert(0, str(HERE))
import content as C  # noqa: E402

# --------------------------------------------------------------------------- palette
BG = "#070A13"
PANEL = "#0B1020"
PANEL2 = "#0E1528"
LINE = "#1E293B"
TEXT = "#E6EDF7"
MUTED = "#94A3B8"
DIM = "#64748B"
CYAN = "#22D3EE"
SKY = "#38BDF8"
VIOLET = "#A78BFA"
PURPLE = "#7C3AED"
PINK = "#F472B6"
GREEN = "#34D399"
AMBER = "#FBBF24"
NAMED = {"text": TEXT, "muted": MUTED, "dim": DIM, "cyan": CYAN, "sky": SKY, "violet": VIOLET,
         "pink": PINK, "green": GREEN, "amber": AMBER}

SANS_FALLBACK = "'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif"
MONO_FALLBACK = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


# --------------------------------------------------------------------------- fonts
class Font:
    def __init__(self, key: str, filename: str, family: str, weight: int, css_class: str, fallback: str):
        self.key, self.family, self.weight, self.css_class, self.fallback = key, family, weight, css_class, fallback
        self.path = HERE / "fonts" / filename
        tt = TTFont(self.path)
        self.cmap = tt.getBestCmap()
        self.adv = tt["hmtx"].metrics
        self.upm = tt["head"].unitsPerEm

    def width(self, s: str, size: float, ls: float = 0.0) -> float:
        total = 0
        for ch in s:
            glyph = self.cmap.get(ord(ch))
            if glyph is None:
                raise ValueError(f"font {self.path.name} has no glyph for {ch!r} (in {s!r})")
            total += self.adv[glyph][0]
        return total * size / self.upm + ls * len(s)


FONTS = {
    "d": Font("d", "SpaceGrotesk-Bold.ttf", "SG", 700, "fd", SANS_FALLBACK),
    "s": Font("s", "SpaceGrotesk-Medium.ttf", "SG", 500, "fs", SANS_FALLBACK),
    "m": Font("m", "JetBrainsMono-Medium.ttf", "JB", 500, "fm", MONO_FALLBACK),
    "mb": Font("mb", "JetBrainsMono-Bold.ttf", "JB", 700, "fmb", MONO_FALLBACK),
}
_subset_cache: dict[tuple[str, str], str] = {}


def woff2_subset(font: Font, chars: str) -> str:
    key = (font.key, chars)
    if key not in _subset_cache:
        opts = ftsubset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        opts.hinting = False
        opts.desubroutinize = True
        tt = ftsubset.load_font(str(font.path), opts)
        sub = ftsubset.Subsetter(opts)
        sub.populate(text=chars)
        sub.subset(tt)
        buf = io.BytesIO()
        ftsubset.save_font(tt, buf, opts)
        _subset_cache[key] = base64.b64encode(buf.getvalue()).decode()
    return _subset_cache[key]


# --------------------------------------------------------------------------- svg builder
def n(v: float) -> str:
    """Compact number formatting for coordinates."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pct(frac: float) -> str:
    return f"{max(0.0, min(100.0, frac * 100)):.3f}".rstrip("0").rstrip(".") + "%"


def esc(s: str) -> str:
    return html.escape(s, quote=False)


class Svg:
    def __init__(self, w: float, h: float, title: str, desc: str):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.defs: list[str] = []
        self.css: list[str] = []
        self._css_seen: set[str] = set()
        self.body: list[str] = []
        self.chars: dict[str, set[str]] = defaultdict(set)
        self._uid = 0

    def uid(self, prefix: str = "i") -> str:
        self._uid += 1
        return f"{prefix}{self._uid}"

    def add(self, *parts: str) -> None:
        self.body.extend(parts)

    def style(self, rule: str) -> None:
        if rule not in self._css_seen:
            self._css_seen.add(rule)
            self.css.append(rule)

    def use_chars(self, font: str, s: str) -> None:
        FONTS[font].width(s, 10)  # raises early if a glyph is missing
        self.chars[font].update(s)

    def text(self, x, y, s, font="s", size=16, fill=TEXT, anchor=None, ls=None, opacity=None,
             cls="", fit=False, extra="") -> str:
        """Return a <text> element (call add() yourself). fit=True pins the width with textLength."""
        self.use_chars(font, s)
        f = FONTS[font]
        a = [f'x="{n(x)}"', f'y="{n(y)}"', f'class="{f.css_class}{" " + cls if cls else ""}"', f'font-size="{n(size)}"']
        if fill:
            a.append(f'fill="{fill}"')
        if anchor:
            a.append(f'text-anchor="{anchor}"')
        if ls:
            a.append(f'letter-spacing="{n(ls)}"')
        if opacity is not None:
            a.append(f'opacity="{n(opacity)}"')
        if fit:
            a.append(f'textLength="{n(f.width(s, size, ls or 0))}" lengthAdjust="spacingAndGlyphs"')
        if extra:
            a.append(extra)
        return f"<text {' '.join(a)}>{esc(s)}</text>"

    def render(self) -> str:
        font_css = []
        for key in sorted(self.chars):
            f = FONTS[key]
            data = woff2_subset(f, "".join(sorted(self.chars[key] | {" "})))
            font_css.append(f"@font-face{{font-family:{f.family};font-weight:{f.weight};font-style:normal;"
                            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")
        classes = "".join(
            f".{f.css_class}{{font-family:{f.family},{f.fallback};font-weight:{f.weight}}}" for f in FONTS.values())
        reduce = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{n(self.w)}" height="{n(self.h)}" viewBox="0 0 {n(self.w)} {n(self.h)}" fill="none" '
            f'role="img" aria-labelledby="title desc">'
            f'<title id="title">{esc(self.title)}</title><desc id="desc">{esc(self.desc)}</desc>'
            f'<style>{"".join(font_css)}{classes}{"".join(self.css)}{reduce}</style>'
            f'<defs>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>'
        )

    def save(self, name: str) -> Path:
        out = ASSETS / name
        out.write_text(self.render(), encoding="utf-8")
        return out


# --------------------------------------------------------------------------- shared components
def card(s: Svg, w: float, h: float, r: float = 22, tint: str = CYAN, accent2: str = PINK) -> tuple[str, str]:
    """Dark card background. Returns (clip id, border element) - add the border last."""
    g = s.uid("c")
    s.defs.append(
        f'<linearGradient id="{g}b" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{tint}" stop-opacity=".55"/><stop offset=".45" stop-color="{VIOLET}" stop-opacity=".14"/>'
        f'<stop offset="1" stop-color="{accent2}" stop-opacity=".42"/></linearGradient>'
        f'<radialGradient id="{g}g" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate({n(w * .1)} 0) scale({n(w * .75)} {n(h * 1.2)})">'
        f'<stop offset="0" stop-color="{tint}" stop-opacity=".11"/><stop offset="1" stop-color="{tint}" stop-opacity="0"/>'
        f'</radialGradient><clipPath id="{g}c"><rect width="{n(w)}" height="{n(h)}" rx="{n(r)}"/></clipPath>')
    s.add(f'<rect width="{n(w)}" height="{n(h)}" rx="{n(r)}" fill="{BG}"/>',
          f'<rect width="{n(w)}" height="{n(h)}" rx="{n(r)}" fill="url(#{g}g)"/>')
    border = f'<rect x=".5" y=".5" width="{n(w - 1)}" height="{n(h - 1)}" rx="{n(r - .5)}" stroke="url(#{g}b)"/>'
    return f"{g}c", border


def dot_grid(s: Svg, x, y, w, h, step=22, color="#1A2438", cx=.5, cy=.4) -> None:
    p, m, rg = s.uid("p"), s.uid("m"), s.uid("r")
    s.defs.append(
        f'<pattern id="{p}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
        f'<circle cx="1.2" cy="1.2" r="1.2" fill="{color}"/></pattern>'
        f'<radialGradient id="{rg}" cx="{cx}" cy="{cy}" r=".75"><stop offset="0" stop-color="#fff"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        f'<mask id="{m}"><rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="url(#{rg})"/></mask>')
    s.add(f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="url(#{p})" mask="url(#{m})"/>')


def corner_brackets(s: Svg, w, h, inset=14, size=16, color=CYAN, op=.5) -> None:
    d = []
    for (x, y, dx, dy) in [(inset, inset, 1, 1), (w - inset, inset, -1, 1), (inset, h - inset, 1, -1), (w - inset, h - inset, -1, -1)]:
        d.append(f"M{n(x)} {n(y + dy * size)}V{n(y)}H{n(x + dx * size)}")
    s.add(f'<path d="{"".join(d)}" stroke="{color}" stroke-opacity="{op}" stroke-width="1.5" stroke-linecap="round"/>')


def header(s: Svg, x, y, kicker: str, title: str, right: float) -> None:
    """Section header: mono kicker, display title, hairline with a travelling glint."""
    s.add(s.text(x, y, kicker, "mb", 12.5, CYAN, ls=2.6))
    s.add(s.text(x, y + 38, title, "d", 30, TEXT))
    x1 = x + FONTS["d"].width(title, 30) + 26
    if right - x1 < 60:
        return
    yy = y + 27
    s.style("@keyframes glint{0%{stroke-dashoffset:120}55%,100%{stroke-dashoffset:-1000}}")
    s.style(".glint{stroke-dasharray:120 1100;animation:glint 5.5s cubic-bezier(.6,0,.3,1) infinite}")
    gid = s.uid("hg")
    s.defs.append(f'<linearGradient id="{gid}" x1="{n(x1)}" x2="{n(right)}" gradientUnits="userSpaceOnUse">'
                  f'<stop stop-color="{CYAN}"/><stop offset=".5" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>')
    s.add(f'<path d="M{n(x1)} {n(yy)}H{n(right)}" stroke="{LINE}"/>',
          f'<path class="glint" d="M{n(x1)} {n(yy)}H{n(right)}" pathLength="1000" stroke="url(#{gid})" stroke-width="2" stroke-linecap="round"/>')


def wrap(text: str, font: str, size: float, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if FONTS[font].width(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def pill(s: Svg, x, y, label: str, color: str, size=10.5, pad=10, h=22, dot=False, anchor_right=False) -> float:
    """Rounded label. Returns its width. With anchor_right, x is the right edge."""
    tw = FONTS["mb"].width(label, size, 1.2)
    w = tw + pad * 2 + (14 if dot else 0)
    x0 = x - w if anchor_right else x
    s.add(f'<rect x="{n(x0)}" y="{n(y)}" width="{n(w)}" height="{h}" rx="{h / 2}" fill="{color}" fill-opacity=".09" '
          f'stroke="{color}" stroke-opacity=".38"/>')
    tx = x0 + pad
    if dot:
        cx, cy = x0 + pad + 3, y + h / 2
        s.style("@keyframes ping{0%{transform:scale(.6);opacity:.9}70%,100%{transform:scale(2.6);opacity:0}}")
        s.style(".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.2s cubic-bezier(.2,.6,.3,1) infinite;opacity:0}")
        s.add(f'<circle class="ping" cx="{n(cx)}" cy="{n(cy)}" r="3.2" fill="{color}"/>',
              f'<circle cx="{n(cx)}" cy="{n(cy)}" r="3.2" fill="{color}"/>')
        tx += 14
    s.add(s.text(tx, y + h / 2 + size * .36, label, "mb", size, color, ls=1.2))
    return w


# --------------------------------------------------------------------------- hero
def typing_loop(s: Svg, x, y, phrases, size=19, color=TEXT, type_dt=.055, hold=1.9, del_dt=.026, gap=.4):
    """Type a phrase, hold, delete it, type the next. SMIL with one value per keystroke."""
    cw = FONTS["m"].width("M", size)
    t, slots = 0.0, []
    for p in phrases:
        start = t
        typed = start + len(p) * type_dt
        del_start = typed + hold
        end = del_start + len(p) * del_dt
        slots.append((p, start, end))
        t = end + gap
    T = t
    times, widths = [], []
    for p, start, _end in slots:
        k = len(p)
        for i in range(k + 1):
            times.append(start + i * type_dt)
            widths.append(i * cw)
        del_start = start + k * type_dt + hold
        for i in range(k - 1, -1, -1):
            times.append(del_start + (k - i) * del_dt)
            widths.append(i * cw)
    # keyTimes must start at 0 and never go backwards
    kt, last = [], -1.0
    for tt in times:
        v = max(tt / T, last + 1e-5)
        kt.append(v)
        last = v
    kt[0] = 0.0
    key_times = ";".join(f"{v:.5f}" for v in kt)
    clip = s.uid("tc")
    full0 = len(phrases[0]) * cw
    s.defs.append(
        f'<clipPath id="{clip}"><rect x="{n(x)}" y="{n(y - size * 1.05)}" width="{n(full0)}" height="{n(size * 1.45)}">'
        f'<animate attributeName="width" values="{";".join(n(v) for v in widths)}" keyTimes="{key_times}" '
        f'dur="{T:.3f}s" calcMode="discrete" repeatCount="indefinite"/></rect></clipPath>')
    parts = [f'<g clip-path="url(#{clip})">']
    for i, (p, start, end) in enumerate(slots):
        vis = "visible" if i == 0 else "hidden"
        if i == 0:
            anim = f'values="visible;hidden" keyTimes="0;{end / T:.5f}"'
        else:
            anim = f'values="hidden;visible;hidden" keyTimes="0;{start / T:.5f};{end / T:.5f}"'
        t_el = s.text(x, y, p, "m", size, color, fit=True, extra=f'visibility="{vis}"')
        t_el = t_el.replace("</text>", f'<animate attributeName="visibility" {anim} dur="{T:.3f}s" calcMode="discrete" repeatCount="indefinite"/></text>')
        parts.append(t_el)
    parts.append("</g>")
    s.add(*parts)
    s.style("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}")
    s.style(".blink{animation:blink 1.05s steps(1,end) infinite}")
    s.add(f'<rect class="blink" x="{n(x + full0 + 2)}" y="{n(y - size * .82)}" width="{n(size * .52)}" height="{n(size * 1.02)}" rx="1.5" fill="{CYAN}">'
          f'<animate attributeName="x" values="{";".join(n(x + v + 2) for v in widths)}" keyTimes="{key_times}" '
          f'dur="{T:.3f}s" calcMode="discrete" repeatCount="indefinite"/></rect>')


def radar(s: Svg, cx, cy, R, blips, T=6.0) -> None:
    disc, sweep_g = s.uid("rd"), s.uid("sw")
    s.defs.append(
        f'<radialGradient id="{disc}"><stop offset="0" stop-color="#0E2236"/><stop offset=".7" stop-color="#0A1426"/>'
        f'<stop offset="1" stop-color="#081020"/></radialGradient>')
    halo = s.uid("ha")
    s.defs.append(f'<radialGradient id="{halo}"><stop offset=".55" stop-color="{CYAN}" stop-opacity=".16"/>'
                  f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>')
    s.add(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(R * 1.32)}" fill="url(#{halo})"/>',
          f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(R)}" fill="url(#{disc})"/>')
    for frac, op in [(1, .42), (.75, .22), (.5, .2), (.25, .16)]:
        s.add(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(R * frac)}" stroke="{CYAN}" stroke-opacity="{op}"/>')
    s.add(f'<path d="M{n(cx - R)} {n(cy)}H{n(cx + R)}M{n(cx)} {n(cy - R)}V{n(cy + R)}" stroke="{CYAN}" stroke-opacity=".12"/>')
    ticks = []
    for k in range(72):
        a = math.radians(k * 5)
        inner = R - (10 if k % 6 == 0 else 4.5)
        ticks.append(f"M{n(cx + inner * math.cos(a))} {n(cy + inner * math.sin(a))}L{n(cx + R * math.cos(a))} {n(cy + R * math.sin(a))}")
    s.add(f'<path d="{"".join(ticks)}" stroke="{CYAN}" stroke-opacity=".38"/>')
    s.style("@keyframes spin{to{transform:rotate(360deg)}}")
    origin = f"transform-origin:{n(cx)}px {n(cy)}px"
    s.style(f".spinslow{{animation:spin 70s linear infinite;{origin}}}")
    s.style(f".spinrev{{animation:spin 40s linear infinite reverse;{origin}}}")
    s.style(f".sweep{{animation:spin {T}s linear infinite;{origin}}}")
    s.add(f'<circle class="spinslow" cx="{n(cx)}" cy="{n(cy)}" r="{n(R + 10)}" stroke="{CYAN}" stroke-opacity=".4" stroke-dasharray="2 7"/>',
          f'<circle class="spinrev" cx="{n(cx)}" cy="{n(cy)}" r="{n(R * .62)}" stroke="{VIOLET}" stroke-opacity=".45" stroke-dasharray="46 16 4 16"/>')
    # sweep: 36 thin slices fading out behind the leading edge (a conic gradient, done by hand)
    slices = []
    count, span = 36, 2.0
    for k in range(count):
        a2 = math.radians(-k * span)
        a1 = math.radians(-(k + 1) * span - .5)
        op = .34 * (1 - k / count) ** 1.8
        slices.append(
            f'<path d="M{n(cx)} {n(cy)}L{n(cx + R * math.cos(a1))} {n(cy + R * math.sin(a1))}'
            f'A{n(R)} {n(R)} 0 0 1 {n(cx + R * math.cos(a2))} {n(cy + R * math.sin(a2))}Z" fill="{CYAN}" fill-opacity="{op:.3f}"/>')
    s.add(f'<g class="sweep">{"".join(slices)}<path d="M{n(cx)} {n(cy)}H{n(cx + R)}" stroke="{CYAN}" stroke-width="2" stroke-linecap="round"/></g>')
    # blips flash exactly when the sweep passes over them
    s.style(f"@keyframes blip{{0%,6%{{opacity:1}}70%,100%{{opacity:.32}}}}")
    s.style(f"@keyframes bping{{0%{{transform:scale(.3);opacity:.95}}30%,100%{{transform:scale(2.5);opacity:0}}}}")
    s.style(f"@keyframes blbl{{0%,12%{{opacity:1}}80%,100%{{opacity:.55}}}}")
    s.style(f".blip{{animation:blip {T}s linear infinite}}.blbl{{animation:blbl {T}s linear infinite}}"
            f".bping{{transform-box:fill-box;transform-origin:center;animation:bping {T}s cubic-bezier(.2,.6,.3,1) infinite;opacity:0}}")
    for label, ang, rf in blips:
        a = math.radians(ang)
        bx, by = cx + R * rf * math.cos(a), cy + R * rf * math.sin(a)
        delay = f"animation-delay:{ang / 360 * T - T:.3f}s"
        right_side = math.cos(a) > 0.15
        lx = bx - 9 if right_side else bx + 9
        anchor = "end" if right_side else "start"
        s.add(f'<circle class="bping" style="{delay}" cx="{n(bx)}" cy="{n(by)}" r="5" stroke="{CYAN}" stroke-width="1.5"/>',
              f'<circle class="blip" style="{delay}" cx="{n(bx)}" cy="{n(by)}" r="3.6" fill="{CYAN}"/>',
              s.text(lx, by + 3.6, label, "mb", 10, TEXT, anchor=anchor, ls=1.1, cls="blbl", extra=f'style="{delay}"'))
    s.add(f'<circle class="ping" cx="{n(cx)}" cy="{n(cy)}" r="4" fill="{CYAN}"/>',
          f'<circle cx="{n(cx)}" cy="{n(cy)}" r="4" fill="{CYAN}"/>')
    s.style("@keyframes ping{0%{transform:scale(.6);opacity:.9}70%,100%{transform:scale(2.6);opacity:0}}")
    s.style(".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.2s cubic-bezier(.2,.6,.3,1) infinite;opacity:0}")


def build_hero() -> Path:
    W, H = 1000, 420
    s = Svg(W, H, f"{C.NAME} — {C.ROLE}",
            f"{C.NAME}. {C.ROLE}. {C.STATUS.title()}. A radar sweeps over the live products: "
            + ", ".join(b[0].title() for b in C.RADAR_BLIPS) + ".")
    clip, border = card(s, W, H, 26)
    s.add(f'<g clip-path="url(#{clip})">')
    s.style("@keyframes drift1{to{transform:translate(70px,40px)}}@keyframes drift2{to{transform:translate(-60px,50px)}}"
            "@keyframes drift3{to{transform:translate(50px,-40px)}}")
    for i, (bx, by, r, col, op, dur) in enumerate([(170, 30, 320, CYAN, .2, 17), (870, 110, 340, PURPLE, .3, 21), (520, 470, 300, PINK, .14, 19)]):
        g = s.uid("ab")
        s.defs.append(f'<radialGradient id="{g}"><stop offset="0" stop-color="{col}" stop-opacity="{op}"/>'
                      f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>')
        s.add(f'<circle cx="{bx}" cy="{by}" r="{r}" fill="url(#{g})" style="animation:drift{i + 1} {dur}s ease-in-out infinite alternate"/>')
    dot_grid(s, 0, 0, W, H, cx=.3, cy=.35)
    rnd = random.Random(42)
    s.style("@keyframes twinkle{0%,100%{opacity:.15}50%{opacity:.95}}")
    stars = []
    keep_clear = [(50, 44, 450, 86), (50, 96, 620, 286), (50, 312, 480, 392)]  # text blocks on the left
    while len(stars) < 46:
        x, y = rnd.uniform(20, W - 20), rnd.uniform(18, H - 18)
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in keep_clear):
            continue
        stars.append(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(rnd.uniform(.5, 1.35))}" fill="#CFE8FF" '
                     f'style="animation:twinkle {rnd.uniform(2.4, 5.6):.2f}s ease-in-out {-rnd.uniform(0, 5):.2f}s infinite"/>')
    s.add(*stars)
    corner_brackets(s, W, H)

    x0 = 58
    pill(s, x0, 50, C.STATUS, GREEN, size=11.5, h=30, pad=13, dot=True)
    # name with a slowly travelling gradient and a soft glow underneath
    name_size = 76
    name_w = FONTS["d"].width(C.NAME, name_size)
    ng, glow = s.uid("ng"), s.uid("gl")
    s.defs.append(
        f'<linearGradient id="{ng}" gradientUnits="userSpaceOnUse" x1="{x0}" y1="0" x2="{n(x0 + name_w)}" y2="0" spreadMethod="reflect">'
        f'<stop stop-color="#F0F9FF"/><stop offset=".38" stop-color="{CYAN}"/><stop offset=".72" stop-color="{VIOLET}"/>'
        f'<stop offset="1" stop-color="{PINK}"/>'
        f'<animateTransform attributeName="gradientTransform" type="translate" values="0 0;{n(2 * name_w)} 0" dur="10s" repeatCount="indefinite"/>'
        f'</linearGradient><filter id="{glow}" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="16"/></filter>')
    s.add(s.text(x0, 168, C.NAME, "d", name_size, CYAN, opacity=.32, extra=f'filter="url(#{glow})"'),
          s.text(x0, 168, C.NAME, "d", name_size, f"url(#{ng})", ls=-1))
    s.add(s.text(x0, 213, C.ROLE, "s", 22, TEXT, opacity=.92))
    s.add(s.text(x0, 270, "❯", "mb", 19, PINK))
    typing_loop(s, x0 + 26, 270, C.HERO_PHRASES)
    cx = x0
    for chip in C.HERO_CHIPS:
        tw = FONTS["m"].width(chip, 11, 1.6)
        w = tw + 26
        s.add(f'<rect x="{n(cx)}" y="318" width="{n(w)}" height="26" rx="7" fill="#0E1628" stroke="{LINE}"/>',
              s.text(cx + 13, 335, chip, "m", 11, MUTED, ls=1.6))
        cx += w + 10
    s.add(s.text(x0, 384, "SCROLL FOR THE FULL BRIEFING  ↓", "m", 10.5, DIM, ls=2.2))
    R = 150
    rcx = max(812, x0 + FONTS["s"].width(C.ROLE, 22) + R + 34)
    radar(s, rcx, 206, R, C.RADAR_BLIPS)
    s.add(s.text(rcx, 392, "SHIPPED · ON RADAR", "mb", 10.5, MUTED, anchor="middle", ls=3))
    s.add("</g>", border)
    return s.save("hero.svg")


# --------------------------------------------------------------------------- buttons
SIMPLE_ICON_PATH = re.compile(r'<path d="([^"]+)"')


def brand_path(name: str) -> str:
    return SIMPLE_ICON_PATH.search((HERE / "icons" / f"brand-{name}.svg").read_text()).group(1)


def build_buttons() -> list[Path]:
    out = []
    buttons = [
        ("portfolio", "Portfolio", CYAN), ("linkedin", "LinkedIn", SKY), ("x", "X / Twitter", TEXT),
        ("leetcode", "LeetCode", AMBER), ("resume", "Resume", VIOLET),
    ]
    for i, (key, label, accent) in enumerate(buttons):
        H = 56
        tw = FONTS["d"].width(label, 17)
        W = 58 + tw + 46
        s = Svg(W, H, label, f"Open {label}")
        g = s.uid("bt")
        s.defs.append(
            f'<linearGradient id="{g}b" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{accent}" stop-opacity=".75"/>'
            f'<stop offset="1" stop-color="{VIOLET}" stop-opacity=".25"/></linearGradient>'
            f'<linearGradient id="{g}s" x1="0" x2="1"><stop stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="{g}c"><rect x="1" y="1" width="{n(W - 2)}" height="{H - 2}" rx="{(H - 2) / 2}"/></clipPath>')
        s.add(f'<rect x="1" y="1" width="{n(W - 2)}" height="{H - 2}" rx="{(H - 2) / 2}" fill="{PANEL}"/>')
        s.style("@keyframes shine{0%{transform:translateX(-110px) skewX(-20deg)}35%,100%{transform:translateX(" + n(W + 60) + "px) skewX(-20deg)}}")
        s.add(f'<g clip-path="url(#{g}c)"><rect width="70" height="{H}" fill="url(#{g}s)" '
              f'style="animation:shine 4.6s cubic-bezier(.5,0,.3,1) {i * .28:.2f}s infinite;transform-box:fill-box;transform-origin:center"/></g>')
        ix, iy = 22, H / 2
        if key == "portfolio":
            s.add(f'<g stroke="{accent}" stroke-width="1.8" stroke-linecap="round"><circle cx="{ix + 11}" cy="{iy}" r="10"/>'
                  f'<ellipse cx="{ix + 11}" cy="{iy}" rx="4.4" ry="10"/><path d="M{ix + 1.5} {iy}h19M{ix + 3} {iy - 5}h16M{ix + 3} {iy + 5}h16"/></g>')
        elif key == "linkedin":
            s.add(f'<rect x="{ix}" y="{iy - 11}" width="22" height="22" rx="5" fill="#0A66C2"/>',
                  s.text(ix + 11, iy + 5.5, "in", "d", 14, "#fff", anchor="middle"))
        elif key in ("x", "leetcode"):
            color = TEXT if key == "x" else "#FFA116"
            s.add(f'<g transform="translate({ix} {iy - 11}) scale({22 / 24:.4f})"><path d="{brand_path(key)}" fill="{color}"/></g>')
        elif key == "resume":
            s.add(f'<g stroke="{accent}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round">'
                  f'<path d="M{ix + 3} {iy - 11}h11l6 6v16a2 2 0 0 1-2 2H{ix + 3}a2 2 0 0 1-2-2V{iy - 9}a2 2 0 0 1 2-2z"/>'
                  f'<path d="M{ix + 14} {iy - 11}v6h6M{ix + 6} {iy}h9M{ix + 6} {iy + 5}h7"/></g>')
        s.add(s.text(58, H / 2 + 6, label, "d", 17, TEXT))
        s.add(s.text(W - 24, H / 2 + 6, "↗", "d", 16, accent, anchor="middle"))
        s.add(f'<rect x="1" y="1" width="{n(W - 2)}" height="{H - 2}" rx="{(H - 2) / 2}" stroke="url(#{g}b)" stroke-width="1.3"/>')
        out.append(s.save(f"btn-{key}.svg"))
    return out


# --------------------------------------------------------------------------- whoami terminal
def build_terminal() -> Path:
    W = 1000
    size, lh, x0 = 15.5, 31, 34
    cw = FONTS["m"].width("M", size)
    top = 48
    first = top + 42
    H = first + len(C.TERMINAL) * lh + 30
    s = Svg(W, H, "whoami", " ".join(
        (f"$ {t}" if kind == "cmd" else "".join(seg for seg, _ in t)) for kind, t in C.TERMINAL))
    clip, border = card(s, W, H, 20)
    s.add(f'<g clip-path="url(#{clip})">')
    dot_grid(s, 0, top, W, H - top, cx=.8, cy=.2)
    s.add(f'<rect width="{W}" height="{top}" fill="#0C1323"/><path d="M0 {top}H{W}" stroke="{LINE}"/>')
    for i, col in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        s.add(f'<circle cx="{28 + i * 20}" cy="{top / 2}" r="6" fill="{col}"/>')
    s.add(s.text(W / 2, top / 2 + 4.5, C.TERMINAL_TITLE, "m", 12.5, DIM, anchor="middle"))
    s.add(s.text(W - 28, top / 2 + 4.5, "01 / WHOAMI", "mb", 11.5, CYAN, anchor="end", ls=2.4))

    # timeline: prompts appear, commands type out, outputs print
    t = .6
    events = []  # (kind, line_index, start, end)
    cursor_steps: list[tuple[float, float, float]] = []  # (time, x, y)
    for i, (kind, val) in enumerate(C.TERMINAL):
        y = first + i * lh
        if kind == "cmd":
            px = x0 + 2 * cw
            cursor_steps.append((t, px, y))
            ts = t + .3
            for k in range(1, len(val) + 1):
                cursor_steps.append((ts + k * .062, px + k * cw, y))
            te = ts + len(val) * .062
            events.append(("cmd", i, t, ts, te))
            t = te + .38
        else:
            events.append(("out", i, t, t, t))
            t += .14
            nxt = C.TERMINAL[i + 1][0] if i + 1 < len(C.TERMINAL) else None
            if nxt == "cmd":
                t += .32
    final_y = first + len(C.TERMINAL) * lh
    events.append(("final", len(C.TERMINAL), t, t, t))
    cursor_steps.append((t, x0 + 2 * cw, final_y))
    D = t + .01

    def appear(start: float) -> str:
        a = max(start / (start + .22), 1e-4)
        return (f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{a:.5f};1" dur="{start + .22:.3f}s" '
                f'fill="freeze"/>')

    for ev in events:
        kind, i, start = ev[0], ev[1], ev[2]
        y = first + i * lh
        if kind in ("cmd", "final"):
            s.add(s.text(x0, y, "❯", "mb", size, PINK).replace("</text>", appear(start) + "</text>"))
        if kind == "cmd":
            _, _, _, ts, te = ev
            val = C.TERMINAL[i][1]
            px = x0 + 2 * cw
            full = len(val) * cw
            cid = s.uid("tc")
            values = ["0"] + [n(k * cw) for k in range(1, len(val) + 1)]
            times = [0.0] + [(ts + k * .062) / te for k in range(1, len(val) + 1)]
            s.defs.append(
                f'<clipPath id="{cid}"><rect x="{n(px)}" y="{n(y - size)}" width="{n(full + 2)}" height="{n(size * 1.5)}">'
                f'<animate attributeName="width" values="{";".join(values)}" keyTimes="{";".join(f"{v:.5f}" for v in times)}" '
                f'dur="{te:.3f}s" calcMode="discrete" fill="freeze"/></rect></clipPath>')
            s.add(f'<g clip-path="url(#{cid})">' + s.text(px, y, val, "m", size, TEXT, fit=True) + "</g>")
        elif kind == "out":
            segs = C.TERMINAL[i][1]
            spans = "".join(f'<tspan fill="{NAMED[c]}">{esc(seg)}</tspan>' for seg, c in segs)
            whole = "".join(seg for seg, _ in segs)
            s.use_chars("m", whole)
            width = FONTS["m"].width(whole, size)
            s.add(f'<text x="{x0}" y="{n(y)}" class="fm" font-size="{size}" textLength="{n(width)}" '
                  f'lengthAdjust="spacingAndGlyphs" xml:space="preserve" style="white-space:pre">{spans}{appear(start)}</text>')
    # one block cursor that follows the typing, then blinks on the last prompt
    xs = ";".join(n(cx + 1) for _, cx, _ in cursor_steps)
    ys = ";".join(n(cy - size * .8) for _, _, cy in cursor_steps)
    kts = ";".join(f"{min(tt / D, 1):.5f}" for tt, _, _ in cursor_steps)
    kts = "0" + kts[kts.index(";"):] if ";" in kts else "0"
    s.style("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}")
    s.style(".blink{animation:blink 1.05s steps(1,end) infinite}")
    fx, fy = cursor_steps[-1][1], cursor_steps[-1][2]
    s.add(f'<rect class="blink" x="{n(fx + 1)}" y="{n(fy - size * .8)}" width="{n(cw * .92)}" height="{n(size * 1.05)}" fill="{CYAN}" rx="1">'
          f'<animate attributeName="x" values="{xs}" keyTimes="{kts}" dur="{D:.3f}s" calcMode="discrete" fill="freeze"/>'
          f'<animate attributeName="y" values="{ys}" keyTimes="{kts}" dur="{D:.3f}s" calcMode="discrete" fill="freeze"/></rect>')
    s.add("</g>", border)
    return s.save("whoami.svg")


# --------------------------------------------------------------------------- operating loop
def stage_icon(kind: str, cx: float, cy: float) -> str:
    st = f'stroke="{CYAN}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "search":
        return f'<g {st}><circle cx="{cx - 3}" cy="{cy - 3}" r="8"/><path d="M{cx + 3} {cy + 3}l7 7"/></g>'
    if kind == "doc":
        return (f'<g {st}><rect x="{cx - 9}" y="{cy - 11}" width="18" height="22" rx="3"/>'
                f'<path d="M{cx - 4.5} {cy - 4}h9M{cx - 4.5} {cy + 1}h9M{cx - 4.5} {cy + 6}h5"/></g>')
    if kind == "pen":
        return (f'<g {st}><path d="M{cx} {cy - 12}l8 13-8 11-8-11z"/><circle cx="{cx}" cy="{cy + 1}" r="2"/>'
                f'<path d="M{cx} {cy - 12}v11"/></g>')
    if kind == "code":
        return f'<g {st}><path d="M{cx - 5} {cy - 8}l-7 8 7 8M{cx + 5} {cy - 8}l7 8-7 8M{cx + 2.5} {cy - 11}l-5 22"/></g>'
    return (f'<g {st}><path d="M{cx - 12} {cy - 1}L{cx + 12} {cy - 10}L{cx + 4} {cy + 11}L{cx - 1} {cy + 3}z"/>'
            f'<path d="M{cx - 1} {cy + 3}L{cx + 12} {cy - 10}"/></g>')


def build_pipeline() -> Path:
    W, H = 1000, 372
    kicker, title = C.PIPELINE_TITLE
    s = Svg(W, H, title, "Discover, define, design, build, ship, then measure and iterate: "
            + "; ".join(f"{a.title()}: {b[0]}, {b[1]}" for a, b, _ in C.PIPELINE))
    clip, border = card(s, W, H, 22)
    s.add(f'<g clip-path="url(#{clip})">')
    dot_grid(s, 0, 0, W, H, cx=.5, cy=.65)
    header(s, 44, 54, kicker, title, W - 44)
    cy = 224
    xs = [116 + i * (884 - 116) / (len(C.PIPELINE) - 1) for i in range(len(C.PIPELINE))]
    fwd, back = 4.2, 1.8
    T = fwd + back
    arc = f"M{n(xs[-1])} {cy - 36}Q500 98 {n(xs[0])} {cy - 36}"
    s.add(f'<path d="M{n(xs[0])} {cy}H{n(xs[-1])}" stroke="{LINE}" stroke-width="2"/>',
          f'<path d="M{n(xs[0])} {cy}H{n(xs[-1])}" stroke="{CYAN}" stroke-opacity=".35" stroke-width="2" stroke-dasharray="2 8"/>',
          f'<path d="{arc}" stroke="{VIOLET}" stroke-opacity=".45" stroke-width="1.5" stroke-dasharray="5 7"/>')
    s.add(s.text(500, 132, C.PIPELINE_LOOP_LABEL, "mb", 11, VIOLET, anchor="middle", ls=2.4))
    # the comet runs left to right along the line, then back over the arc
    tail = s.uid("tl")
    s.defs.append(f'<linearGradient id="{tail}" x1="0" x2="1"><stop stop-color="{CYAN}" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="{CYAN}"/></linearGradient>')
    run = xs[-1] - xs[0]
    s.style(f"@keyframes comet{{0%{{transform:translateX(0);opacity:1}}{pct(fwd / T)}{{transform:translateX({n(run)}px);opacity:1}}"
            f"{pct((fwd + .01) / T)},100%{{transform:translateX({n(run)}px);opacity:0}}}}")
    s.style(f"@keyframes backdot{{0%,{pct(fwd / T)}{{opacity:0}}{pct((fwd + .05) / T)},{pct(.985)}{{opacity:1}}100%{{opacity:0}}}}")
    s.add(f'<g style="animation:comet {T}s linear infinite"><rect x="{n(xs[0] - 90)}" y="{cy - 1.5}" width="90" height="3" rx="1.5" fill="url(#{tail})"/>'
          f'<circle cx="{n(xs[0])}" cy="{cy}" r="10" fill="{CYAN}" fill-opacity=".22"/><circle cx="{n(xs[0])}" cy="{cy}" r="4.5" fill="#fff"/></g>')
    s.add(f'<g style="animation:backdot {T}s linear infinite"><circle r="4" fill="{VIOLET}"/><circle r="9" fill="{VIOLET}" fill-opacity=".25"/>'
          f'<animateMotion dur="{T}s" repeatCount="indefinite" path="{arc}" keyPoints="0;0;1;1" keyTimes="0;{fwd / T:.4f};.985;1" calcMode="linear"/></g>')
    s.style(f"@keyframes nodeflash{{0%{{opacity:1;transform:scale(1.12)}}22%,100%{{opacity:0;transform:scale(1)}}}}")
    s.style(".nflash{transform-box:fill-box;transform-origin:center;opacity:0}")
    for (name, caption, icon), x in zip(C.PIPELINE, xs):
        t_hit = (x - xs[0]) / run * fwd
        s.add(f'<circle cx="{n(x)}" cy="{cy}" r="36" fill="#0C1424" stroke="{LINE}" stroke-width="1.5"/>',
              f'<circle class="nflash" style="animation:nodeflash {T}s ease-out {t_hit - T:.3f}s infinite" cx="{n(x)}" cy="{cy}" r="36" '
              f'fill="{CYAN}" fill-opacity=".10" stroke="{CYAN}" stroke-width="2"/>',
              stage_icon(icon, x, cy),
              s.text(x, cy + 66, name, "mb", 13, TEXT, anchor="middle", ls=2.4),
              s.text(x, cy + 90, caption[0], "s", 13.5, MUTED, anchor="middle"),
              s.text(x, cy + 109, caption[1], "s", 13.5, MUTED, anchor="middle"))
    s.add("</g>", border)
    return s.save("operating-loop.svg")


# --------------------------------------------------------------------------- figures
def build_figures() -> Path:
    kicker, title = C.FIGURES_TITLE
    cols, tw, th, gap = 4, 218, 156, 16
    W = 1000
    mx = (W - cols * tw - (cols - 1) * gap) / 2
    y0 = 120
    rows = math.ceil(len(C.FIGURES) / cols)
    H = y0 + rows * th + (rows - 1) * gap + 36
    s = Svg(W, H, title, "; ".join(f"{v} {c}" for _, v, c in C.FIGURES))
    clip, border = card(s, W, H, 22, tint=VIOLET)
    s.add(f'<g clip-path="url(#{clip})">')
    dot_grid(s, 0, 0, W, H, cx=.5, cy=.2)
    header(s, 44, 54, kicker, title, W - 44)
    accents = [(CYAN, SKY), (SKY, VIOLET), (VIOLET, PINK), (PINK, AMBER)]
    size = 40
    cw = FONTS["mb"].width("0", size)
    L = size * 1.5  # gap between stacked digits, wider than the window so a roll shows clean slices
    s.style("@keyframes tshine{0%{transform:translateX(-140px) skewX(-18deg)}28%,100%{transform:translateX(380px) skewX(-18deg)}}")
    shine = s.uid("sh")
    s.defs.append(f'<linearGradient id="{shine}" x1="0" x2="1"><stop stop-color="#fff" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    for idx, (kick, value, caption) in enumerate(C.FIGURES):
        r, c = divmod(idx, cols)
        x, y = mx + c * (tw + gap), y0 + r * (th + gap)
        a1, a2 = accents[(idx + r) % len(accents)]
        tc, gg, ng = s.uid("tc"), s.uid("tg"), s.uid("ng")
        s.defs.append(
            f'<clipPath id="{tc}"><rect x="{n(x)}" y="{n(y)}" width="{tw}" height="{th}" rx="16"/></clipPath>'
            f'<linearGradient id="{gg}" x1="{n(x)}" x2="{n(x + tw)}" gradientUnits="userSpaceOnUse">'
            f'<stop stop-color="{a1}"/><stop offset="1" stop-color="{a2}"/></linearGradient>'
            f'<linearGradient id="{ng}" x1="{n(x + 18)}" x2="{n(x + 18 + cw * len(value))}" gradientUnits="userSpaceOnUse">'
            f'<stop stop-color="#F8FAFC"/><stop offset=".55" stop-color="{a1}"/><stop offset="1" stop-color="{a2}"/></linearGradient>')
        s.add(f'<rect x="{n(x)}" y="{n(y)}" width="{tw}" height="{th}" rx="16" fill="{PANEL}" fill-opacity=".92" stroke="{LINE}"/>',
              f'<g clip-path="url(#{tc})"><rect x="{n(x)}" y="{n(y)}" width="{tw}" height="2.5" fill="url(#{gg})"/>'
              f'<rect x="{n(x)}" y="{n(y - 20)}" width="70" height="{th + 40}" fill="url(#{shine})" '
              f'style="animation:tshine 7s ease-in-out {1.6 + idx * .35:.2f}s infinite;transform-box:fill-box;transform-origin:center"/></g>')
        s.add(s.text(x + 18, y + 30, kick, "mb", 10.5, DIM, ls=1.8))
        s.add(f'<circle cx="{n(x + tw - 20)}" cy="{n(y + 26)}" r="3" fill="{a1}"/>')
        # odometer: every digit column rolls up to its final digit, staggered left to right
        base = y + 84
        oc = s.uid("oc")
        s.defs.append(f'<clipPath id="{oc}"><rect x="{n(x + 10)}" y="{n(base - size * .8)}" width="{tw - 20}" height="{n(size * .9)}"/></clipPath>')
        cols_svg, static = [], []
        xi = x + 18
        digit_i = 0
        for ch in value:
            if ch.isdigit():
                d = int(ch)
                shift = (10 + d) * L
                delay = .35 + idx * .11 + digit_i * .08
                dur = delay + 1.9
                tsp = "".join(f'<tspan x="{n(xi)}" y="{n(base + k * L)}">{k % 10}</tspan>' for k in range(20))
                s.use_chars("mb", "0123456789")
                cols_svg.append(
                    f'<g transform="translate(0 {n(-shift)})"><animateTransform attributeName="transform" type="translate" '
                    f'values="0 0;0 0;0 {n(-shift)}" keyTimes="0;{delay / dur:.4f};1" calcMode="spline" '
                    f'keySplines="0 0 1 1;.12 .8 .22 1" dur="{dur:.2f}s" fill="freeze"/>'
                    f'<text class="fmb" font-size="{size}" fill="url(#{ng})">{tsp}</text></g>')
                digit_i += 1
            else:  # separators and symbols stay put, outside the clip so commas keep their tails
                static.append(s.text(xi, base, ch, "mb", size, f"url(#{ng})"))
            xi += cw
        s.add(f'<g clip-path="url(#{oc})">{"".join(cols_svg)}</g>', *static)
        lines = wrap(caption, "s", 13.5, tw - 36)
        if len(lines) > 2:
            raise ValueError(f"figure caption {caption!r} needs {len(lines)} lines, the tile has room for 2")
        for li, line in enumerate(lines):
            s.add(s.text(x + 18, y + 114 + li * 19, line, "s", 13.5, MUTED))
    s.add("</g>", border)
    return s.save("figures.svg")


# --------------------------------------------------------------------------- project cards
def jpeg_data_uri(name: str) -> str:
    path = HERE / "frames" / f"{name}.jpg"
    with Image.open(path) as im:
        assert im.size == (720, 405), f"{path.name} is {im.size}, expected 720x405 - rerun capture_frames.py"
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def build_card(p: dict, index: int, accent: str) -> Path:
    W, H = 500, 456
    s = Svg(W, H, f"{p['title']} — live at {p['url'].replace('https://', '')}", p["desc"])
    clip, border = card(s, W, H, 20, tint=accent, accent2=VIOLET)
    s.add(f'<g clip-path="url(#{clip})">')
    fx, fy, fw = 14, 14, 472
    bar = 30
    vh = fw * 405 / 720
    vy = fy + bar
    frame_clip = s.uid("fc")
    s.defs.append(f'<clipPath id="{frame_clip}"><rect x="{fx}" y="{fy}" width="{fw}" height="{n(bar + vh)}" rx="12"/></clipPath>')
    view_clip = s.uid("vc")
    s.defs.append(f'<clipPath id="{view_clip}"><rect x="{fx}" y="{n(vy)}" width="{fw}" height="{n(vh)}"/></clipPath>')
    s.add(f'<g clip-path="url(#{frame_clip})">')
    s.add(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{bar}" fill="#0F172A"/>')
    for i, col in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        s.add(f'<circle cx="{fx + 16 + i * 14}" cy="{fy + bar / 2}" r="4.2" fill="{col}"/>')
    ux, uw = fx + 66, fw - 66 - 12
    s.add(f'<rect x="{ux}" y="{fy + 6}" width="{uw}" height="18" rx="9" fill="#060A14" stroke="{LINE}"/>',
          f'<path d="M{ux + 12} {fy + 14.5}v-2.2a2.8 2.8 0 0 1 5.6 0v2.2M{ux + 10.6} {fy + 14.5}h8.4v5.6h-8.4z" '
          f'stroke="{GREEN}" stroke-width="1.2" stroke-linejoin="round"/>')
    frames = p["frames"]
    nf = len(frames)
    hold, slide = 2.7, .85
    P = hold + slide
    T = nf * P
    delay = -(index * 1.35)
    # images: defined once, the first frame is re-used after the last for a seamless loop
    imgs = []
    for k, fr in enumerate(frames):
        iid = s.uid("im")
        s.defs.append(f'<image id="{iid}" width="{fw}" height="{n(vh)}" preserveAspectRatio="xMidYMid slice" '
                      f'xlink:href="{jpeg_data_uri(fr["shot"])}"/>')
        imgs.append(iid)
    kf = []
    for k in range(nf):
        t0, t1 = k * P, k * P + hold
        kf.append(f"{pct(t0 / T)}{{transform:translateY({n(-k * vh)}px)}}")
        kf.append(f"{pct(t1 / T)}{{transform:translateY({n(-k * vh)}px);animation-timing-function:cubic-bezier(.65,0,.35,1)}}")
    kf.append(f"100%{{transform:translateY({n(-nf * vh)}px)}}")
    s.style(f"@keyframes scroll{index}{{{''.join(kf)}}}")
    uses = "".join(f'<use xlink:href="#{imgs[k % nf]}" x="{fx}" y="{n(vy + k * vh)}"/>' for k in range(nf + 1))
    s.add(f'<g clip-path="url(#{view_clip})"><g style="animation:scroll{index} {T:.2f}s {delay:.2f}s infinite">{uses}</g></g>')
    # page-load bar that runs during each scroll
    lk = [f"0%{{transform:scaleX(0);opacity:0}}"]
    for k in range(nf):
        a, b = k * P + hold, (k + 1) * P
        lk.append(f"{pct((a - .01) / T)}{{transform:scaleX(0);opacity:0}}{pct(a / T)}{{transform:scaleX(0);opacity:1}}"
                  f"{pct((b - .06) / T)}{{transform:scaleX(1);opacity:1}}{pct(min(b + .3, T) / T)}{{transform:scaleX(1);opacity:0}}")
    s.style(f"@keyframes load{index}{{{''.join(lk)}}}")
    lg = s.uid("lg")
    s.defs.append(f'<linearGradient id="{lg}" x1="0" x2="1"><stop stop-color="{accent}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>')
    s.add(f'<rect x="{fx}" y="{n(vy)}" width="{fw}" height="2.5" fill="url(#{lg})" opacity="0" '
          f'style="animation:load{index} {T:.2f}s {delay:.2f}s infinite;transform-box:fill-box;transform-origin:left center"/>')
    # scrollbar thumb
    track_h = vh - 12
    thumb_h = max(26, track_h / nf)
    span = track_h - thumb_h
    tk = []
    for k in range(nf):
        pos = span * k / max(1, nf - 1)
        tk.append(f"{pct(k * P / T)}{{transform:translateY({n(pos)}px)}}"
                  f"{pct((k * P + hold) / T)}{{transform:translateY({n(pos)}px);animation-timing-function:cubic-bezier(.65,0,.35,1)}}")
    tk.append("100%{transform:translateY(0)}")
    s.style(f"@keyframes thumb{index}{{{''.join(tk)}}}")
    s.add(f'<rect x="{fx + fw - 7}" y="{n(vy + 6)}" width="3.5" height="{n(thumb_h)}" rx="1.75" fill="#fff" fill-opacity=".55" '
          f'style="animation:thumb{index} {T:.2f}s {delay:.2f}s infinite"/>')
    # the headline stat floats over the screenshot, bottom left
    stat_w = FONTS["mb"].width(p["badge"], 11, 1.3) + 26
    sx, sy = fx + 12, vy + vh - 12 - 26
    s.add(f'<rect x="{n(sx)}" y="{n(sy)}" width="{n(stat_w)}" height="26" rx="8" fill="#070A13" fill-opacity=".86" '
          f'stroke="{accent}" stroke-opacity=".6"/>',
          s.text(sx + 13, sy + 17.2, p["badge"], "mb", 11, accent, ls=1.3))
    s.add("</g>")
    s.add(f'<rect x="{fx + .5}" y="{fy + .5}" width="{fw - 1}" height="{n(bar + vh - 1)}" rx="11.5" stroke="#26324A"/>')
    # URL text cross-fades with the frames
    dt = .18
    for k, fr in enumerate(frames):
        label = fr["domain"]
        max_w = uw - 34
        while FONTS["m"].width(label, 10.5) > max_w:
            label = label[:-2] + "…"
        if nf == 1:
            s.add(s.text(ux + 26, fy + 18.6, label, "m", 10.5, MUTED))
            continue
        sw = [(j * P + hold + slide / 2) for j in range(nf)]  # moment frame j hands over to j+1
        if k == 0:
            rule = (f"0%{{opacity:1}}{pct((sw[0] - dt) / T)}{{opacity:1}}{pct((sw[0] + dt) / T)}{{opacity:0}}"
                    f"{pct((sw[-1] - dt) / T)}{{opacity:0}}{pct((sw[-1] + dt) / T)}{{opacity:1}}100%{{opacity:1}}")
        else:
            rule = (f"0%{{opacity:0}}{pct((sw[k - 1] - dt) / T)}{{opacity:0}}{pct((sw[k - 1] + dt) / T)}{{opacity:1}}"
                    f"{pct((sw[k] - dt) / T)}{{opacity:1}}{pct((sw[k] + dt) / T)}{{opacity:0}}100%{{opacity:0}}")
        s.style(f"@keyframes url{index}_{k}{{{rule}}}")
        s.add(s.text(ux + 26, fy + 18.6, label, "m", 10.5, MUTED, opacity=1 if k == 0 else 0,
                     extra=f'style="animation:url{index}_{k} {T:.2f}s {delay:.2f}s infinite"'))
    # text block
    ty = fy + bar + vh + 40
    s.add(s.text(26, ty, p["title"], "d", 23, TEXT))
    pill(s, W - 24, ty - 17, "LIVE", GREEN, size=10.5, h=22, pad=10, dot=True, anchor_right=True)
    lines = wrap(p["desc"], "s", 14, W - 52)
    if len(lines) > 2:
        raise ValueError(f"{p['key']}: description needs {len(lines)} lines, the card has room for 2. Shorten it.")
    for li, line in enumerate(lines):
        s.add(s.text(26, ty + 26 + li * 20, line, "s", 14, MUTED))
    cx = 26
    cy = ty + 66
    for chip in p["chips"]:
        w = FONTS["m"].width(chip, 11) + 20
        s.add(f'<rect x="{n(cx)}" y="{n(cy)}" width="{n(w)}" height="22" rx="11" fill="#0F172A" stroke="{LINE}"/>',
              s.text(cx + 10, cy + 15, chip, "m", 11, MUTED))
        cx += w + 7
    if cx - 7 > W - 50:  # leave room for the arrow on the right
        raise ValueError(f"{p['key']}: tech chips are {cx - 7 - 26:.0f}px wide, the card has {W - 76}px")
    s.add(s.text(W - 26, cy + 15.5, "↗", "d", 16, accent, anchor="end"))
    s.add("</g>", border)
    return s.save(f"card-{p['key']}.svg")


def build_section_bar(name: str, kicker: str, title: str, sub: str) -> Path:
    W, H = 1000, 118
    s = Svg(W, H, title, sub)
    clip, border = card(s, W, H, 22)
    s.add(f'<g clip-path="url(#{clip})">')
    dot_grid(s, 0, 0, W, H, cx=.85, cy=.3)
    header(s, 44, 50, kicker, title, W - 44)
    s.add("</g>", border)
    return s.save(name)


# --------------------------------------------------------------------------- stack
ID_RE = re.compile(r'id="([^"]+)"')


def icon_markup(name: str, prefix: str) -> str:
    raw = (HERE / "icons" / f"{name}.svg").read_text()
    inner = re.sub(r"^.*?<svg[^>]*>", "", raw, count=1, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, flags=re.S)
    for old in set(ID_RE.findall(inner)):
        inner = inner.replace(f'id="{old}"', f'id="{prefix}{old}"').replace(f"url(#{old})", f"url(#{prefix}{old})")
        inner = inner.replace(f'href="#{old}"', f'href="#{prefix}{old}"')
    return inner


def build_stack() -> Path:
    kicker, title = C.STACK_TITLE
    W = 1000
    pw, ph, gap = 452, 150, 24
    mx = (W - 2 * pw - gap) / 2
    y0 = 120
    H = y0 + 2 * ph + gap + 36
    names = {"CPP": "C++", "NextJS-Dark": "Next.js", "TailwindCSS-Dark": "Tailwind CSS", "ThreeJS-Dark": "Three.js",
             "NodeJS-Dark": "Node.js", "ExpressJS-Dark": "Express", "PostgreSQL-Dark": "PostgreSQL", "Github-Dark": "GitHub",
             "GithubActions-Dark": "GitHub Actions", "VSCode-Dark": "VS Code"}
    desc = "; ".join(f"{cat.title()}: " + ", ".join(names.get(i, i.replace("-Dark", "")) for i in icons) for cat, icons in C.STACK)
    s = Svg(W, H, title, desc)
    clip, border = card(s, W, H, 22, tint=SKY)
    s.add(f'<g clip-path="url(#{clip})">')
    dot_grid(s, 0, 0, W, H, cx=.5, cy=.5)
    header(s, 44, 54, kicker, title, W - 44)
    s.style("@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}")
    s.style("@keyframes beam{0%{transform:translateX(-160px)}45%,100%{transform:translateX(620px)}}")
    beam = s.uid("bm")
    s.defs.append(f'<linearGradient id="{beam}" x1="0" x2="1"><stop stop-color="{CYAN}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{CYAN}" stop-opacity=".09"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>')
    titles_col = [CYAN, VIOLET, PINK, AMBER]
    icon_no = 0
    for pi, (cat, icons) in enumerate(C.STACK):
        r, c = divmod(pi, 2)
        px, py = mx + c * (pw + gap), y0 + r * (ph + gap)
        pc = s.uid("pc")
        s.defs.append(f'<clipPath id="{pc}"><rect x="{n(px)}" y="{n(py)}" width="{pw}" height="{ph}" rx="16"/></clipPath>')
        s.add(f'<rect x="{n(px)}" y="{n(py)}" width="{pw}" height="{ph}" rx="16" fill="{PANEL}" fill-opacity=".92" stroke="{LINE}"/>',
              f'<g clip-path="url(#{pc})"><rect x="{n(px)}" y="{n(py)}" width="140" height="{ph}" fill="url(#{beam})" '
              f'style="animation:beam 6.5s ease-in-out {pi * 1.1:.1f}s infinite"/></g>',
              s.text(px + 22, py + 32, cat, "mb", 11.5, titles_col[pi], ls=2.4),
              s.text(px + pw - 22, py + 32, f"{len(icons):02d}", "m", 11, DIM, anchor="end"))
        size = 50
        step = (pw - 44 - size) / (len(icons) - 1)
        for k, name in enumerate(icons):
            ix, iy = px + 22 + k * step, py + 60
            icon_no += 1
            s.add(f'<g style="animation:float 3.8s ease-in-out {-((k + pi * 2) * .42):.2f}s infinite">'
                  f'<svg x="{n(ix)}" y="{n(iy)}" width="{size}" height="{size}" viewBox="0 0 256 256" fill="none">'
                  f'{icon_markup(name, f"k{icon_no}_")}</svg></g>')
    s.add("</g>", border)
    s.add("<!-- Icons: skill-icons by tandpfun, MIT licence (https://github.com/tandpfun/skill-icons) -->")
    return s.save("stack.svg")


# --------------------------------------------------------------------------- journey
def build_journey() -> Path:
    kicker, title = C.JOURNEY_TITLE
    W, H = 1000, 488
    s = Svg(W, H, title, "; ".join(f"{d}: {t} ({x})" for d, t, x in C.JOURNEY))
    clip, border = card(s, W, H, 22, tint=CYAN, accent2=AMBER)
    s.add(f'<g clip-path="url(#{clip})">')
    dot_grid(s, 0, 0, W, H, cx=.5, cy=.6)
    header(s, 44, 54, kicker, title, W - 44)
    ly = 304
    x0, x1 = 66, W - 66
    nodes = len(C.JOURNEY)
    xs = [x0 + i * (x1 - x0) / (nodes - 1) for i in range(nodes)]
    draw = 3.4
    lgid = s.uid("jl")
    s.defs.append(f'<linearGradient id="{lgid}" x1="{x0}" x2="{x1}" gradientUnits="userSpaceOnUse"><stop stop-color="{CYAN}"/>'
                  f'<stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>')
    s.style("@keyframes draw{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}")
    s.style("@keyframes pop{from{transform:scale(0);opacity:0}to{transform:scale(1);opacity:1}}")
    s.style("@keyframes rise{from{transform:translateY(8px);opacity:0}to{transform:translateY(0);opacity:1}}")
    s.style("@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}")
    s.style("@keyframes run{0%{stroke-dashoffset:60}60%,100%{stroke-dashoffset:-1000}}")
    s.add(f'<path d="M{x0} {ly}H{x1}" stroke="{LINE}" stroke-width="3" stroke-linecap="round"/>',
          f'<path d="M{x0} {ly}H{x1}" pathLength="1000" stroke="url(#{lgid})" stroke-width="3" stroke-linecap="round" '
          f'stroke-dasharray="1000" style="animation:draw {draw}s cubic-bezier(.3,.1,.3,1) .2s both"/>',
          f'<path d="M{x0} {ly}H{x1}" pathLength="1000" stroke="#fff" stroke-opacity=".8" stroke-width="3" stroke-linecap="round" '
          f'stroke-dasharray="60 1100" style="animation:run 6s ease-in-out {draw + .4:.1f}s infinite;stroke-dashoffset:60"/>')
    tiers = {  # (date_y, title_y, detail_y, connector y1, y2)
        "far_up": (150, 172, 191, 199, ly - 12), "near_up": (220, 242, 261, 269, ly - 12),
        "near_dn": (350, 372, 391, ly + 12, 334), "far_dn": (414, 436, 455, ly + 12, 398),
    }
    order = ["far_up", "far_dn", "near_up", "near_dn"]
    for i, ((date, ttl, detail), x) in enumerate(zip(C.JOURNEY, xs)):
        tier = tiers[order[i % 4]]
        t_hit = .2 + draw * (x - x0) / (x1 - x0) * .92
        last = i == nodes - 1
        color = [CYAN, SKY, VIOLET, PINK, AMBER][i % 5] if not last else GREEN
        anchor, tx = "middle", x
        if i == 0:
            anchor, tx = "start", x - 14
        elif last:
            anchor, tx = "end", x + 14
        cy1, cy2 = tier[3], tier[4]
        # connectors grow out of the timeline, so pin the end that touches it
        origin = f"transform-origin:{n(x)}px {n(cy2 if cy1 < ly else cy1)}px"
        s.add(f'<path d="M{n(x)} {cy1}V{cy2}" stroke="{color}" stroke-opacity=".45" stroke-dasharray="3 4" '
              f'style="animation:grow .5s ease-out {t_hit + .05:.2f}s both;{origin}"/>')
        s.add(f'<g style="animation:pop .45s cubic-bezier(.3,1.6,.5,1) {t_hit:.2f}s both;transform-box:fill-box;transform-origin:center">'
              f'<circle cx="{n(x)}" cy="{ly}" r="{9 if last else 7.5}" fill="{BG}" stroke="{color}" stroke-width="2.5"/>'
              f'<circle cx="{n(x)}" cy="{ly}" r="3" fill="{color}"/></g>')
        if last:
            s.style("@keyframes nowping{0%{transform:scale(.6);opacity:.8}80%,100%{transform:scale(3.2);opacity:0}}")
            for j in range(2):
                s.add(f'<circle cx="{n(x)}" cy="{ly}" r="8" stroke="{GREEN}" stroke-width="2" opacity="0" '
                      f'style="animation:nowping 2.4s ease-out {t_hit + .5 + j * 1.2:.2f}s infinite;transform-box:fill-box;transform-origin:center"/>')
        group = (s.text(tx, tier[0], date, "mb", 11, color, anchor=anchor, ls=1.6)
                 + s.text(tx, tier[1], ttl, "d", 16, TEXT, anchor=anchor)
                 + s.text(tx, tier[2], detail, "s", 12.5, MUTED, anchor=anchor))
        s.add(f'<g style="animation:rise .55s ease-out {t_hit + .12:.2f}s both">{group}</g>')
    s.add("</g>", border)
    return s.save("journey.svg")


# --------------------------------------------------------------------------- footer
def build_footer() -> Path:
    W, H = 1000, 230
    s = Svg(W, H, C.FOOTER_LINE, C.FOOTER_SUB)
    clip, border = card(s, W, H, 26, tint=VIOLET)
    s.add(f'<g clip-path="url(#{clip})">')
    dot_grid(s, 0, 0, W, H, cx=.5, cy=.5)
    cx, cy = W / 2, 104
    s.style("@keyframes ripple{0%{transform:scale(.4);opacity:.7}100%{transform:scale(5.2);opacity:0}}")
    for j in range(4):
        s.add(f'<circle cx="{cx}" cy="{cy}" r="44" stroke="{CYAN if j % 2 == 0 else VIOLET}" stroke-width="1.4" opacity="0" '
              f'style="animation:ripple 6.4s cubic-bezier(.2,.6,.35,1) {j * 1.6:.1f}s infinite;transform-origin:{cx}px {cy}px"/>')
    # waves along the bottom
    s.style("@keyframes wave{to{transform:translateX(-500px)}}")
    for k, (col, op, amp, dur, yb) in enumerate([(CYAN, .09, 9, 9, 204), (VIOLET, .1, 12, 13, 211), (PINK, .07, 7, 17, 218)]):
        pts = []
        for xx in range(0, 2001, 25):
            pts.append(f"{xx} {n(yb + amp * math.sin(xx / 500 * 2 * math.pi + k))}")
        d = "M" + "L".join(pts) + f"V{H}H0Z"
        s.add(f'<path d="{d}" fill="{col}" fill-opacity="{op}" style="animation:wave {dur}s linear infinite"/>')
    fg = s.uid("fg")
    line_w = FONTS["d"].width(C.FOOTER_LINE, 34)
    s.defs.append(f'<linearGradient id="{fg}" gradientUnits="userSpaceOnUse" x1="{n(cx - line_w / 2)}" x2="{n(cx + line_w / 2)}" spreadMethod="reflect">'
                  f'<stop stop-color="#F0F9FF"/><stop offset=".45" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/>'
                  f'<animateTransform attributeName="gradientTransform" type="translate" values="0 0;{n(2 * line_w)} 0" dur="9s" repeatCount="indefinite"/></linearGradient>')
    s.add(s.text(cx, cy + 12, C.FOOTER_LINE, "d", 34, f"url(#{fg})", anchor="middle"))
    s.add(s.text(cx, cy + 46, C.FOOTER_SUB.upper(), "m", 11, MUTED, anchor="middle", ls=2.4))
    corner_brackets(s, W, H)
    s.add("</g>", border)
    return s.save("footer.svg")


# --------------------------------------------------------------------------- main
CARD_ACCENTS = {"sort-and-visualize": "#FF4D8D", "frankcalculator": "#2DD4BF", "aevoura": "#FB3B5C",
                "socio-top-paper": "#F43F5E", "kodex": "#FF7A30", "warlife": "#A3E635"}


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    written = [build_hero(), *build_buttons(), build_terminal(), build_pipeline(), build_figures(),
               build_section_bar("shipped.svg", *C.SHIPPED_TITLE, "Live websites, each card links to the running site"),
               *(build_card(p, i, CARD_ACCENTS.get(p["key"], CYAN)) for i, p in enumerate(C.PROJECTS)),
               build_stack(), build_journey(),
               build_section_bar("live-signal.svg", *C.LIVE_TITLE, "3D contribution calendar, streak and snake, rebuilt daily"),
               build_footer()]
    for path in written:
        print(f"{path.stat().st_size / 1024:7.1f} KB  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
