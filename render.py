#!/usr/bin/env python3
"""Saturday 21 November 2026 — the day's world news on one deterministic page.

This file is built in PARTS. Phase 1 (this file) implements the layout ENGINE
and the TOP of the page: masthead, stat band, region pills and three lead cards.
Later phases append further sections to build() before the single final render.

Nothing here is random or networked: the same code always produces the same
bytes. Every string is measured with the very font that draws it, every line
box is reserved, and any two text boxes that are not explicitly allowed to
touch raise an AssertionError.
"""
import os
import html
import math
from functools import lru_cache
from io import BytesIO

import cairosvg
from PIL import Image, ImageFont

# --------------------------------------------------------------------------
# Palette and type
# --------------------------------------------------------------------------
PAPER = '#f6f2e7'
NAVY = '#1a2440'
RED = '#b23a3a'
GOLD = '#c9a227'
GREEN = '#477453'
TEAL = '#397e85'
MUTED = '#555b63'
WHITE = '#ffffff'
BAND = '#ebe5d6'

SERIF = 'DejaVu Serif'
SANS = 'DejaVu Sans'
FONT_DIR = '/usr/share/fonts/truetype/dejavu/'

# Provenance vocabulary: a chip colour per confidence level.
PROV_COLORS = {'CONFIRMED': GREEN, 'OFFICIAL': TEAL, 'REPORTED': GOLD, 'CLAIM': RED}

# --------------------------------------------------------------------------
# Page geometry and copy (1024-wide coordinate space; SVG renders at 2x)
# --------------------------------------------------------------------------
PAGE = 1024
MARGIN = 14

# Masthead ---------------------------------------------------------------
MAST_LEFT = 'THE WORLD IN ONE DAY'
MAST_RIGHT = ('36 STORIES · 7 REGIONS · '
              'EVERY ONE DATED SATURDAY 21 NOVEMBER 2026')
MAST_DATE = 'Saturday 21 November 2026'
STRAPLINE = ('COP31 overruns with no fossil-fuel deal · three missiles downed '
             'over Riyadh · a magnitude-6.7 quake shakes Peru · Zelensky: '
             'the Crimea bridge "will not stay"')

# Stat band: value, caption ---------------------------------------------
STATS = [
    ('3', 'ballistic missiles downed over Riyadh'),
    ('M 6.7', 'quake shakes Peru; no damage'),
    ('58+', 'hurt in the Kryvyi Rih strike'),
    ('146', 'safe after a jet engine fire alert'),
    ('$55,122', "Bitcoin's 2-year low, early Saturday"),
    ('124*', "Rahul's unbeaten ton vs New Zealand"),
]

# Region pills: label, colour -------------------------------------------
REGION_PILLS = [
    ('WAR 7', RED),
    ('CLIMATE 5', TEAL),
    ('DIPLOMACY 5', NAVY),
    ('ASIA-PACIFIC 6', NAVY),
    ('AMERICAS 6', RED),
    ('EUROPE 4', NAVY),
    ('MARKETS & SPORT 3', GOLD),
]

# Lead cards: place · kicker, provenance, headline, body, sources, scene, chip
LEADS = [
    dict(
        place='ANTALYA, TÜRKIYE · CLIMATE',
        kicker='COP31: OVERTIME, NO DEAL',
        prov='CONFIRMED',
        head='Climate summit runs into Saturday with no deal on fossil fuels',
        body=('Plenary suspended Friday 22:29, resumed Saturday. Draft drops '
              'fossil-fuel language; Panama threatens to block it.'),
        source='UN News, AFP, Al Jazeera',
        scene='cop',
        chip='Plenary status',
    ),
    dict(
        place='RIYADH · WAR',
        kicker='3 MISSILES DOWNED',
        prov='CONFIRMED',
        head='Saudi air defences down three ballistic missiles over Riyadh',
        body=('Downed before dawn Saturday, days after the PIF tower was hit '
              'on Thursday. Houthis threaten Jeddah and Red Sea ports.'),
        source='Al Jazeera, AFP, SPA',
        scene='missiles',
        chip='Sat before dawn',
    ),
    dict(
        place='JUNÍN, PERU · EARTHQUAKE',
        kicker='QUAKE M 6.7',
        prov='CONFIRMED',
        head='Magnitude-6.7 earthquake shakes central Peru',
        body=('Struck 00:09 UTC — 19:09 Friday local — 108 km deep near '
              'Carhuamayo, felt in Lima. No deaths, damage or tsunami risk.'),
        source='USGS, Gestión',
        scene='quake',
        chip='00:09 UTC',
    ),
]

