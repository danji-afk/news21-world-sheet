#!/usr/bin/env python3
"""The world map and the 23 secondary briefs for Saturday 21 November 2026.

`render.py` owns the page engine: measurement, the text-placement system and
every primitive that draws ink. This module owns one section of the sheet —
the schematic world map with its numbered pins, the Wellington inset, the
legend, the two-column brief list, the date-check strip and the footer — and
appends it to that engine with a single call:

    import map_briefs
    map_briefs.wire()

`wire()` is written to be called from inside `render.build()` just before the
closing tags, so the whole page is still assembled and verified by one engine.
It imports `render` lazily so that this file can be imported, and its own
geometry self-tested, before the renderer has grown the call.

Nothing here is random or networked. The pin label offsets are a solved
constant table; `check_pins()` re-proves the two properties they were solved
for (labels inside the panel, no two labels overlapping) on every run.
"""
import math

# --------------------------------------------------------------------------
# Briefs: story number, place, one-line story, source
# --------------------------------------------------------------------------
BRIEFS = [
    (14, 'COPENHAGEN', "Denmark expels Russia's defence attaché over a "
                       "thwarted killing plot.", 'AP, BBC'),
    (15, 'EU · COP31', 'EU warns the draft risks turning COP31 into a '
                       '"fossil summit".', 'AFP, Euronews'),
    (16, 'PANAMA', 'Minister threatens to block any COP31 text without '
                   'fossil-fuel language.', 'UN News'),
    (17, 'JAKARTA', "Indonesia's PLN signs six clean-power purchase "
                    'agreements.', 'Antara'),
    (18, 'SAUDI ARABIA', 'Houthis threaten Jeddah and all Saudi Red Sea '
                         'ports.', 'Al Jazeera'),
    (19, 'WASHINGTON', 'Vance says the February Iran strikes were "Trump\'s '
                       'call".', 'Reuters'),
    (20, 'GULF OF FINLAND', 'Cargo ship ablaze after a drone strike; crew '
                            'evacuates.', 'Reuters'),
    (21, 'COLOMBIA', '"El Chapo Isidro" captured; 11 die in the operation.',
     'AP'),
    (22, 'GAZA', 'Strike on a food truck kills three; aid convoys pause.',
     'Al Jazeera'),
    (23, 'BRUSSELS', 'EU and Indonesia seal a long-negotiated trade deal.',
     'EU Council'),
    (24, 'JEFFERSON CITY', "Missouri judge approves Bayer's $7.25bn Roundup "
                           'settlement.', 'AFP, AP'),
    (25, 'ST. LOUIS', 'Jury hands Bayer a defence win in a weedkiller cancer '
                      'trial.', 'AP'),
    (26, 'SEJONG', 'Five cars of a freight train derail; no one is hurt.',
     'Yonhap'),
    (27, 'TAIPEI', 'Legislative Yuan passes the NT$20,000 universal cash '
                   'payout.', 'Taipei Times'),
    (28, 'NEW DELHI', 'Pakistan minister joins an SCO forum — first visit '
                      'since 2023.', 'Dawn'),
    (29, 'ODISHA', "Cyclone Akvan's remnants move inland; rain alerts "
                   'continue.', 'IMD'),
    (30, 'THE HAGUE', "Rights groups urge sanctions after the ICJ's Rohingya "
                      'genocide finding.', 'AP'),
    (31, 'PYONGYANG', 'Kim tours teaching-aid factory construction sites.',
     'KCNA'),
    (32, 'TOKYO', "Takaichi's approval holds above 70% for a third month.",
     'Nikkei'),
    (33, 'BANGKOK', 'Flood alert along the Chao Phraya and Noi rivers.',
     'The Nation'),
    (34, 'PORT LOUIS', 'AU roundtable on African risk financing and the risk '
                       'premium.', 'Al Jazeera'),
    (35, 'MELBOURNE', 'One dead, three teens arrested after city stabbings.',
     'ABC'),
    (36, 'SAN FRANCISCO', 'S&P and Nasdaq slide further as the AI rout '
                          'deepens.', 'Reuters'),
]

