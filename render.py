#!/usr/bin/env python3
"""Saturday 21 November 2026 — the day's world news on one deterministic page.

This file is built in PARTS. Phase 1 implements the layout ENGINE and the TOP
of the page: masthead, stat band, region pills and three lead cards. Phase 2
adds the ten feature cards, each with its own original vector scene. Later
phases append further sections to build() before the single final render.

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

# The day in UTC: (hour, minute, caption, side). Each tick's clock-and-caption
# block is stacked either above or below the axis, alternating tick by tick so
# that the five events crowded into the first six hours cannot collide.
TICKS = [
    (0, 9, 'Peru quake M 6.7 · USGS', 'up'),
    (2, 15, 'Finland restricts Gulf airspace', 'down'),
    (4, 0, 'Vegas: Verstappen P1', 'up'),
    (5, 0, 'Tanker hit 11 nmi off Khasab · UKMTO', 'down'),
    (5, 50, '2nd tanker 17 nmi east · UKMTO', 'up'),
    (15, 30, 'Anatra: EU-CEPA pact signed', 'down'),
    (17, 30, 'Newcastle: vASarell 2-2', 'up'),
]

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
        place='HORMUZ · IRAN WAR',
        kicker='GULF · IRAN WAR',
        prov=(('CONFIRMED', TEAL), ('CLAIM', GOLD)),
        head='Iran strikes Bahrain bases; tankers hit off Oman',
        body=('IRGC says it hit US radars at two bases; Bahrain says a civilian '
              'plant burned. UKMTO: two tankers struck off Khasab.'),
        body_fill=MUTED,
        source='UKMTO, IRIB, BNA',
        scene='gulf',
        chip='Gulf escalation',
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

# Feature cards: number, kicker, provenance, headline, body, sources, scene
FEATURES = [
    dict(n='04', kicker='KYIV · WAR', prov='OFFICIAL', scene='bridge',
         head='Zelensky: the Crimea bridge "will not stay"',
         body=('Interview given Friday, aired into Saturday; warns of '
               'double-tap strikes.'),
         source='NBC, Kyiv Independent'),
    dict(n='05', kicker='KRYVYI RIH · WAR', prov='CONFIRMED', scene='kyiv',
         head='Ballistic strike on Kryvyi Rih kills two, hurts dozens',
         body=('A boy and a young medic died; the toll rose past 58 in a '
               '"double-tap".'),
         source='AP, DW'),
    dict(n='06', kicker='TEHRAN · DIPLOMACY', prov='OFFICIAL', scene='flags',
         head='Iran: enriched uranium stock "stays in the country"',
         body=('Araghchi still sees a "fair solution" with Washington on '
               'the table.'),
         source='Iran newspaper, Reuters'),
    dict(n='07', kicker='RIYADH · WAR', prov='OFFICIAL', scene='riyadh',
         head='Three ballistic missiles downed over Riyadh',
         body=('Downed before dawn Saturday, days after the PIF tower was '
               'hit.'),
         source='Al Jazeera, AFP, SPA'),
    dict(n='08', kicker='WASHINGTON · TECH', prov='CONFIRMED', scene='scales',
         head='Trump vows a "tremendous tax" on data centres abroad',
         body=('US firms building AI data centres overseas would pay; no '
               'details given.'),
         source='CNBC, AP'),
    dict(n='09', kicker='BEIJING · DIPLOMACY', prov='CONFIRMED', scene='deal',
         head='China tells Japan to "correct" its words on Taiwan',
         body=("Guo Jiakun's remarks came Friday; Tokyo says its stance is "
               'unchanged.'),
         source='Straits Times, CGTN'),
    dict(n='10', kicker='DAVAO · AVIATION', prov='CONFIRMED', scene='jet',
         head='Jet lands safely after engine fire alert',
         body=('Air Niugini 767 from Hong Kong diverted past midnight; '
               '146 safe.'),
         source='AP, CNA'),
    dict(n='11', kicker='CANBERRA · DIPLOMACY', prov='CONFIRMED', scene='globe',
         head='Australia and China agree to talks on AI',
         body=("Agreed at the leaders' meeting with Li Qiang; Albanese ends "
               '11-day trip.'),
         source='ABC, PM.gov.au'),
    dict(n='12', kicker='WELLINGTON · CRICKET', prov='CONFIRMED', scene='cricket',
         head='Rahul hits an unbeaten 124 against New Zealand',
         body=('124* at tea, India 344/2 replying to 368; tons in all four '
               'SENA lands.'),
         source='AFP, The Hindu'),
    dict(n='13', kicker='LAS VEGAS · F1', prov='CONFIRMED', scene='chart',
         head='Russell fastest; Verstappen to stewards',
         body=('1:34.041 in a damp Friday session; their contact is under '
               'review.'),
         source='F1.com, FIA'),
]

# Big data callouts stamped into the top-right of each feature-card scene,
# keyed by story number: (value, caption, colour).
#
# The figures are the ones this sheet itself verifies: the 58+ hurt above, the
# 146 safe on the Davao flight, Rahul's 124*, the three missiles over Riyadh.
# Eight stories from the brief (Gulf of Finland drones, robot arms, the cartel
# capture, EU-Indonesia, Basra, Taiwan markets, the rugby score, the CAF vote,
# Mastung) are not feature cards on this page, so their callouts have no card
# to sit on; TAX and CORRECT are the quotable facts of cards 08 and 09.
FEATURE_CALLOUTS = {
    '04': ('FRI', 'INTERVIEW GIVEN', NAVY),
    '05': ('58+', 'HURT IN STRIKE', RED),
    '06': ('STAYS', 'URANIUM STOCK', NAVY),
    '07': ('3', 'MISSILES DOWNED', RED),
    '08': ('TAX', 'ON DATA CENTRES', NAVY),
    '09': ('CORRECT', 'BEIJING TO TOKYO', NAVY),
    '10': ('146', 'SAFE ON BOARD', NAVY),
    '11': ('11', 'DAY TRIP ENDS', NAVY),
    '12': ('124*', 'NOT OUT AT TEA', RED),
    '13': ('P1', 'VERSTAPPEN · VEGAS', RED),
}

# Layout anchors ---------------------------------------------------------
# Timeline strip: sits between the masthead rule and the stat band.
TL_Y, TL_H = 75, 34
TL_AXIS_X, TL_AXIS_W = 52, 954   # 00:00 .. 23:59 spans the axis exactly
TL_AXIS_DY = 16.5                # axis offset inside the strip

CARD_Y = 160
CARD_W = 322
CARD_H = 177
CARD_XS = (14, 351, 688)

# Feature grid: five equal columns filling x=14..1010 with 8px gutters.
# (996 - 4*8) / 5 = 192.8; the brief's "182.4" leaves a 52px ragged edge.
FEAT_W = (1010 - MARGIN - 4 * 8) / 5
FEAT_H = 132
FEAT_GAP = 8
FEAT_XS = tuple(MARGIN + i * (FEAT_W + FEAT_GAP) for i in range(5))
FEAT_YS = (341, 481)
FEAT_SCENE_H = 50

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


# Lead-scene labels are queued while the scaled art group is open and emitted
# once it is closed, so they are measured, collision-checked and drawn in PAGE
# coordinates exactly where the reader sees them.
SCENE_LABELS = []   # (text, x, y, w, h, size, kwargs)
SCENE_PILLS = []    # (label, x, y, w, h, colour, size, region)
SCENE_PLATES = []   # (x, y, w, h, fill, rx, opacity) in page coordinates


def scene_label(s, x, y, w, h, size, **kw):
    SCENE_LABELS.append((s, x, y, w, h, size, kw))


def scene_pill(label, x, y, w, h, color, size, region):
    SCENE_PILLS.append((label, x, y, w, h, color, size, region))


def scene_plate(x, y, w, h, fill, rx=0, opacity=1.0):
    """A rectangle in page coordinates, emitted after the scaled art group.

    Scene art is drawn on a 196 x 52 canvas stretched to the band, so a rect
    inside that group would scale non-uniformly and its corner radius would
    shear. Anything that must stay pixel-exact is queued here instead.
    """
    SCENE_PLATES.append((x, y, w, h, fill, rx, opacity))


def callout(x, y, w, h, value, caption, color):
    """A small white card with a big bold figure and a tiny muted caption.

    Drawn after the scene's scaled group closes, so both strings go through
    block() in page coordinates and reserve real boxes. The card is opaque,
    so whatever art sat under the corner is covered rather than showing
    through; the coloured rule on its left edge ties it to the card accent.
    """
    add(rect(x, y, w, h, WHITE, 2))
    add(rect(x, y, 2.4, h, color))
    add(rect(x + 0.5, y + 0.5, w - 1, h - 1, 'none', 2, stroke='#cfc8b6', sw=0.6))
    block(value, x + 6, y + 2.0, w - 10, 13.6, 10.5, minimum=7.5, bold=True,
          serif=True, fill=color, region='callout')
    block(caption, x + 6, y + 15.9, w - 10, 6.4, 5.0, minimum=4.0,
          fill=MUTED, region='callout')


def scene_cop(x, y, w, h, region):
    """Climate: teal globe with white meridians, a red thermometer, a clock,
    and a 13-box calendar counter for the summit's 12 scheduled days plus one.

    The globe, thermometer and clock are packed into the left 106 scene units
    so the counter owns the right of the band. The counter is drawn as art in
    scene units, but its numerals and captions are queued in page coordinates
    through scene_label() so block() measures and reserves them like any other
    text.
    """
    add(rect(0, 0, SCENE_W, SCENE_H, '#dfe8e4'))
    # Globe
    add(circle(40, 26, 20, TEAL))
    add(path('M 20 26 H 60 M 40 6 Q 23 26 40 46 M 40 6 Q 57 26 40 46',
             stroke=WHITE, sw=0.9, extra='opacity=".75"'))
    add(path('M 22 16 Q 40 21 58 16 M 22 36 Q 40 31 58 36',
             stroke=WHITE, sw=0.7, extra='opacity=".6"'))
    # Thermometer
    add(rect(70, 9, 5.4, 23, WHITE, 3))
    add(rect(71.3, 18, 2.8, 15, RED, 1.4))
    add(circle(72.7, 34, 5, RED))
    add(line(72.7, 12, 72.7, 19, RED, 1.1))
    # Clock
    add(circle(92, 30, 10, WHITE, NAVY, 1.3))
    add(line(92, 30, 92, 23, NAVY, 1.3))
    add(line(92, 30, 97, 33.5, NAVY, 1.3))
    add(circle(92, 30, 1.2, RED))
    for tick in range(12):
        a = tick * math.pi / 6
        add(circle(92 + 8 * math.sin(a), 30 - 8 * math.cos(a), 0.45, NAVY))
    # The day counter: thirteen calendars, 9..21. Twelve were scheduled; the
    # thirteenth, in red, is the overtime Saturday the summit ran into.
    # Everything is laid out in page units and queued, so the boxes stay
    # square-ish and the numerals sit on whole pixels.
    bw_p, bh_p, gap_p = 8.4, 11.0, 0.55      # page units
    left_p, top_p = x + 178, y + 11.0
    grey, grey_ink = '#b7b0a0', '#3b372e'
    for k, day in enumerate(range(9, 22)):
        bx = left_p + k * (bw_p + gap_p)
        hot = day == 21
        scene_plate(bx, top_p, bw_p, bh_p, RED if hot else grey, 1.2)
        scene_label(str(day), bx, top_p + 2.7, bw_p, 6.0, 4.4,
                    bold=True, fill=WHITE if hot else grey_ink, center=True)
    # Under the strip: the key on the left, the overtime pill on the right,
    # then the one-line caption that explains both.
    base = top_p + 12.6
    scene_label('SCHEDULED DAYS', left_p + 0.5, base, 60, 7.0, 4.5,
                bold=True, fill=MUTED, tracking=0.2)
    pill_x = left_p + 13 * (bw_p + gap_p) - 25
    scene_plate(pill_x, base - 0.7, 25, 9.0, GOLD, 4.5)
    scene_label('+1 DAY', pill_x, base + 0.2, 25, 7.2, 5.2,
                bold=True, fill=NAVY, center=True)
    scene_label('Day 13 of a 12-day summit', left_p + 0.5, base + 9.0,
                132, 8.0, 5.4, fill=MUTED)


def scene_gulf(x, y, w, h, region):
    """Iran war: night water, a muted-teal Hormuz strait, red strikes.

    Geometry is drawn in the 196 x 52 scene canvas. All label ink stays above
    scene y=41: the caption and provenance pills cover the band below that.
    Labels are queued in page coordinates so block() measures and
    collision-checks them exactly where the reader sees them.

    Reading left to right: Bahrain (the red starburst) in the lower left,
    the Iranian coast and the IRAN label across the top right, the KHASAB
    point below it, and the two burning tankers out in the channel.
    """
    add(rect(0, 0, SCENE_W, SCENE_H, '#0d1b2e'))
    # Water texture: pale wave rules across the open Gulf.
    for wy, x1, x2 in ((31, 4, 66), (41, 2, 56), (48, 16, 88)):
        add(path(f'M {x1} {wy} q 9 -2 18 0 t 18 0 t 18 0 t 18 0',
                 stroke='#24405c', sw=0.7))
    # The Iranian coast fills the top-right, so the IRAN label sits on land.
    add(path('M 54 0 L 196 0 L 196 16 Q 172 14 152 16 Q 126 19 106 13 '
             'Q 82 8 54 0 Z', fill='#31465e', stroke='#48607a', sw=0.6))
    # The Arabian shore runs along the bottom left, under Bahrain.
    add(path('M 0 40 L 104 40 Q 84 46 56 48 Q 26 51 0 52 Z',
             fill='#31465e', stroke='#48607a', sw=0.6))
    # The strait: a broad muted-teal channel between the two coasts.
    strait = ('M 0 28 Q 34 25 62 28 Q 96 31 124 25 Q 150 19 176 21 '
              'Q 186 22 196 19 L 196 30 Q 180 32 170 30 Q 146 28 124 34 '
              'Q 96 41 62 38 Q 34 36 0 38 Z')
    add(path(strait, fill=TEAL, stroke='none', extra='opacity=".62"'))
    add(path('M 0 28 Q 34 25 62 28 Q 96 31 124 25 Q 150 19 176 21 Q 186 22 196 19',
             stroke='#9ccdd0', sw=0.55, extra='opacity=".6"'))
    # Bahrain: a small island with a red starburst over it.
    add('<ellipse cx="58" cy="40" rx="11" ry="4" fill="#3b5069"/>')
    add(circle(58, 39, 1.9, RED))
    for k in range(8):
        a = k * math.pi / 4
        add(line(58 + 2.3 * math.cos(a), 39 + 2.3 * math.sin(a),
                 58 + 6.8 * math.cos(a), 39 + 6.8 * math.sin(a),
                 '#ff6b5a', 1.1))
    add(circle(58, 39, 9.0, RED, opacity=0.22))
    # Khasab point on the Iranian side of the strait.
    add(circle(114, 17, 1.9, WHITE))
    add(circle(114, 17, 4.0, WHITE, opacity=0.18))
    # Two burning tankers east of Khasab, out in the channel.
    for tx, ty in ((150, 28), (172, 24)):
        add(f'<path d="M {tx - 7} {ty} L {tx + 7} {ty} L {tx + 4} {ty + 3.4} '
            f'L {tx - 4} {ty + 3.4} Z" fill="#516884" stroke="#a6bcd4" '
            f'stroke-width="0.55"/>')
        add(circle(tx, ty - 1.6, 1.9, GOLD))
        add(circle(tx, ty - 1.6, 4.6, '#e28d44', opacity=0.5))
        add(path(f'M {tx} {ty - 4} q 2 -3.4 0 -6', stroke='#d6c3a4',
                 sw=0.75, extra='opacity=".75"'))
    # Thin red dashed arcs from the IRAN label out to Bahrain and the two
    # burning ships — the strike lines the story describes.
    add(path('M 148 8 Q 108 22 68 33', stroke='#ff5a4a', sw=1.25,
             extra='stroke-dasharray="3.4 2.4"'))
    add(path('M 158 9 Q 154 19 150 24', stroke='#ff5a4a', sw=1.15,
             extra='stroke-dasharray="3.4 2.4"'))
    add(path('M 168 10 Q 170 16 172 20', stroke='#ff5a4a', sw=1.1,
             extra='stroke-dasharray="3.4 2.4"'))
    sx, sy = w / SCENE_W, h / SCENE_H
    scene_label('IRAN', x + 150 * sx, y + 0.8 * sy, 30 * sx, 7.2 * sy, 6.6,
                bold=True, fill='#ffd7d1', center=True)
    scene_label('KHASAB', x + 88 * sx, y + 13.0 * sy, 30 * sx, 6.6 * sy, 5.4,
                bold=True, fill=WHITE, center=True)
    scene_label('BAHRAIN', x + 44 * sx, y + 35.0 * sy, 32 * sx, 6.6 * sy, 5.4,
                bold=True, fill='#ffd7d1', center=True)


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
    # Centre the magnitude in the readout card (inner width 69 scene units).
    scene_label('M 6.7', x + 115 * sx, y + 18 * sy, 70 * sx, 15 * sy, 12,
                bold=True, fill=RED, center=True)
    # Depth sits left of the readout card, in the clear sky above the flat
    # tail of the trace (the spike ends at scene x=55).
    scene_label('108 km deep', x + 58 * sx, y + 17 * sy, 52 * sx, 10 * sy,
                7.5, bold=True, fill=MUTED)


def scene(kind, x, y, w, h, region):
    SCENE_LABELS.clear()
    SCENE_PILLS.clear()
    SCENE_PLATES.clear()
    scene_open(x, y, w, h)
    if kind == 'cop':
        scene_cop(x, y, w, h, region)
    elif kind == 'gulf':
        scene_gulf(x, y, w, h, region)
    elif kind == 'quake':
        scene_quake(x, y, w, h, region)
    else:
        raise AssertionError(f'unknown scene {kind!r}')
    scene_close()
    for px, py, pw, ph, fill, rx, opacity in SCENE_PLATES:
        add(rect(px, py, pw, ph, fill, rx, opacity))
    for label, px, py, pw, ph, color, size, reg in SCENE_PILLS:
        pill(label, px, py, pw, ph, color, size, reg)
    for s, lx, ly, lw, lh, size, kw in SCENE_LABELS:
        block(s, lx, ly, lw, lh, size, region=region, **kw)
    SCENE_LABELS.clear()
    SCENE_PILLS.clear()
    SCENE_PLATES.clear()


# --------------------------------------------------------------------------
# Feature scenes. Shapes are drawn in the normalised 196 x 52 canvas, but any
# *text* is registered in PAGE coordinates and emitted only after the scaled
# group is closed, so every label is measured and collision-checked exactly
# like the rest of the page (and lands where the reader sees it).
# --------------------------------------------------------------------------
def sc_kyiv(x, y, w, h):
    """Kyiv at night: skyline, gold windows, fire glow, red streaks.

    The three right-hand blocks are kept to 22 scene units tall (top edge at
    y=30) so the data callout in the band's top-right corner has clear sky.
    """
    add(rect(0, 0, SCENE_W, SCENE_H, 'url(#night)'))
    add('<ellipse cx="104" cy="50" rx="58" ry="16" fill="url(#fire)"/>')
    for i, (bx, bw, bh) in enumerate((
            (0, 16, 26), (17, 12, 34), (30, 14, 22), (45, 11, 30),
            (57, 16, 40), (74, 12, 24), (87, 15, 33), (103, 12, 20),
            (116, 16, 37), (133, 12, 22), (146, 14, 20), (161, 11, 22),
            (173, 23, 20))):
        add(rect(bx, 52 - bh, bw, bh, '#0d1526'))
        cols = max(1, (bw - 4) // 5)
        rows = max(1, (bh - 6) // 7)
        for c in range(int(cols)):
            for r in range(int(rows)):
                if (i + c * 3 + r * 5) % 3 == 0:
                    add(rect(bx + 2.5 + c * 5, 52 - bh + 4 + r * 7,
                             1.3, 1.8, GOLD, 0, 0.85))
    add(path('M 4 4 L 42 21', stroke='#d94f4f', sw=1.5))
    add(path('M 26 2 L 62 18', stroke='#d94f4f', sw=1.1))


def sc_bridge(x, y, w, h):
    """Kerch bridge at night, cut by red slashes; the label sits in the sky.
    Everything structural stays below scene y=17 so the label band at the
    top of the scene is clear ink."""
    add(rect(0, 0, SCENE_W, SCENE_H, 'url(#night)'))
    add(rect(0, 44, SCENE_W, 8, '#0a1120'))
    add(path('M 0 39 Q 98 31 196 39', stroke='#8fa2c9', sw=4.6))
    for tx in (46, 150):
        add(line(tx, 17, tx, 46, '#8fa2c9', 4.6))
        add(line(tx - 7, 23, tx + 7, 23, '#8fa2c9', 3.0))
    add(path('M 0 21 Q 23 29 46 17 Q 98 34 150 17 Q 173 29 196 21',
             stroke='#8fa2c9', sw=2.0))
    for hx in (18, 30, 60, 72, 86, 110, 124, 138, 164, 178):
        top = (21 + (hx / 46) * -4 if hx < 46 else
               (17 + abs(hx - 98) / 52 * 17 if hx < 150 else
                17 + (196 - hx) / 46 * 4))
        add(line(hx, top, hx, 38.4, '#8fa2c9', 1.1))
    add(path('M 64 20 L 80 33', stroke='#ff5a4a', sw=3.0))
    add(path('M 118 21 L 102 34', stroke='#ff5a4a', sw=3.0))
    scene_label('WILL NOT STAY', x + 7, y + 3, 104, 12, 8.5,
                bold=True, fill=WHITE)


def sc_flags(x, y, w, h):
    """Tehran talks: two flags on poles over a pale ground, teal link curve."""
    add(rect(0, 0, SCENE_W, SCENE_H, '#efe9da'))
    add(line(56, 9, 56, 51, NAVY, 1.6))
    add(line(128, 9, 128, 51, NAVY, 1.6))
    add(rect(56, 9, 46, 27, RED))
    add(circle(79, 22.5, 7, GOLD))
    add(rect(128, 11, 42, 25, WHITE, 0, 1.0, NAVY, 0.8))
    add(circle(149, 23.5, 6.5, RED))
    add(path('M 18 45 Q 96 31 178 45', stroke=TEAL, sw=1.6))
    add(circle(96, 37.5, 2.0, TEAL))


def sc_riyadh(x, y, w, h):
    """Riyadh: night sky over a skyline, three missile trails and intercepts."""
    add(rect(0, 0, SCENE_W, SCENE_H, 'url(#night)'))
    # Skyline silhouette: low blocks and one tall tower. Everything sits
    # below scene y=26 so the label band across the top is clear ink.
    for bx, bw, bh in ((0, 15, 15), (16, 11, 22), (28, 13, 12), (42, 10, 18),
                       (53, 14, 11), (68, 12, 20), (81, 9, 14), (91, 13, 9),
                       (105, 11, 16), (117, 12, 10)):
        add(rect(bx, 52 - bh, bw, bh, '#0c1526'))
        if bh > 15:
            add(rect(bx + bw / 2 - 1.2, 52 - bh - 3, 2.4, 3.4, '#0c1526'))
    # A tapered tower for scale, with a single aircraft-warning light.
    add('<path d="M 136 52 L 139 27 L 143 27 L 146 52 Z" fill="#0c1526"/>')
    add(circle(141, 26.4, 0.9, RED))
    for i in range(9):
        add(rect(4 + i * 12.5, 46 - (i % 3) * 2.5, 1.3, 1.8, GOLD, 0, 0.6))
    # Three thin trails rising from the horizon, each ending in a burst.
    for sx, ex, ey, apex in ((56, 86, 22, 36), (72, 108, 17, 28),
                             (88, 130, 22, 32)):
        add(path(f'M {sx} 51 Q {(sx + ex) / 2} {apex} {ex} {ey}',
                 stroke='#ff6b5a', sw=1.5))
        add(circle(ex, ey, 2.2, GOLD))
        add(circle(ex, ey, 4.6, GOLD, opacity=0.35))
        add(circle(ex, ey, 7.2, GOLD, opacity=0.14))
    # Three intercept bursts on a small white tally board, top-left. The
    # board is pure art: the "3 MISSILES DOWNED" callout in the opposite
    # corner already says it in words, so repeating text here would double
    # the figure and crowd the band.
    sx, sy = w / SCENE_W, h / SCENE_H
    add(rect(8 * sx, 4 * sy, 30 * sx, 34 * sy, WHITE, 2))
    add(rect(8 * sx, 4 * sy, 2.6 * sx, 34 * sy, RED))
    for k in range(3):
        cy = (11 + k * 9) * sy
        add(circle(25 * sx, cy, 2.3 * sx, GOLD))
        add(circle(25 * sx, cy, 4.6 * sx, GOLD, opacity=0.30))
        add(circle(25 * sx, cy, 6.8 * sx, GOLD, opacity=0.12))


def sc_scales(x, y, w, h):
    """Washington: scales of justice in navy and teal on pale paper."""
    add(rect(0, 0, SCENE_W, SCENE_H, '#efe9da'))
    add(rect(84, 44, 30, 3.2, NAVY, 1))
    add(line(99, 12, 99, 45, NAVY, 2.4))
    add(line(49, 16, 149, 16, NAVY, 2.2))
    add(circle(99, 16, 3.2, GOLD))
    for cx in (49, 149):
        # Pans hang *below* the beam: apex at the beam, bowl opening upward
        add(line(cx, 16, cx - 14, 34, NAVY, 0.8))
        add(line(cx, 16, cx + 14, 34, NAVY, 0.8))
        add(path(f'M {cx - 15} 34 Q {cx} 43 {cx + 15} 34 Z',
                 fill=TEAL, stroke=TEAL, sw=0.8))
        add(line(cx - 15, 34, cx + 15, 34, NAVY, 1.2))


def sc_deal(x, y, w, h):
    """Beijing: two overlapping flags, red and white, joined by a teal curve."""
    add(rect(0, 0, SCENE_W, SCENE_H, '#f0ece2'))
    add(rect(50, 11, 58, 33, RED, 2))
    add(rect(88, 9, 58, 33, WHITE, 2, 1.0, NAVY, 0.9))
    add(circle(117, 25.5, 6, RED))
    add(path('M 26 44 Q 66 27 98 36 Q 130 45 172 27', stroke=TEAL, sw=2.0))
    add(circle(98, 36, 2.4, TEAL))


def sc_jet(x, y, w, h):
    """Davao: airliner side view in a pale sky, red alert disc at the tail."""
    add(rect(0, 0, SCENE_W, SCENE_H, '#dfe9f2'))
    # Motion streaks trailing behind the tail
    for yy, ln in ((41, 16), (45, 11), (49, 7)):
        add(line(6, yy, 6 + ln, yy, '#c05050', 1.2, 'opacity=".6"'))
    # Tail fin, then the fuselage over it, nose to the right
    add(f'<path d="M 58 22 L 50 5 L 66 5 L 74 22 Z" fill="{WHITE}" '
        f'stroke="{NAVY}" stroke-width="1.1"/>')
    add(f'<path d="M 50 31 L 36 38 L 52 38 L 62 32 Z" fill="{WHITE}" '
        f'stroke="{NAVY}" stroke-width="1.0"/>')
    add(f'<path d="M 56 23 Q 56 19 63 19 L 150 19 Q 168 20 176 27 '
        f'Q 168 35 150 36 L 63 36 Q 56 36 56 31 Z" fill="{WHITE}" '
        f'stroke="{NAVY}" stroke-width="1.3"/>')
    # Swept wing down and back, with an engine pod beneath it
    add(f'<path d="M 112 30 L 86 47 L 108 47 L 128 32 Z" fill="{WHITE}" '
        f'stroke="{NAVY}" stroke-width="1.1"/>')
    add(f'<path d="M 104 33 L 92 43 L 104 43 L 112 33 Z" fill="#c9d6e2" '
        f'stroke="{NAVY}" stroke-width="0.9"/>')
    # Cabin windows and cockpit
    for i in range(9):
        add(circle(76 + i * 7, 26, 1.2, NAVY))
    add(f'<path d="M 158 22 Q 166 23 170 27 Q 166 31 158 31 Z" '
        f'fill="{NAVY}"/>')
    sx, sy = w / SCENE_W, h / SCENE_H
    add(circle(30, 15, 8, RED))
    scene_label('!', x + 30 * sx - 6.5, y + 15 * sy - 6.2, 13, 12.5, 9.5,
                bold=True, fill=WHITE, center=True)


def sc_globe(x, y, w, h):
    """Canberra: teal globe with white meridians and two small flag pins."""
    add(rect(0, 0, SCENE_W, SCENE_H, '#efe9da'))
    add(circle(98, 27, 20, TEAL))
    add(path('M 78 27 H 118 M 98 7 Q 80 27 98 47 M 98 7 Q 116 27 98 47',
             stroke=WHITE, sw=0.9, extra='opacity=".75"'))
    add(path('M 80 16 Q 98 21 116 16 M 80 38 Q 98 33 116 38',
             stroke=WHITE, sw=0.7, extra='opacity=".6"'))
    for px_, py_, col in ((66, 7, RED), (130, 29, NAVY)):
        add(line(px_, py_, px_, py_ + 12, NAVY, 1.2))
        add(rect(px_, py_, 11, 7, col))


def sc_cricket(x, y, w, h):
    """Wellington: bat, ball and the big red not-out score."""
    add(rect(0, 0, SCENE_W, SCENE_H, '#eef0e6'))
    add(rect(0, 40, SCENE_W, 12, '#7fa06a'))
    add(line(0, 40, SCENE_W, 40, '#4f7040', 1.2))
    # Bat leaning up and to the right: navy grip at the top, willow blade below
    add(f'<g transform="translate(54 47) rotate(34)">'
        f'<rect x="-2.6" y="-33" width="5.2" height="14" fill="{NAVY}" rx="1.2"/>'
        f'<rect x="-2.6" y="-20" width="5.2" height="3" fill="#d9d4c8"/>'
        f'<path d="M -5.4 -17 H 5.4 V 0 Q 5.4 4 0 4 Q -5.4 4 -5.4 0 Z" '
        f'fill="#b07c47"/>'
        f'<path d="M -5.4 -17 H -1.6 V 0 Q -1.6 4 -5.4 0 Z" fill="#c99259"/>'
        f'</g>')
    add(circle(92, 33, 3.8, RED))
    add(circle(92, 33, 3.8, RED, stroke=WHITE, sw=0.6))
    add(path('M 88.6 31.6 Q 92 33.4 95.4 31.6', stroke='#f0c9c9', sw=0.6))


def sc_chart(x, y, w, h):
    """Las Vegas: a lap-time trace falling to the best lap, on navy.

    The plot fills the band. Its top-right corner is deliberately plain navy
    for the data callout, and the only scene label sits top-left, in the
    clear sky above the trace's first point.
    """
    add(rect(0, 0, SCENE_W, SCENE_H, NAVY))
    for i in range(14):
        bh = 6 + (i * 7) % 15
        add(rect(7 + i * 7.0, 51 - bh, 2.4, bh, '#33436d'))
    pts = ((7, 16), (21, 20), (35, 17), (49, 25), (63, 22),
           (77, 31), (91, 36), (104, 43))
    add(path('M ' + ' L '.join(f'{a} {b}' for a, b in pts),
             stroke='#d94f4f', sw=2.0))
    for a, b in pts:
        add(circle(a, b, 1.4, '#e8a5a5'))
    scene_label('LAP TIMES', x + 7, y + 3.0, 78, 8.0, 6.4,
                bold=True, fill='#8f9cbe')


FEATURE_SCENES = {
    'kyiv': sc_kyiv, 'bridge': sc_bridge, 'flags': sc_flags, 'riyadh': sc_riyadh,
    'scales': sc_scales, 'deal': sc_deal, 'jet': sc_jet, 'globe': sc_globe,
    'cricket': sc_cricket, 'chart': sc_chart,
}


def feature_scene(kind, x, y, w, h, region):
    SCENE_LABELS.clear()
    SCENE_PLATES.clear()
    scene_open(x, y, w, h)
    FEATURE_SCENES[kind](x, y, w, h)
    scene_close()
    for px, py, pw, ph, fill, rx, opacity in SCENE_PLATES:
        add(rect(px, py, pw, ph, fill, rx, opacity))
    for s, lx, ly, lw, lh, size, kw in SCENE_LABELS:
        block(s, lx, ly, lw, lh, size, region=region, **kw)
    SCENE_LABELS.clear()
    SCENE_PLATES.clear()


# --------------------------------------------------------------------------
# Sections (each appends its own fragments to PARTS)
# --------------------------------------------------------------------------
def masthead():
    track = 0.45
    block(MAST_LEFT, MARGIN, 1, 300, 9.5, 7.5, bold=True, region='mast-left',
          tracking=track)
    # Right-aligned by measurement: block() draws left-to-right from x.
    right_w = measure(MAST_RIGHT, 7.5, tracking=track)
    block(MAST_RIGHT, PAGE - MARGIN - right_w, 1, right_w, 9.5, 7.5,
          region='mast-right', tracking=track)
    block(MAST_DATE, MARGIN, 10.8, PAGE - 2 * MARGIN, 43, 34, minimum=34,
          bold=True, serif=True, center=True, region='mast-date')
    block(STRAPLINE, MARGIN, 55.5, PAGE - 2 * MARGIN, 13.5, 10.5,
          minimum=10, serif=True, italic=True, fill=RED, center=True,
          region='strapline')


def timeline_strip():
    """The day's seven dated beats on one linear 00:00-23:59 UTC axis.

    Each tick carries a bold time beside the axis and a muted caption on the
    far side, and the pair alternates sides tick by tick. Every caption box
    runs only as far as the next tick on its own side, so the five events
    crowded into the first six hours share the left end without colliding.
    """
    x0, w = MARGIN, PAGE - 2 * MARGIN
    add(rect(x0, TL_Y, w, TL_H, BAND))
    add(line(x0, TL_Y, x0 + w, TL_Y, NAVY, 0.7))
    add(line(x0, TL_Y + TL_H, x0 + w, TL_Y + TL_H, NAVY, 0.7))
    # Left-margin label, stacked over two lines clear of the first tick box.
    block('THE DAY', x0 + 3, TL_Y + 8.2, 30, 7.75, 6.2, bold=True,
          region='timeline')
    block('IN UTC', x0 + 3, TL_Y + 16.2, 30, 7.75, 6.2, bold=True,
          region='timeline')

    axis_y = TL_Y + TL_AXIS_DY
    add(line(TL_AXIS_X, axis_y, TL_AXIS_X + TL_AXIS_W, axis_y, NAVY, 0.7))
    # A short end-cap makes the axis read as a measured scale, not a rule.
    add(line(TL_AXIS_X + TL_AXIS_W, axis_y - 2.4,
             TL_AXIS_X + TL_AXIS_W, axis_y + 2.4, NAVY, 0.7))

    marks = [(TL_AXIS_X + (hh * 60 + mm) / 1439 * TL_AXIS_W,
              f'{hh:02d}:{mm:02d}', caption, side)
             for hh, mm, caption, side in TICKS]

    # A tick's label block is stacked either above or below the axis, with
    # the bold clock nearest the line and the muted caption beyond it; the
    # side alternates tick by tick. Each block runs rightwards from its dot
    # and stops short of the next tick on its own side, so the five events
    # crowded into the first six hours cannot collide.
    for i, (px, clock, caption, side) in enumerate(marks):
        add(circle(px, axis_y, 1.7, NAVY))
        add(circle(px, axis_y, 2.9, NAVY, opacity=0.13))
        peers = sorted(m[0] for m in marks if m[3] == side)
        k = peers.index(px)
        stop = (TL_AXIS_X + TL_AXIS_W if k == len(peers) - 1
                else peers[k + 1] - 2.5)
        left = px + 1.6
        cw = stop - left
        if side == 'up':
            block(caption, left, TL_Y + 0.9, cw, 6.6, 5.2, fill=MUTED,
                  region='timeline')
            block(clock, left, TL_Y + 7.5, cw, 7.0, 5.6, bold=True,
                  region='timeline')
        else:
            block(clock, left, axis_y + 1.4, cw, 7.0, 5.6, bold=True,
                  region='timeline')
            block(caption, left, axis_y + 8.9, cw, 6.6, 5.2, fill=MUTED,
                  region='timeline')


def stat_band():
    add(rect(MARGIN, 111.5, PAGE - 2 * MARGIN, 28, BAND, 4))
    cell_w = (PAGE - 2 * MARGIN) / len(STATS)
    for i, (value, caption) in enumerate(STATS):
        x = MARGIN + i * cell_w
        if i:
            add(line(x, 115, x, 136, '#d6cdb8', 0.8))
        block(value, x + 4, 111.8, cell_w - 8, 18.5, 15.5, minimum=13,
              bold=True, fill=RED, center=True, region='stats')
        block(caption, x + 5, 130.6, cell_w - 10, 8.2, 6.9, minimum=6.2,
              center=True, fill=NAVY, region='stats')


def region_pills():
    gap = 8
    w = (PAGE - 2 * MARGIN - gap * (len(REGION_PILLS) - 1)) / len(REGION_PILLS)
    for i, (label, color) in enumerate(REGION_PILLS):
        pill(label, MARGIN + i * (w + gap), 141.5, w, 13.5, color, 7.2,
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
        # Caption + provenance chips on the seam. A lead may carry one pill
        # or a pair (its confirmed fact plus the claim it is reporting).
        pill(lead['chip'], x + 8, y + 57, 104, 14, NAVY, 7.5, r)
        prov = lead['prov']
        if isinstance(prov, str):
            prov = ((prov, PROV_COLORS[prov], 88, 7.5),)
        else:
            prov = tuple((label, color, max(30, 8 + measure(label, 7.2, True)),
                          7.2) for label, color in prov)
        px = x + 118
        for label, color, pw, psize in prov:
            pill(label, px, y + 57, pw, 14, color, psize, r)
            px += pw + 4
        # Place line, numbered
        number(i + 1, x + 17, y + 83, r)
        block(lead['place'], x + 30, y + 78, 282, 10, 8, bold=True,
              region=r)
        # Kicker, headline, body, sources
        pill(lead['kicker'], x + 10, y + 90, 172, 14, RED, 8, r)
        block(lead['head'], x + 10, y + 108, CARD_W - 20, 35, 14,
              minimum=12.5, bold=True, serif=True, lines=2, region=r)
        block(lead['body'], x + 10, y + 145, CARD_W - 20, 21, 8.25,
              minimum=7.5, lines=2, fill=lead.get('body_fill', NAVY),
              region=r)
        block('(' + lead['source'] + ')', x + 10, y + 166,
              CARD_W - 20, 9.5, 7.2, italic=True, fill=MUTED, region=r)


def feature_cards():
    """Ten feature cards, five across and two down, filling y=341..613.

    The section is clipped to y >= 341 so that the 2x render's resampling
    halo on the top card edge cannot bleed into the finished sections above.
    """
    add('<clipPath id="clip-features"><rect x="0" y="341" width="1024" '
        'height="683"/></clipPath>')
    add('<g clip-path="url(#clip-features)">')
    for i, feat in enumerate(FEATURES):
        x = FEAT_XS[i % 5]
        y = FEAT_YS[i // 5]
        r = f'feat-{feat["n"]}'
        card(x, y, FEAT_W, FEAT_H)
        # Scene band, clipped to the card's rounded top corners
        add(f'<clipPath id="clip-{r}"><rect x="{x:g}" y="{y:g}" '
            f'width="{FEAT_W:g}" height="{FEAT_SCENE_H}" rx="6"/></clipPath>')
        add(f'<g clip-path="url(#clip-{r})">')
        feature_scene(feat['scene'], x, y, FEAT_W, FEAT_SCENE_H, r)
        add('</g>')
        # Big data callout, top-right of the scene band. Width follows the
        # measured figure so the number is never clipped.
        data = FEATURE_CALLOUTS.get(feat['n'])
        if data:
            value, caption, color = data
            cw = max(measure(value, 10.5, True, serif=True),
                     measure(caption, 5.0, True),
                     measure(value, 7.5, True, serif=True)) + 17
            callout(x + FEAT_W - 7 - cw, y + 5, cw, 22,
                    value, caption, color)
        # Kicker pill straddling the scene seam: number, then the label.
        # A CLAIM is called out in red, with a paler numeral for contrast.
        kick_w = 62 + measure(feat['kicker'], 7, True)
        px, py = x + 7, y + FEAT_SCENE_H - 9
        claimed = feat['prov'] == 'CLAIM'
        add(rect(px, py, kick_w, 13, RED if claimed else NAVY, 4))
        block(feat['n'], px + 4, py + 3.2, 13, 9, 7, bold=True,
              fill='#f2d98c' if claimed else GOLD, region=r)
        block(feat['kicker'], px + 17, py + 3.2, kick_w - 21, 9, 7,
              bold=True, fill=WHITE, region=r)
        # Provenance chip under the kicker
        prov_w = 12 + measure(feat['prov'], 6.8, True)
        pill(feat['prov'], x + 7, py + 16, prov_w, 12,
             PROV_COLORS[feat['prov']], 6.8, r)
        # Headline, body, sources
        block(feat['head'], x + 8, y + 68, FEAT_W - 16, 30, 11.5,
              minimum=9.5, bold=True, serif=True, lines=2, region=r)
        block(feat['body'], x + 8, y + 98, FEAT_W - 16, 21, 8.5,
              minimum=7.5, lines=2, region=r)
        block('(' + feat['source'] + ')', x + 8, y + 120,
              FEAT_W - 16, 9.5, 7.2, italic=True, fill=MUTED, region=r)
    add('</g>')


# Provenance key, set as one line of fine print directly under DATE CHECK.
CHECKED_LABEL = 'HOW WE CHECKED'
CHECKED_TEXT = (
    'CONFIRMED = 2+ official sources · OFFICIAL = on the record officials · '
    'REPORTED = one major outlet · CLAIM = unverified party claim. '
    'Corrections: none; figures verified against agency copy '
    '(USGS 108 km depth, UKMTO distances as reported).')


def how_we_checked():
    """One muted line of fine print in the DATE CHECK band's lower padding.

    The band itself is owned by map_briefs; this only inks text inside the
    space it leaves, so nothing has to move. block(lines=1) guarantees a
    single row: if the copy ever outgrows the width it is ellipsised rather
    than wrapped, which is what keeps this a one-line strip.
    """
    y, size = 961.4, 6.2
    label_w = measure(CHECKED_LABEL, size, True)
    block(CHECKED_LABEL, 112, y, label_w + 0.5, 7.9, size, bold=True,
          fill=NAVY, region='checked')
    block(CHECKED_TEXT, 112 + label_w + 6, y, 884 - label_w - 6, 7.9, size,
          minimum=5.0, lines=1, fill=MUTED, region='checked')


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
    timeline_strip()
    stat_band()
    region_pills()
    lead_cards()

    # --- later phases insert more sections here ---
    feature_cards()

    import map_briefs
    map_briefs.wire()
    how_we_checked()

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