# Layout anchors ---------------------------------------------------------
CARD_Y = 156
CARD_W = 322
CARD_H = 177
CARD_XS = (14, 351, 688)

# --------------------------------------------------------------------------
# Engine state
# --------------------------------------------------------------------------
PLACED = []      # {'region','box','text','size','lines'} for every block()
SHORTENED = []   # (region, original, shortened) for any block that was trimmed
PARTS = []       # SVG fragments, joined in order by build()


def esc(value):
    return html.escape(str(value), quote=True)


def add(fragment):
    PARTS.append(fragment)


def reset():
    PLACED.clear()
    SHORTENED.clear()
    PARTS.clear()


# --------------------------------------------------------------------------
# SVG primitives
# --------------------------------------------------------------------------
def rect(x, y, w, h, fill, rx=0, opacity=1.0, stroke='none', sw=0):
    """An SVG rectangle; the single source of truth for box geometry."""
    out = (f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
           f'rx="{rx:g}" fill="{fill}"')
    if opacity != 1.0:
        out += f' opacity="{opacity:g}"'
    if stroke != 'none':
        out += f' stroke="{stroke}" stroke-width="{sw:g}"'
    return out + '/>'


def path(d, fill='none', stroke=NAVY, sw=1, extra=''):
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw:g}" {extra}/>')


def circle(x, y, r, fill, stroke='none', sw=1, opacity=1.0):
    out = (f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" fill="{fill}" '
           f'stroke="{stroke}" stroke-width="{sw:g}"')
    if opacity != 1.0:
        out += f' opacity="{opacity:g}"'
    return out + '/>'


def line(x1, y1, x2, y2, stroke=NAVY, sw=1, extra=''):
    return (f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
            f'stroke="{stroke}" stroke-width="{sw:g}" {extra}/>')


