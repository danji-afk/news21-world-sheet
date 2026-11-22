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
# Briefs: story number, place, one-line story, source, provenance
#
# Stories 1-13 are the three leads and ten feature cards, which render.py
# draws; these 23 are the "also on Saturday" list behind the map pins.
# Two old briefs are gone: the Riyadh missiles brief, promoted to feature 07,
# and the Gaza food-truck brief, replaced by the drone strike on the aid van.
# The cartel capture is *not* a feature card on this page, so it stays.
#
# Provenance vocabulary matches render.py: CONFIRMED = 2+ outlets,
# OFFICIAL = on the record, REPORTED = one major outlet, CLAIM = one side.
# --------------------------------------------------------------------------
BRIEFS = [
    (14, 'GAZA CITY', 'Drone strike on a food-aid van kills three.',
     'Al Jazeera', 'REPORTED'),
    (15, 'HORMUZ', 'IRGC says it downed a US MQ-9; Washington does not '
                   'comment.', 'Reuters', 'CLAIM'),
    (16, 'TEHRAN', 'Iran recalls 168 killed in the US strike on a school.',
     'Anadolu', 'CLAIM'),
    (17, 'PARIS', '68,500 stolen or forged luxury goods; Christian Dior bags '
                  'most cited.', 'Reuters', 'OFFICIAL'),
    (18, 'ZURICH', 'Spain and the Netherlands win the ccTLD arbitration vote.',
     'NZZ', 'OFFICIAL'),
    (19, 'PAS-DE-CALAIS', 'Floods swamp 395 homes; 65 roads shut.',
     'Anadolu', 'REPORTED'),
    (20, 'NEWCASTLE', 'Anatra held to 2-2; Chelsea lose 1-4 to Leeds.',
     'Al Jazeera', 'REPORTED'),
    (21, 'DUBLIN', 'Ireland edge South Africa 20-17 in rugby.',
     'AFP', 'REPORTED'),
    (22, 'MONTEREY', 'More arrests in the Nobel FBI database breach.',
     'NEB', 'OFFICIAL'),
    (23, 'CLEVELAND', 'Harden passes Bryant on the NBA 30-point list.',
     'AF', 'REPORTED'),
    (24, 'MELBOURNE', 'Australia beat England by 3 wickets in the T20.',
     'AFP', 'REPORTED'),
    (25, 'DOHA', 'Cameroon lose their U17 World Cup opener 2-1.',
     'Africanews', 'REPORTED'),
    (26, 'MORONI', 'Assogene Sadio loses his presidential security job.',
     'Anadolu', 'OFFICIAL'),
    (27, 'ST ELIAS', 'Canada: 700,000 doses expiring shortly.',
     'Globe and Mail', 'REPORTED'),
    (28, 'DHAKA', 'Five more deaths with measles symptoms.',
     'Daily Star', 'REPORTED'),
    (29, 'NEW DELHI', 'Congress vows more protests against Modi.',
     'Deccan', 'OFFICIAL'),
    (30, 'SYDNEY', 'Pakistani minister calls climate change an "emergency" at '
                   'the SCG forum.', 'SCG', 'REPORTED'),
    (31, 'KATHMANDU', 'Shell infighting; 26 days of protests paralysed '
                      'business.', 'KTM Post', 'REPORTED'),
    (32, 'FUKUSHIMA', 'Snow strands travellers; ~700 homes lose power.',
     'Kyodo', 'OFFICIAL'),
    (33, 'BALI', 'Russian Interpol fugitive refused entry.',
     'Antara', 'OFFICIAL'),
    (34, 'SINALOA', '"El Chapo Isidro" captured; 11 die in the operation.',
     'AP', 'CONFIRMED'),
    (35, 'GULF OF FINLAND', 'Cargo ship ablaze after a drone strike; crew '
                            'evacuates.', 'AP, DW', 'CONFIRMED'),
    (36, 'BRUSSELS', 'EU and Indonesia seal a long-negotiated trade deal.',
     'EU Council', 'CONFIRMED'),
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
# to read as a leader rather than a stray mark. Two pairs share a true
# point by design — the Gulf lead and its brief (2/15), the Tehran feature
# and its brief (6/16) — and their labels are pulled to opposite sides.
#
# Every point was checked against the CONTINENTS outlines above (point in
# polygon), so no pin floats in open water.
# --------------------------------------------------------------------------
PINS = [
    (1, 30.7, 36.9, -7, 0),        # Antalya — COP31 lead
    (2, 56.3, 26.6, 7, -1),        # Strait of Hormuz — Gulf lead
    (3, -76.2, -11.5, 6, -4),      # Junín, Peru — quake lead
    (4, 30.5, 50.4, 0, 7),         # Kyiv
    (5, 33.4, 47.6, 1, -7),        # Kryvyi Rih
    (6, 51.4, 35.7, -7, -2),       # Tehran — feature
    (7, 46.7, 24.5, -2, 7),        # Riyadh — feature
    (8, -77.0, 38.9, 7, 1),        # Washington — feature
    (9, 116.4, 39.9, 5, -5),       # Beijing — feature
    (10, 125.6, 7.1, -1, -7),      # Davao — feature
    (11, 149.1, -35.3, -1, -7),    # Canberra — feature
    (13, -115.1, 36.2, 7, 0),      # Las Vegas — feature
    (14, 34.5, 31.5, -5, 5),       # Gaza
    (15, 56.3, 26.6, 3, 12),       # Hormuz (brief, second label)
    (16, 51.4, 35.7, 7, 1),        # Tehran (brief, second label)
    (17, 2.35, 48.86, 4, -6),      # Paris
    (18, 8.54, 47.38, -3, 10),     # Zurich
    (19, 2.4, 50.9, -5, 5),        # Pas-de-Calais
    (20, -1.61, 54.97, 5, -7),     # Newcastle
    (21, -6.26, 53.35, -5, -5),    # Dublin
    (22, -121.4, 36.5, -7, -1),    # Monterey
    (23, -81.7, 41.5, -7, 0),      # Cleveland
    (24, 144.9, -37.8, -7, 1),     # Melbourne
    (25, 51.5, 25.3, -6, -4),      # Doha
    (26, 43.3, -11.7, 5, -5),      # Moroni
    (27, -138.9, 60.5, -7, 0),     # St Elias, Alaska
    (28, 90.4, 23.8, -5, 5),       # Dhaka
    (29, 77.2, 28.6, 1, -7),       # New Delhi
    (30, 150.9, -33.8, 5, 5),      # Sydney (SCG forum)
    (31, 85.3, 27.7, 7, 0),        # Kathmandu
    (32, 140.5, 37.6, 1, -7),      # Fukushima
    (33, 115.2, -8.4, -7, -1),     # Bali
    (34, -107.4, 24.8, 5, -5),     # Sinaloa (Chapo Isidro)
    (35, 25.0, 60.2, 0, -7),       # Gulf of Finland
    (36, 4.4, 50.8, 7, 6),         # Brussels
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
    # Anatolia and the Levant: the Turkish plateau down the coast to Gaza,
    # so the Antalya lead, the Gaza brief and the Iranian pins all sit on land
    [(26.2, 40.4), (27.6, 37.2), (30.0, 36.1), (33.0, 35.9), (36.2, 36.0),
     (38.6, 37.0), (40.9, 37.7), (41.7, 41.4), (36.0, 42.2), (30.0, 41.2),
     (27.0, 41.2)],
    [(33.9, 31.0), (34.9, 31.3), (35.3, 32.4), (36.0, 33.5), (36.4, 36.2),
     (34.9, 36.5), (34.3, 33.0)],
    # Britain and Ireland: the Newcastle and Dublin briefs
    [(-5.2, 50.0), (-3.4, 50.3), (-0.9, 50.8), (1.4, 51.1), (1.7, 52.6),
     (0.2, 53.5), (-1.4, 54.9), (-2.2, 56.9), (-3.9, 58.6), (-5.6, 58.5),
     (-5.6, 56.0), (-4.9, 54.7), (-3.2, 54.1), (-3.3, 53.4), (-4.6, 53.3),
     (-4.2, 52.5), (-5.2, 51.8), (-3.3, 51.4)],
    [(-6.1, 52.1), (-6.1, 53.4), (-5.8, 54.5), (-6.4, 55.3), (-7.5, 55.4),
     (-8.7, 55.2), (-10.1, 54.2), (-10.5, 53.2), (-10.0, 52.1), (-9.5, 51.5),
     (-8.2, 51.6), (-6.7, 52.2)],
    # Japan: Honshu, Kyushu and the southern tip of Hokkaido in one arc.
    # Widened east of the old outline so the Fukushima brief has land.
    [(130.0, 31.2), (131.0, 31.5), (131.9, 33.6), (133.0, 34.4),
     (135.2, 35.5), (136.7, 37.3), (139.0, 38.0), (140.0, 39.5),
     (141.0, 41.2), (142.5, 43.3), (145.5, 44.4), (143.6, 45.6),
     (141.0, 42.0), (141.1, 40.5), (141.0, 38.4), (140.9, 37.0),
     (140.4, 35.7), (139.8, 34.9), (138.8, 34.6), (137.0, 34.6),
     (135.4, 33.6), (133.0, 33.4), (131.2, 33.0), (130.0, 32.0)],
    # Taiwan: a sliver, so the Taipei pin is not in open water
    [(119.9, 22.2), (121.0, 21.9), (121.9, 23.4), (121.9, 25.2),
     (121.4, 25.3), (120.2, 23.3)],
    # The Philippines: Luzon and Mindanao in one simplified silhouette
    [(120.3, 18.6), (122.4, 18.6), (124.2, 13.2), (126.6, 9.6),
     (126.2, 6.4), (124.2, 5.8), (121.9, 6.9), (119.8, 13.0), (119.6, 16.2)],
    # Comoros and Mauritius: the Moroni and Port Louis pins
    [(43.05, -11.4), (43.6, -11.5), (43.7, -12.1), (43.3, -12.5),
     (42.95, -12.0), (42.9, -11.6)],
    [(57.3, -19.9), (57.85, -19.95), (57.85, -20.4), (57.4, -20.55),
     (57.3, -20.15)],
    # New Zealand
    [(173, -35), (175, -37), (178, -38), (176, -41), (173, -41),
     (171, -44), (167, -46), (168, -44), (172, -41), (173, -38),
     (172, -36)],
    # Maritime Southeast Asia: Sumatra, Java, the Lesser Sundas and Sulawesi.
    # The southern edge is carried east past Java so the Bali brief has land.
    [(95, 6), (100, 2), (104, -1), (106.0, -6.3), (107.2, -7.5),
     (110.0, -7.4), (112.5, -6.8), (114.2, -7.4), (114.4, -9.1),
     (115.9, -9.1), (116.2, -8.0), (118, -8.0), (120, -8.2), (124, -8.2),
     (130, -7), (135, -4), (133, 0), (128, 1), (123, 1), (119, 3),
     (114, 2), (110, 1), (106, 2), (102, 4), (98, 5)],
]

# Copy ---------------------------------------------------------------------
MAP_HEAD = 'WHERE IT HAPPENED'
BRIEF_HEAD = 'ALSO ON SATURDAY 21 NOVEMBER — 23 MORE STORIES'
LEGEND = ['Numbered pins: the 23 brief stories · schematic map',
          'Red circles: story numbers on this page']
INSET_PLACE = 'WELLINGTON'
INSET_STORY = 'Cricket: Rahul 124* · India 344/2'
DATE_PILL = 'DATE CHECK'
# Date honesty, as two labelled lines: what happened on another day, and what
# had not happened yet when the sheet went to press. Each label is set bold
# on its own row; the body follows it on the same line.
DATE_ROWS = [
    ('Left out (other day):',
     'Taiex -17.5% weekly fall (biggest weekly points fall on record) is over '
     'Friday 20 November; Kryvyi Rih barrage and missiles in Poland were '
     'Friday; Chapo Isidro was detained Friday night, reported Saturday.'),
    ('Not yet (future):',
     'COP31 approval session Sun 06:00 GMT; Las Vegas Grand Prix Sunday; '
     'Nations Championship final next Sunday at Twickenham.'),
]
FOOTER = ('Every story happened, or was first reported, on Saturday 21 November '
          '2026 in some time zone. Claims are attributed, not stated as fact. '
          'CONFIRMED = 2+ outlets · OFFICIAL = on record · REPORTED = one '
          'outlet · CLAIM = one side · Original drawings. 2026-11-21')

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

    # The deliberately shared coordinates must be well separated.
    by_n = {p[0]: p for p in PINS}
    for a, b in ((2, 15), (6, 16)):
        pa, pb = by_n[a][3:], by_n[b][3:]
        d = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
        assert d >= 13.0, f'labels {a}/{b} share a point but sit {d:.1f}px apart'

    assert len(PINS) == 35, f'expected 35 pins, found {len(PINS)}'
    assert len(BRIEFS) == 23, f'expected 23 briefs, found {len(BRIEFS)}'
    assert sorted(n for n, *_ in PINS) == sorted([n for n in range(1, 37)
                                                  if n != 12]), \
        'pins must cover stories 1-36 except the Wellington inset (12)'
    assert sorted(n for n, *_ in BRIEFS) == [n for n in range(14, 37)], \
        'briefs must be exactly stories 14-36'
    # Every brief has a pin of the same number, and vice versa.
    assert {n for n, *_ in BRIEFS} == {n for n, *_ in PINS if n >= 14}, \
        'briefs and pins disagree about stories 14-36'
    # Each pin's true point must land on a landmass, not in open water.
    for n, lon, lat, *_ in PINS:
        assert any(_in_polygon(lon, lat, poly) for poly in CONTINENTS), (
            f'pin {n} at ({lon}, {lat}) is in open water')
    return len(PINS)


def _in_polygon(lon, lat, poly):
    """Ray-casting point-in-polygon test in lon/lat space (pure python)."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            x_at = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < x_at:
                inside = not inside
    return inside


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
# The rich brief row: number disc, place (bold red), story (navy),
# source and provenance (italic muted)
# --------------------------------------------------------------------------
NUMBER_X = 9            # disc centre, measured from the row's left edge
NUMBER_R = 5.2          # disc radius
TEXT_X = 18             # first word, measured from the row's left edge
TEXT_R = 4              # right pad, so a full line never touches the edge


def _row_runs(place, story, source, prov):
    """The row as a flat list of (text, size, bold, italic) words.

    Colour changes mid-line, so the row cannot go through render.block();
    it is laid out here as word runs and then reserved in render.PLACED as
    one box, which is what render.verify() checks at the end of the build.
    The provenance word closes the row, in the same muted italic as the
    source but bold, so it reads as a chip rather than more source text.
    """
    runs = [(w, PLACE_SIZE, True, False) for w in place.split()]
    runs += [(w, STORY_SIZE, False, False) for w in story.split()]
    runs.append(('(' + source + ' ·', SOURCE_SIZE, False, True))
    runs.append((prov + ')', SOURCE_SIZE, True, False))
    return runs


def _row_lines(render, place, story, source, prov, width):
    """Greedy word wrap across mixed styles, measured with render.measure."""
    lines, cur = [], []
    used = 0.0
    for word, size, bold, italic in _row_runs(place, story, source, prov):
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


def _brief_row(render, n, place, story, source, prov, x, y):
    """One alternating strip, its number disc, and its rich text.

    The strip and the disc are drawn; the text is laid out word by word and
    the whole row is reserved in render.PLACED as a single box, so the page
    engine's collision sweep sees one brief, not a dozen loose words.
    """
    h = BRIEF_ROW_H - 1.5
    if n % 2 == 0:
        render.add(render.rect(x, y, BRIEF_W, h, render.WHITE, 2))
    else:
        render.add(render.rect(x, y, BRIEF_W, h, '#eee9df', 2))

    # Number disc, vertically centred on the strip's first line.
    render.number(n, x + NUMBER_X, y + 9.2, 'briefs-num', NUMBER_R)

    width = BRIEF_W - TEXT_X - TEXT_R
    lines = _row_lines(render, place, story, source, prov, width)
    assert 1 <= len(lines) <= 2, (
        f'brief {n} wraps to {len(lines)} lines at {width}px: {place!r}')
    for _, used in lines:
        assert used <= width + 0.01, (
            f'brief {n} line overflows: {used:.1f}px of {width}px')

    # The reservation covers the *text* area, not the whole strip: the number
    # disc is reserved separately by render.number() a few lines above, and a
    # box starting at x would swallow that disc and collide with itself.
    box = (x + TEXT_X, y, x + BRIEF_W - TEXT_R, y + h)
    render.PLACED.append({'region': 'briefs', 'box': box,
                          'text': f'{place} {story} ({source} · {prov})',
                          'size': STORY_SIZE, 'lines': len(lines)})
    for old in render.PLACED[:-1]:
        assert not render.intersects(box, old['box']), (
            f'brief {n} collides with a {old["region"]} box')

    tx = x + TEXT_X
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
            n, place, story, source, prov = BRIEFS[idx]
            _brief_row(render, n, place, story, source, prov, x,
                       BRIEF_TOP + r * BRIEF_ROW_H)


# --------------------------------------------------------------------------
# Date check and footer
# --------------------------------------------------------------------------
def _date_check(render):
    """Two date-honesty rows, each a bold label and a run of muted facts.

    The label is set on its own baseline so the two rows read as a small
    table of contents for what the sheet left out and what it could not
    yet know. Both rows are measured before they are drawn: the body column
    starts where the widest label ends, so neither row can run under the
    other's label.
    """
    top, h = 933, 37
    render.add(render.rect(14, top, 996, h, '#eae2d3', 3))
    render.pill(DATE_PILL, 24, top + 9, 76, 15, render.RED, 7.5, 'date')

    label_size = 8.0
    label_w = max(render.measure(lbl, label_size, True)
                  for lbl, _ in DATE_ROWS)
    body_x = 112 + label_w + 4
    body_w = 996 - 8 - body_x

    # Both bodies share one size. The longest row decides it, so the two
    # rows stay typographically identical instead of the long one shrinking
    # on its own and leaving the short one a size larger.
    body_size = 8.0
    while (body_size > 7.2 and
           max(render.measure(b, body_size) for _, b in DATE_ROWS) > body_w):
        body_size = round(body_size - 0.1, 2)

    for i, (label, body) in enumerate(DATE_ROWS):
        y = top + 3.5 + i * 11.4
        render.block(label, 112, y, label_w + 0.5, 10, label_size,
                     bold=True, fill=render.RED, region='date-label')
        render.block(body, body_x, y, body_w, 10, body_size,
                     minimum=body_size, fill=render.MUTED,
                     region='date-body')


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
    """Two checks, one line each. Never writes entry.png."""
    ok = True

    try:
        count = check_pins()
        print(f'pins ok: {count} labels inside {MAP_W}x{MAP_H}, '
              f'no two overlapping')
    except AssertionError as exc:
        ok = False
        print(f'pins FAILED: {exc}')

    # render.build() now calls map_briefs.wire() itself, so building the page
    # exercises this section in its real position and then verifies every
    # reserved box. Calling wire() again here would place it twice.
    try:
        import render
        svg = render.build()
        render.verify()
        print(f'build ok: {len(render.PLACED)} boxes, none overlapping '
              f'({len(svg)} svg chars)')
    except Exception as exc:
        ok = False
        print(f'build FAILED: {type(exc).__name__}: {exc}')

    return ok


if __name__ == '__main__':
    raise SystemExit(0 if _self_test() else 1)