# --------------------------------------------------------------------------
# Map panel geometry
# --------------------------------------------------------------------------
MAP_X, MAP_Y = 14, 638
MAP_W, MAP_H = 300, 190
LABEL_R = 6.5
LAT_TOP, LAT_BOTTOM = 85, -60

# Latitude lines drawn faintly across the panel (lat, label)
LATITUDES = [60, 40, 20, 0, -20, -40]


def project(lon, lat):
    """Equirectangular: lon -180..180 across the panel, lat 85..-60 down it."""
    return ((lon + 180) / 360 * MAP_W,
            (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * MAP_H)


# --------------------------------------------------------------------------
# Pins: story number, lon, lat, label_dx, label_dy
#
# The offsets were solved so every 13-pixel label circle sits wholly inside
# the panel and no two labels overlap, while each leader stays short enough
# to read as a leader rather than a stray mark. Pins 19/25 and 23/30 share
# a true point by design (two St Louis stories, two Hague stories) and their
# labels are pulled to opposite sides.
# --------------------------------------------------------------------------
PINS = [
    (1, 30.7, 36.9, 12.6, 5.1),        # Antalya
    (2, 46.7, 24.5, -4.8, 14.1),       # Riyadh
    (3, -76.2, -11.5, 5.9, -15.3),     # Junín, Peru
    (4, 30.5, 50.4, 16.0, 8.5),        # Kyiv
    (5, 33.4, 47.6, -8.2, -17.9),      # Kryvyi Rih
    (6, 51.4, 35.7, 13.6, -0.5),       # Tehran
    (7, 56.3, 26.6, -14.7, 3.6),       # Strait of Hormuz
    (8, -77.0, 38.9, 9.4, -13.4),      # Washington
    (9, 116.4, 39.9, 16.7, 8.2),       # Beijing
    (10, 125.6, 7.1, -19.3, -3.4),     # Davao
    (11, 149.1, -35.3, 8.9, -10.3),    # Canberra
    (13, -115.1, 36.2, -2.5, 14.8),    # Las Vegas
    (14, 12.6, 55.7, -16.0, -4.3),     # Copenhagen
    (15, 4.4, 50.8, 8.0, 16.1),        # Brussels
    (16, -79.5, 9.0, -16.0, 11.0),     # Panama City
    (17, 106.8, -6.2, 6.8, -11.5),     # Jakarta
    (18, 44.2, 15.3, 5.7, 14.3),       # Sanaa
    (19, -90.2, 38.6, -9.5, 13.6),     # St Louis (first label)
    (20, 25.0, 60.2, 15.6, -8.9),      # Gulf of Finland
    (21, -74.1, 4.7, -11.0, 16.2),     # Colombia
    (22, 34.5, 31.5, -0.8, -13.0),     # Gaza
    (23, 4.3, 52.1, 14.3, 5.0),        # The Hague (first label)
    (24, -92.2, 38.6, -11.2, -12.0),   # Jefferson City
    (25, -90.2, 38.6, 5.5, -17.3),     # St Louis (second label)
    (26, 127.3, 36.5, 9.7, 17.1),      # Sejong
    (27, 121.5, 25.0, -7.1, -10.9),    # Taipei
    (28, 77.2, 28.6, 13.7, -6.2),      # New Delhi
    (29, 85.8, 20.3, -10.5, 12.8),     # Odisha
    (30, 4.3, 52.1, 1.5, -17.8),       # The Hague (second label)
    (31, 125.8, 39.0, -3.5, 19.0),     # Pyongyang
    (32, 139.7, 35.7, -10.6, -8.3),    # Tokyo
    (33, 100.5, 13.7, 3.2, -14.5),     # Bangkok
    (34, 57.5, -20.2, -3.1, 16.1),     # Port Louis
    (35, 144.9, -37.8, -11.6, -14.1),  # Melbourne
    (36, -122.4, 37.8, 19.2, -0.6),    # San Francisco
]

# --------------------------------------------------------------------------
# Continents: simplified outlines as (lon, lat) vertices. Coarse on purpose:
# this is a locator diagram, not an atlas, so the shapes need to be readable
# at 300 x 190 rather than exact.
# --------------------------------------------------------------------------
CONTINENTS = [
    # North America: Alaska, the Pacific coast, Baja, Central America, the
    # Gulf, the Atlantic seaboard, the St Lawrence and the Arctic coast.
    [(-168, 66), (-164, 58), (-155, 57), (-145, 60), (-134, 56), (-125, 48),
     (-122, 37), (-114, 29), (-105, 20), (-95, 15), (-87, 13), (-80, 8),
     (-79, 10), (-84, 16), (-88, 21), (-94, 18), (-97, 26), (-89, 29),
     (-81, 25), (-80, 32), (-74, 40), (-67, 45), (-56, 50), (-64, 58),
     (-78, 62), (-95, 70), (-125, 70), (-150, 71)],
    # South America: Caribbean coast, Brazil's bulge, the Plata, Patagonia,
    # the Andes and the Pacific coast back to the isthmus.
    [(-78, 9), (-72, 12), (-62, 11), (-52, 5), (-44, -2), (-35, -8),
     (-39, -15), (-41, -23), (-48, -25), (-54, -34), (-58, -38), (-63, -42),
     (-68, -50), (-71, -54), (-74, -52), (-72, -42), (-70, -30), (-70, -18),
     (-76, -14), (-81, -4), (-80, 0), (-78, 4)],
    # Africa: the Atlantic bulge, the Gulf of Guinea, the Cape, the Horn and
    # the Red Sea coast.
    [(-17, 15), (-16, 21), (-10, 29), (-6, 36), (0, 36), (10, 37),
     (11, 33), (20, 32), (32, 31), (35, 28), (43, 12), (51, 12), (48, 5),
     (42, -1), (40, -10), (35, -20), (33, -26), (28, -33), (20, -35),
     (18, -34), (15, -27), (12, -17), (9, -1), (9, 4), (3, 6), (-8, 4),
     (-13, 8), (-16, 12)],
    # Europe: Iberia, France, the Low Countries, Jutland, Scandinavia, the
    # Baltic, the Mediterranean shore and the Black Sea.
    [(-9, 37), (-9, 43), (-1, 43), (-2, 48), (2, 51), (4, 53), (8, 54),
     (10, 57), (7, 58), (5, 62), (14, 68), (22, 70), (30, 70), (40, 68),
     (40, 50), (38, 46), (35, 44), (30, 45), (28, 41), (26, 40), (23, 38),
     (19, 40), (16, 38), (14, 40), (12, 44), (8, 44), (3, 43), (0, 39),
     (-6, 36)],
    # Asia: the Siberian coast, the Pacific rim, the Gulf, India, Arabia,
    # Anatolia and the Urals.
    [(40, 68), (62, 73), (85, 77), (110, 77), (135, 75), (160, 72),
     (180, 70), (178, 65), (165, 60), (150, 59), (142, 52), (134, 46),
     (128, 41), (126, 37), (122, 31), (120, 24), (111, 20), (106, 11),
     (103, 3), (100, 7), (98, 13), (92, 21), (80, 10), (71, 20),
     (65, 25), (57, 24), (52, 14), (44, 14), (36, 29), (40, 50)],
    # Greenland
    [(-45, 60), (-53, 64), (-58, 69), (-62, 75), (-55, 80), (-42, 83),
     (-28, 81), (-20, 76), (-23, 71), (-30, 67), (-38, 64)],
    # Australia
    [(114, -22), (113, -27), (116, -35), (124, -33), (132, -32), (140, -38),
     (148, -38), (153, -31), (153, -26), (147, -19), (142, -11), (136, -12),
     (131, -12), (125, -15), (118, -20)],
    # Madagascar
    [(49, -12), (50, -17), (47, -25), (44, -25), (43, -20), (44, -15),
     (46, -12)],
    # Japan: Honshu, Kyushu and the southern tip of Hokkaido in one arc
    [(130, 31), (132, 33), (135, 34), (137, 37), (141, 41), (145, 44),
     (143, 45), (140, 40), (136, 36), (133, 33), (131, 32)],
    # New Zealand
    [(173, -35), (175, -37), (178, -38), (176, -41), (173, -41),
     (171, -44), (167, -46), (168, -44), (172, -41), (173, -38),
     (172, -36)],
    # Maritime Southeast Asia: Sumatra, Java, the Lesser Sundas and Sulawesi
    [(95, 6), (100, 2), (104, -1), (108, -5), (113, -7), (118, -8),
     (124, -8), (130, -7), (135, -4), (133, 0), (128, 1), (123, 1),
     (119, 3), (114, 2), (110, 1), (106, 2), (102, 4), (98, 5)],
]

# Copy ---------------------------------------------------------------------
MAP_HEAD = 'WHERE IT HAPPENED'
BRIEF_HEAD = 'ALSO ON SATURDAY 21 NOVEMBER — 23 MORE STORIES'
LEGEND = ['Numbered pins: the 23 brief stories · schematic map',
          'Red circles: story numbers on this page']
INSET_PLACE = 'WELLINGTON'
INSET_STORY = 'Cricket: Rahul 124* · India 344/2'
DATE_PILL = 'DATE CHECK'
DATE_TEXT = ('These happened earlier but were carried into Saturday: the Kryvyi '
             'Rih strike (Friday evening) · Zelensky\'s interview was given '
             'Friday · Peru\'s quake was 19:09 Friday local · Trump\'s '
             'briefing, China\'s remarks to Japan, the Copenhagen expulsion, '
             'Cyclone Akvan\'s landfall and Russell\'s session were all Friday.')
FOOTER = ('Every story happened, or was first reported, on Saturday 21 November '
          '2026 in some time zone. Claims are attributed, not stated as fact. '
          'CONFIRMED = 2+ outlets · OFFICIAL = on record · CLAIM = one side. · '
          'Original drawings. 2026-11-21')

# Brief list geometry ------------------------------------------------------
BRIEF_COLS = ((330, 12), (674, 11))   # (x, rows) for the two columns
BRIEF_TOP = 638
BRIEF_ROW_H = 23.75
BRIEF_W = 316                          # column text width
BRIEF_PAD = 6

# Text sizes inside a brief row: place, story, source.
PLACE_SIZE, STORY_SIZE, SOURCE_SIZE = 7.9, 7.4, 6.9


# --------------------------------------------------------------------------
# Geometry self-test: pure python, no rendering
# --------------------------------------------------------------------------
def label_box(n, x, y):
    """The box render.number() reserves for a numeral in a label circle.

    render.number() calls block(str(n), x - r, y - 0.65 * size, 2 * r,
    1.25 * size, ...), so this is that rectangle, in panel coordinates.
    """
    size = 7 if n < 10 else 6.5
    return (x - LABEL_R, y - 0.65 * size, x + LABEL_R, y - 0.65 * size + 1.25 * size)


def _overlap(a, b, gap=0.0):
    return (a[0] < b[2] - gap and a[2] > b[0] + gap and
            a[1] < b[3] - gap and a[3] > b[1] + gap)


def check_pins():
    """Prove the two properties the offset table was solved for.

    Returns the number of pins checked. Raises AssertionError on any breach:
    a label outside the panel, or two labels whose circles touch.
    """
    boxes = {}
    for n, lon, lat, dx, dy in PINS:
        px, py = project(lon, lat)
        lx, ly = px + dx, py + dy
        box = label_box(n, lx, ly)
        assert (box[0] >= 0 and box[1] >= 0 and
                box[2] <= MAP_W and box[3] <= MAP_H), (
            f'pin {n}: label box {box} leaves the {MAP_W}x{MAP_H} panel')
        assert math.hypot(dx, dy) <= 23.0, (
            f'pin {n}: leader {math.hypot(dx, dy):.1f}px is too long to read')
        boxes[n] = box

    names = sorted(boxes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not _overlap(boxes[a], boxes[b]), (
                f'labels {a} and {b} overlap: {boxes[a]} vs {boxes[b]}')

    # The two deliberately shared coordinates must be well separated.
    for a, b in ((19, 25), (23, 30)):
        pa, pb = PINS[a - 14][3:], PINS[b - 14][3:]
        d = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
        assert d >= 13.0, f'labels {a}/{b} share a point but sit {d:.1f}px apart'

    assert len(PINS) == 35, f'expected 35 pins, found {len(PINS)}'
    assert len(BRIEFS) == 23, f'expected 23 briefs, found {len(BRIEFS)}'
    assert sorted(n for n, *_ in PINS) == sorted([n for n in range(1, 37)
                                                  if n != 12]), \
        'pins must cover stories 1-36 except the Wellington inset (12)'
    return len(PINS)


# --------------------------------------------------------------------------
# Drawing helpers (all delegated to the render engine)
# --------------------------------------------------------------------------
def _smooth_path(pts):
    """A closed polygon through quadratic midpoint curves.

    Each vertex becomes a control point and each edge midpoint an on-curve
    anchor, which rounds every corner without moving the shape's overall
    position — the coastlines read as drawn rather than plotted.
    """
    n = len(pts)
    mids = [((pts[i][0] + pts[(i + 1) % n][0]) / 2,
             (pts[i][1] + pts[(i + 1) % n][1]) / 2) for i in range(n)]
    d = [f'M {mids[0][0]:.2f} {mids[0][1]:.2f}']
    for i in range(1, n + 1):
        cx, cy = pts[i % n]
        mx, my = mids[i % n]
        d.append(f'Q {cx:.2f} {cy:.2f} {mx:.2f} {my:.2f}')
    return ' '.join(d) + ' Z'


def _map_panel(render):
    """Navy panel, faint latitude lines, land in paper colour."""
    render.add(render.rect(MAP_X, MAP_Y, MAP_W, MAP_H, render.NAVY, 4))
    # A hairline inner keyline lifts the panel off the paper.
    render.add(render.rect(MAP_X + 0.5, MAP_Y + 0.5, MAP_W - 1, MAP_H - 1,
                           'none', 4, stroke='#3a4560', sw=0.5))

    for lat in LATITUDES:
        y = MAP_Y + project(0, lat)[1]
        render.add(render.line(MAP_X + 6, y, MAP_X + MAP_W - 6, y,
                               '#ffffff', 0.4, extra='opacity=".13"'))

    for poly in CONTINENTS:
        pts = [project(lon, lat) for lon, lat in poly]
        pts = [(MAP_X + x, MAP_Y + y) for x, y in pts]
        render.add(render.path(_smooth_path(pts), fill=render.PAPER,
                               stroke=render.NAVY, sw=0.45,
                               extra='stroke-linejoin="round"'))


def _pins(render):
    """Leader, true-point dot and numbered disc for every brief story."""
    for n, lon, lat, dx, dy in PINS:
        px, py = project(lon, lat)
        ax, ay = MAP_X + px, MAP_Y + py
        lx, ly = ax + dx, ay + dy
        render.add(render.line(ax, ay, lx, ly, render.RED, 0.7,
                               extra='opacity=".75"'))
        render.add(render.circle(ax, ay, 1.5, render.RED))
        render.add(render.circle(ax, ay, 2.6, render.RED, opacity=0.28))
        render.number(n, lx, ly, 'map', LABEL_R)


def _inset(render):
    """Wellington: story 12 has no pin, so it gets a disc under the panel."""
    cx = MAP_X + 50
    cy = MAP_Y + MAP_H + 52
    render.add(render.circle(cx, cy, 44, render.NAVY))
    render.number(12, cx, cy - 15, 'map-inset', 9)
    render.block(INSET_PLACE, cx - 40, cy - 1, 80, 10, 7.5, bold=True,
                 fill=render.WHITE, center=True, region='space-inset')
    render.block(INSET_STORY, cx - 40, cy + 10, 80, 11, 5.25, minimum=4.5,
                 fill=render.WHITE, center=True, region='space-inset')


def _legend(render):
    """Two grey key lines, set beside the inset so both fit under the panel."""
    x = MAP_X + 100
    w = MAP_W - 102
    y = MAP_Y + MAP_H + 14
    for i, line in enumerate(LEGEND):
        render.add(render.circle(x + 2, y + 4.4 + i * 11, 2.2,
                                 render.RED if i == 0 else render.NAVY))
        render.block(line, x + 8, y + i * 11, w - 8, 9.5, 6.5,
                     minimum=5.5, fill=render.MUTED, region='legend')


# --------------------------------------------------------------------------
# The rich brief row: place (bold red), story (navy), source (italic muted)
# --------------------------------------------------------------------------
def _row_runs(place, story, source):
    """The row as a flat list of (text, size, bold, italic, fill) words.

    Colour changes mid-line, so the row cannot go through render.block();
    it is laid out here as word runs and then reserved in render.PLACED as
    one box, which is what render.verify() checks at the end of the build.
    """
    runs = [(w, PLACE_SIZE, True, False) for w in place.split()]
    runs += [(w, STORY_SIZE, False, False) for w in story.split()]
    runs.append(('(' + source + ')', SOURCE_SIZE, False, True))
    return runs


def _row_lines(render, place, story, source, width):
    """Greedy word wrap across mixed styles, measured with render.measure."""
    lines, cur = [], []
    used = 0.0
    for word, size, bold, italic in _row_runs(place, story, source):
        w = render.measure(word, size, bold, italic=italic)
        gap = render.measure(' ', size, bold) if cur else 0.0
        if cur and used + gap + w > width:
            lines.append((cur, used))
            cur, used = [(word, size, bold, italic)], w
        else:
            cur.append((word, size, bold, italic))
            used += gap + w
    if cur:
        lines.append((cur, used))
    return lines


def _brief_row(render, n, place, story, source, x, y):
    """One alternating strip plus its rich text, reserved as a single box."""
    h = BRIEF_ROW_H - 1.5
    if n % 2 == 0:
        render.add(render.rect(x, y, BRIEF_W, h, render.WHITE, 2))
    else:
        render.add(render.rect(x, y, BRIEF_W, h, '#eee9df', 2))

    lines = _row_lines(render, place, story, source, BRIEF_W - 2 * BRIEF_PAD)
    assert 1 <= len(lines) <= 2, (
        f'brief {n} wraps to {len(lines)} lines at {BRIEF_W}px: {place!r}')
    for _, used in lines:
        assert used <= BRIEF_W - 2 * BRIEF_PAD + 0.01, (
            f'brief {n} line overflows: {used:.1f}px')

    box = (x, y, x + BRIEF_W, y + h)
    render.PLACED.append({'region': 'briefs', 'box': box,
                          'text': f'{place} {story} ({source})',
                          'size': STORY_SIZE, 'lines': len(lines)})
    for old in render.PLACED[:-1]:
        assert not render.intersects(box, old['box']), (
            f'brief {n} collides with a {old["region"]} box')

    tx = x + BRIEF_PAD
    for i, (line, _) in enumerate(lines):
        base = y + 8.6 + i * 8.2
        cursor = tx
        for j, (word, size, bold, italic) in enumerate(line):
            if j:
                cursor += render.measure(' ', size, bold)
            if bold:
                fill = render.RED
            elif italic:
                fill = render.MUTED
            else:
                fill = render.NAVY
            render.add(render.text_node(word, cursor, base, size, bold=bold,
                                        italic=italic, fill=fill))
            cursor += render.measure(word, size, bold, italic=italic)


def _briefs(render):
    render.block(BRIEF_HEAD, 330, 617, 660, 15, 12, minimum=10.5, bold=True,
                 region='briefs-head')
    for ci, (x, rows) in enumerate(BRIEF_COLS):
        for r in range(rows):
            idx = r if ci == 0 else 12 + r
            n, place, story, source = BRIEFS[idx]
            _brief_row(render, n, place, story, source, x,
                       BRIEF_TOP + r * BRIEF_ROW_H)


# --------------------------------------------------------------------------
# Date check and footer
# --------------------------------------------------------------------------
def _date_check(render):
    top, h = 933, 37
    render.add(render.rect(14, top, 996, h, '#eae2d3', 3))
    render.pill(DATE_PILL, 24, top + 9, 76, 15, render.RED, 7.5, 'date')
    render.block(DATE_TEXT, 112, top + 5, 884, 27, 9, minimum=8, lines=2,
                 region='date')


def _footer(render):
    y = 984
    render.add(render.line(14, y - 8, 1010, y - 8, render.NAVY, 0.7))
    w = render.measure(FOOTER, 7.5)
    render.block(FOOTER, (render.PAGE - w) / 2, y, w, 9.5, 7.5,
                 fill=render.MUTED, center=True, region='footer')


# --------------------------------------------------------------------------
# The one entry point render.py will call
# --------------------------------------------------------------------------
def wire(render_module=None):
    """Append the map, briefs, date check and footer to the page.

    Imports the sibling renderer lazily: this module must be importable, and
    self-testable, before render.py grows its `map_briefs.wire()` call.
    """
    import sys
    render = render_module or (sys.modules['__main__'] if hasattr(sys.modules.get('__main__'), 'block') else sys.modules['render'])

    check_pins()

    render.block(MAP_HEAD, MAP_X, MAP_Y - 18, MAP_W, 14, 12, minimum=10.5,
                 bold=True, region='map-head')
    _map_panel(render)
    _pins(render)
    _inset(render)
    _legend(render)
    _briefs(render)
    _date_check(render)
    _footer(render)


# --------------------------------------------------------------------------
# Self-test: `python3 map_briefs.py`
# --------------------------------------------------------------------------
def _self_test():
    """Three checks, one line each. Never writes entry.png."""
    ok = True

    try:
        count = check_pins()
        print(f'pins ok: {count} labels inside {MAP_W}x{MAP_H}, '
              f'no two overlapping')
    except AssertionError as exc:
        ok = False
        print(f'pins FAILED: {exc}')

    try:
        import sys
        render = sys.modules['__main__'] if hasattr(sys.modules.get('__main__'), 'block') else sys.modules['render']
    except Exception as exc:                      # pragma: no cover
        print(f'render import FAILED: {exc}')
        return False

    # Build a scratch page, then wire into the same state render.build() left
    # behind. build() resets the engine, so this is exactly the position the
    # real call will occupy: after every earlier section, before the close.
    try:
        svg = render.build()
        before = len(render.PLACED)
        wire()
        added = len(render.PLACED) - before
        print(f'wire ok: {added} boxes added after render.build() '
              f'({len(render.PLACED)} total, {len(svg)} svg chars)')
    except Exception as exc:
        ok = False
        print(f'wire FAILED: {type(exc).__name__}: {exc}')

    # If render.build() has not yet grown its own wire() call, prove that
    # wiring then closing the page still satisfies render.verify().
    try:
        render.build()
        wire()
        render.add('</g></svg>')
        render.verify()
        print('verify ok: every reserved box on-page and non-overlapping '
              f'({len(render.PLACED)} boxes)')
    except Exception as exc:
        ok = False
        print(f'verify FAILED: {type(exc).__name__}: {exc}')

    return ok


if __name__ == '__main__':
    raise SystemExit(0 if _self_test() else 1)