def text_node(s, x, y, size, bold=False, serif=False, italic=False,
              fill=NAVY, center=False, tracking=0):
    """One line of text. Italic is synthesised with skewX: the installed
    DejaVu family ships no italic face, and cairosvg would silently ignore
    font-style="italic" rather than slant the glyphs."""
    family = SERIF if serif else SANS
    anchor = 'middle' if center else 'start'
    weight = 700 if bold else 400
    attrs = (f'font-family="{family}" font-size="{size:g}" '
             f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"')
    if tracking:
        attrs += f' letter-spacing="{tracking:g}"'
    if not italic:
        return f'<text x="{x:g}" y="{y:g}" {attrs}>{esc(s)}</text>'
    # Skew about the baseline point so the line keeps its measured anchor.
    return (f'<g transform="translate({x:g} {y:g}) skewX(-11)">'
            f'<text x="0" y="0" {attrs}>{esc(s)}</text></g>')


# --------------------------------------------------------------------------
# Measurement: the PIL font is the authority for every width
# --------------------------------------------------------------------------
@lru_cache(maxsize=None)
def font(size, bold=False, serif=False):
    name = ('DejaVuSerif' if serif else 'DejaVuSans') + ('-Bold' if bold else '')
    return ImageFont.truetype(FONT_DIR + name + '.ttf', round(size * 20))


@lru_cache(maxsize=None)
def _measure_cached(s, size, bold, serif):
    return font(size, bold, serif).getlength(s) / 20


def measure(s, size, bold=False, serif=False, italic=False, tracking=0):
    """Width in page units, measured at 20x to keep sub-unit precision.
    The synthetic italic skew does not change advance widths."""
    base = _measure_cached(s, size, bold, serif)
    return base + tracking * max(len(s) - 1, 0)


def wrap(s, w, size, bold=False, serif=False, italic=False, tracking=0):
    """Greedy word wrap against the measured width."""
    rows = []
    for word in s.split():
        candidate = word if not rows else rows[-1] + ' ' + word
        if rows and measure(candidate, size, bold, serif, italic, tracking) > w:
            rows.append(word)
        else:
            if rows:
                rows[-1] = candidate
            else:
                rows.append(word)
    return rows


def intersects(a, b):
    """True when two axis-aligned boxes overlap by more than a hair."""
    return (a[0] < b[2] - 0.01 and a[2] > b[0] + 0.01 and
            a[1] < b[3] - 0.01 and a[3] > b[1] + 0.01)


# --------------------------------------------------------------------------
# The core text placement system
# --------------------------------------------------------------------------
def block(s, x, y, w, h, size=9, minimum=None, lines=1, bold=False,
          serif=False, italic=False, fill=NAVY, center=False,
          region='page', tracking=0):
    """Place wrapped text inside (x, y, w, h).

    The algorithm, in order:
      1. Wrap at `size` and measure the real ink box (centred lines are
         narrowed to their actual width).
      2. If the text needs more rows than allowed, is taller than h, wider
         than w, leaves the page, or collides with any box already placed,
         shrink the font by 0.25pt and retry — down to `minimum`.
      3. If it still does not fit, drop trailing words and add an ellipsis,
         retrying at the smallest size. Never drop below two words.
      4. If nothing works, raise AssertionError: silence is a bug.
    """
    minimum = size if minimum is None else minimum
    original = s
    while True:
        rows = wrap(s, w, size, bold, serif, italic, tracking)
        widths = [measure(r, size, bold, serif, italic, tracking) for r in rows]
        actual_w = max(widths, default=0)
        height = len(rows) * size * 1.25
        box = (x, y, x + w, y + height)
        if center:
            box = (x + (w - actual_w) / 2, y, x + (w + actual_w) / 2, y + height)
        conflict = any(intersects(box, old['box']) for old in PLACED)
        fits = (len(rows) <= lines and height <= h + 0.01
                and actual_w <= w + 0.01 and box[0] >= 0 and box[2] <= PAGE)
        if fits and not conflict:
            break
        if size > minimum:
            size = max(minimum, size - 0.25)
        elif conflict:
            # Shrinking is the only thing that can move a box out of the way.
            raise AssertionError(
                f'Collision ({region}): {original!r} box={box} '
                f'at minimum size {size:g}')
        elif len(s.split()) > 2:
            words = s.rstrip('…').split()
            s = ' '.join(words[:-1]).rstrip('.,;:') + '…'
        else:
            raise AssertionError(
                f'Layout failure ({region}): {original!r} box={box} '
                f'lines={len(rows)} at minimum size {size:g}')
    if s != original:
        SHORTENED.append((region, original, s))
    PLACED.append({'region': region, 'box': box, 'text': s,
                   'size': size, 'lines': len(rows)})
    for i, row in enumerate(rows):
        xx = x + w / 2 if center else x
        baseline = y + size + i * size * 1.25
        add(text_node(row, xx, baseline, size, bold=bold, serif=serif,
                      italic=italic, fill=fill, center=center,
                      tracking=tracking))
    return height


# --------------------------------------------------------------------------
# Composite components
# --------------------------------------------------------------------------
def pill(label, x, y, w, h, color, size=8, region='page'):
    """Rounded colour chip with a centred bold white label placed by block()."""
    add(rect(x, y, w, h, color, min(h / 2, 4)))
    pad = 3
    top = y + (h - size * 1.25) / 2
    block(label, x + pad, top, w - 2 * pad, size * 1.25, size,
          bold=True, fill=WHITE, center=True, region=region)


def number(n, x, y, region='page', r=7):
    """Red disc with a centred white numeral."""
    add(circle(x, y, r, RED))
    size = 7 if n < 10 else 6.5
    block(str(n), x - r, y - 0.65 * size, 2 * r, 1.25 * size, size,
          bold=True, fill=WHITE, center=True, region=region)


def card(x, y, w, h):
    """White card lifted off the paper by a soft navy shadow."""
    add(rect(x + 3, y + 3, w, h, NAVY, 6, 0.12))
    add(rect(x, y, w, h, WHITE, 6))


# --------------------------------------------------------------------------
# Scene art: original vector drawings normalised to a 196 x 52 canvas
# --------------------------------------------------------------------------
SCENE_W, SCENE_H = 196, 52


def scene_open(x, y, w, h):
    add(f'<g transform="translate({x:g} {y:g}) '
        f'scale({w / SCENE_W:.6f} {h / SCENE_H:.6f})">')


def scene_close():
    add('</g>')


def scene_cop(x, y, w, h, region):
    """Climate: teal globe with white meridians, a red thermometer, a clock."""
    add(rect(0, 0, SCENE_W, SCENE_H, '#dfe8e4'))
    # Globe
    add(circle(64, 26, 23, TEAL))
    add(path('M 41 26 H 87 M 64 3 Q 45 26 64 49 M 64 3 Q 83 26 64 49',
             stroke=WHITE, sw=0.9, extra='opacity=".75"'))
    add(path('M 43 15 Q 64 21 85 15 M 43 37 Q 64 31 85 37',
             stroke=WHITE, sw=0.7, extra='opacity=".6"'))
    # Thermometer
    add(rect(112, 9, 6, 25, WHITE, 3))
    add(rect(113.4, 19, 3.2, 16, RED, 1.6))
    add(circle(115, 36, 5.5, RED))
    add(line(115, 12, 115, 20, RED, 1.2))
    # Clock
    add(circle(136, 30, 12, WHITE, NAVY, 1.3))
    add(line(136, 30, 136, 22, NAVY, 1.3))
    add(line(136, 30, 142, 33.5, NAVY, 1.3))
    add(circle(136, 30, 1.2, RED))
    for tick in range(12):
        a = tick * math.pi / 6
        add(circle(136 + 9.7 * math.sin(a), 30 - 9.7 * math.cos(a), 0.45, NAVY))
    # Red "OVERTIME" chip, top right
    pill('OVERTIME', x + w * 0.755, y + 4, w * 0.205, 13, RED, 7, region)


def scene_missiles(x, y, w, h, region):
    """War: night sky, three red arcs ending in gold bursts, city silhouette."""
    add(rect(0, 0, SCENE_W, SCENE_H, 'url(#night)'))
    for i, (sx, ex, apex) in enumerate(((6, 58, 30), (40, 96, 20), (74, 132, 34))):
        add(path(f'M {sx} 50 Q {(sx + ex) / 2} {apex} {ex} 50',
                 stroke='#d94f4f', sw=1.8))
        add(circle(ex - 3, 49, 2.6, GOLD))
        add(circle(ex - 3, 49, 5.2, GOLD, opacity=0.35))
        add(line(sx, 50, sx + 6, 47, '#d94f4f', 1.4))
    # City silhouette
    for i, bh in enumerate((12, 17, 10, 20, 14, 23, 12, 18, 11, 16)):
        bx = 4 + i * 9.5
        add(rect(bx, 52 - bh, 7.5, bh, '#101a30'))
    for i in range(7):
        add(rect(6 + i * 13, 44 - (i % 3) * 3, 1.4, 2, GOLD, 0, 0.75))
    block('3 DOWNED', x + w * 0.755, y + 6, w * 0.21, 12, 9,
          bold=True, fill=GOLD, region=region)


def scene_quake(x, y, w, h, region):
    """Earthquake: pale ground, red seismograph, white magnitude readout."""
    add(rect(0, 0, SCENE_W, SCENE_H, '#efe9da'))
    add(line(0, 41, SCENE_W, 41, '#d8cfba', 0.8))
    add(path('M 0 32 H 20 l 5 -18 l 5 32 l 5 -38 l 5 29 l 4 -10 l 4 13 l 4 -21 '
             'l 4 15 H 196',
             stroke=RED, sw=1.8, extra='stroke-linejoin="round"'))
    # Readout card with the magnitude and depth, drawn as art
    add(rect(112, 7, 76, 33, WHITE, 3))
    add(rect(112, 7, 3, 33, RED, 1))
    sx, sy = w / SCENE_W, h / SCENE_H
    block('M 6.7', x + 119 * sx, y + 11 * sy, 64 * sx, 15 * sy, 12,
          bold=True, fill=RED, region=region)
    block('108 km deep', x + 119 * sx, y + 26 * sy, 64 * sx, 10 * sy, 7.5,
          fill=MUTED, region=region)


def scene(kind, x, y, w, h, region):
    scene_open(x, y, w, h)
    if kind == 'cop':
        scene_cop(x, y, w, h, region)
    elif kind == 'missiles':
        scene_missiles(x, y, w, h, region)
    elif kind == 'quake':
        scene_quake(x, y, w, h, region)
    else:
        raise AssertionError(f'unknown scene {kind!r}')
    scene_close()


# --------------------------------------------------------------------------
# Sections (each appends its own fragments to PARTS)
# --------------------------------------------------------------------------
def masthead():
    track = 0.45
    block(MAST_LEFT, MARGIN, 3, 300, 10, 8, bold=True, region='mast-left',
          tracking=track)
    # Right-aligned by measurement: block() draws left-to-right from x.
    right_w = measure(MAST_RIGHT, 8, tracking=track)
    block(MAST_RIGHT, PAGE - MARGIN - right_w, 3, right_w, 10, 8,
          region='mast-right', tracking=track)
    block(MAST_DATE, MARGIN, 14, PAGE - 2 * MARGIN, 65.5, 52, minimum=52,
          bold=True, serif=True, center=True, region='mast-date')
    block(STRAPLINE, MARGIN, 81, PAGE - 2 * MARGIN, 14.5, 11.5,
          minimum=10.5, serif=True, italic=True, fill=RED, center=True,
          region='strapline')
    add(line(MARGIN, 96.5, PAGE - MARGIN, 96.5, NAVY, 0.8))


def stat_band():
    add(rect(MARGIN, 99, PAGE - 2 * MARGIN, 32, BAND, 4))
    cell_w = (PAGE - 2 * MARGIN) / len(STATS)
    for i, (value, caption) in enumerate(STATS):
        x = MARGIN + i * cell_w
        if i:
            add(line(x, 104, x, 126, '#d6cdb8', 0.8))
        block(value, x + 4, 99.5, cell_w - 8, 21.5, 17, minimum=14,
              bold=True, fill=RED, center=True, region='stats')
        block(caption, x + 5, 121.2, cell_w - 10, 9, 7.2, minimum=6.5,
              center=True, fill=NAVY, region='stats')


def region_pills():
    gap = 8
    w = (PAGE - 2 * MARGIN - gap * (len(REGION_PILLS) - 1)) / len(REGION_PILLS)
    for i, (label, color) in enumerate(REGION_PILLS):
        pill(label, MARGIN + i * (w + gap), 134, w, 15, color, 7.2,
             region='regions')


def lead_cards():
    for i, lead in enumerate(LEADS):
        x, y, r = CARD_XS[i], CARD_Y, f'lead-{i + 1}'
        card(x, y, CARD_W, CARD_H)
        # Scene band, clipped to the card's rounded top corners
        add(f'<clipPath id="clip-lead-{i + 1}"><rect x="{x}" y="{y}" '
            f'width="{CARD_W}" height="69" rx="6"/></clipPath>')
        add(f'<g clip-path="url(#clip-lead-{i + 1})">')
        scene(lead['scene'], x, y, CARD_W, 69, r)
        add('</g>')
        # Caption + provenance chips on the seam
        pill(lead['chip'], x + 8, y + 57, 104, 14, NAVY, 7.5, r)
        pill(lead['prov'], x + 118, y + 57, 88, 14,
             PROV_COLORS[lead['prov']], 7.5, r)
        # Place line, numbered
        number(i + 1, x + 17, y + 83, r)
        block(lead['place'], x + 30, y + 78, 282, 10, 8, bold=True,
              region=r)
        # Kicker, headline, body, sources
        pill(lead['kicker'], x + 10, y + 90, 172, 14, RED, 8, r)
        block(lead['head'], x + 10, y + 108, CARD_W - 20, 35, 14,
              minimum=12.5, bold=True, serif=True, lines=2, region=r)
        block(lead['body'], x + 10, y + 145, CARD_W - 20, 21, 8.25,
              minimum=7.5, lines=2, region=r)
        block('(' + lead['source'] + ')', x + 10, y + 166,
              CARD_W - 20, 9.5, 7.2, italic=True, fill=MUTED, region=r)


def build():
    """Assemble the whole page. Later phases append sections before the
    closing tag; the order of calls is the order of the page."""
    reset()
    add('<svg xmlns="http://www.w3.org/2000/svg" width="2048" height="2048" '
        'viewBox="0 0 2048 2048">'
        '<defs>'
        '<linearGradient id="night" x1="0" y1="0" x2="0" y2="1">'
        '<stop stop-color="#10182d"/><stop offset="1" stop-color="#38415a"/>'
        '</linearGradient>'
        '<radialGradient id="fire">'
        '<stop stop-color="#e28d44" stop-opacity=".9"/>'
        '<stop offset="1" stop-color="#b23a3a" stop-opacity="0"/>'
        '</radialGradient>'
        '</defs>'
        '<g transform="scale(2)">')
    add(rect(0, 0, PAGE, PAGE, PAPER))

    masthead()
    stat_band()
    region_pills()
    lead_cards()

    # --- later phases insert more sections here ---

    add('</g></svg>')
    verify()
    return ''.join(PARTS)


def verify():
    """A final independent pass: every reserved box is on the page, inside
    its own limits, and no two boxes overlap."""
    for i, a in enumerate(PLACED):
        assert 0 <= a['box'][0] <= a['box'][2] <= PAGE, a
        assert 0 <= a['box'][1] <= a['box'][3] <= PAGE, a
        for b in PLACED[i + 1:]:
            assert not intersects(a['box'], b['box']), (a, b)


# --------------------------------------------------------------------------
# Deterministic rasterisation
# --------------------------------------------------------------------------
def render_png(svg):
    """Raster at 2x, downscale with LANCZOS, save an optimised RGB PNG."""
    png = cairosvg.svg2png(bytestring=svg.encode('utf-8'),
                           output_width=2048, output_height=2048)
    with Image.open(BytesIO(png)) as raw:
        image = raw.convert('RGB').resize((1024, 1024),
                                          Image.Resampling.LANCZOS)
        out = BytesIO()
        image.save(out, format='PNG', optimize=True)
    return out.getvalue()


def main():
    first_svg = build()
    first = render_png(first_svg)
    # Build a second time from scratch: the engine's global state must not
    # leak between runs, and the bytes must match exactly.
    second = render_png(build())
    assert first == second, 'Render is not deterministic'

    with Image.open(BytesIO(first)) as check:
        assert check.size == (1024, 1024), check.size
        assert check.mode == 'RGB', check.mode
    assert len(first) <= 1048576, f'PNG exceeds 1 MiB: {len(first)} bytes'

    out_dir = os.environ.get('MAKEFUN_OUTPUT_DIR', '.')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'entry.png'), 'wb') as fh:
        fh.write(first)

    # Final independent sweep over every reserved box.
    collisions = sum(1 for i, a in enumerate(PLACED)
                     for b in PLACED[i + 1:] if intersects(a['box'], b['box']))
    assert collisions == 0, f'{collisions} collisions'
    print(f'text blocks checked: {len(PLACED)}')
    print(f'shortened: {len(SHORTENED)}')
    for region, original, short in SHORTENED:
        print(f'  {region}: {short!r}')
    print(f'collisions: {collisions}')
    print(f'wrote entry.png: 1024x1024 RGB, {len(first)} bytes')


if __name__ == '__main__':
    main()
