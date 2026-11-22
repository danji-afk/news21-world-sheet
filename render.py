#!/usr/bin/env python3
"""Saturday 21 November 2026 — the day's world news in one deterministic image.

Same proven layout engine as our 20 November sheet: every text block is measured,
reserved and collision-checked; every figure below was verified against named
outlets, and each story carries a provenance chip (CONFIRMED / OFFICIAL /
REPORTED / CLAIM).
"""
import os
import html
from functools import lru_cache
from io import BytesIO
import cairosvg
from PIL import Image, ImageFont

PAPER = '#f6f2e7'
NAVY = '#1a2440'
RED = '#b23a3a'
GOLD = '#c9a227'
WHITE = '#ffffff'
GREEN = '#477453'
TEAL = '#397e85'
MUTED = '#555b63'
SERIF = 'DejaVu Serif'
SANS = 'DejaVu Sans'
PLACED = []
SHORTENED = []
PARTS = []
REGIONS = {}

PROV_COLORS = {'CONFIRMED': GREEN, 'OFFICIAL': TEAL, 'REPORTED': GOLD, 'CLAIM': RED}

def esc(s):
    return html.escape(str(s), quote=True)

def add(s):
    PARTS.append(s)

def rect(x, y, w, h, fill, rx=0, opacity=1):
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx:g}" fill="{fill}" opacity="{opacity:g}"/>'

def path(d, fill='none', stroke=NAVY, sw=1, extra=''):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'

def circle(x, y, r, fill, stroke='none'):
    return f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'

@lru_cache(None)
def font(size, bold=False, serif=False, italic=False):
    base = 'DejaVuSerif' if serif else 'DejaVuSans'
    suffix = '-Bold' if bold else ''
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/' + base + suffix + '.ttf', round(size * 20))

def measure(s, size, bold=False, serif=False, italic=False):
    return font(size, bold, serif, italic).getlength(s) / 20

def intersects(a, b):
    return a[0] < b[2] - .01 and a[2] > b[0] + .01 and a[1] < b[3] - .01 and a[3] > b[1] + .01

def wrap(s, w, size, bold, serif, italic):
    rows = []
    for word in s.split():
        if not rows or measure(rows[-1] + ' ' + word, size, bold, serif, italic) > w:
            rows.append(word)
        else:
            rows[-1] += ' ' + word
    return rows

def block(s, x, y, w, h, size=9, minimum=None, lines=1, bold=False,
          serif=False, italic=False, fill=NAVY, center=False, region='page', shorten=True):
    """Measure every glyph, reserve a line box, then check against ALL text boxes."""
    minimum = size if minimum is None else minimum
    original = s
    while True:
        rows = wrap(s, w, size, bold, serif, italic)
        actual_w = max((measure(t, size, bold, serif, italic) for t in rows), default=0)
        height = len(rows) * size * 1.25
        box = (x, y, x + w, y + height)
        if center:
            box = (x + (w-actual_w)/2, y, x + (w+actual_w)/2, y+height)
        conflict = any(intersects(box, old['box']) for old in PLACED if old['region'] != region)
        fits = len(rows) <= lines and height <= h + .01 and actual_w <= w + .01
        fits = fits and 14 <= box[0] <= box[2] <= 1010 and 0 <= box[1] <= box[3] <= 1010
        if fits and not conflict:
            break
        if size > minimum:
            size = max(minimum, size-.25)
        elif shorten and len(s.split()) > 2 and not conflict:
            s = ' '.join(s.rstrip('…').split()[:-1]).rstrip('.,;:') + '…'
        else:
            raise AssertionError(f'Layout failure ({region}): {original!r}, box={box}, collision={conflict}, lines={len(rows)}')
    if s != original:
        SHORTENED.append((region, original, s))
    PLACED.append({'region': region, 'box': box, 'text': s, 'size': size})
    REGIONS[region] = REGIONS.get(region, 0) + 1
    family = SERIF if serif else SANS
    for i, row in enumerate(rows):
        xx = x+w/2 if center else x
        baseline = y + size + i*size*1.25
        add(f'<text x="{xx:g}" y="{baseline:g}" font-family="{family}" font-size="{size:g}" font-weight="{700 if bold else 400}" font-style="{"italic" if italic else "normal"}" fill="{fill}" text-anchor="{"middle" if center else "start"}">{esc(row)}</text>')
    return height

def pill(label, x, y, w, h, color, size=8, region='page'):
    add(rect(x,y,w,h,color,4))
    top = y+h/2-.65*size
    block(label,x+4,top,w-8,size*1.25,size,fill=WHITE,bold=True,center=True,region=region)

def number(n, x, y, r=7, region='map'):
    add(circle(x,y,r,RED))
    size = 7 if n < 10 else 6.5
    block(str(n),x-r,y-.65*size,2*r,1.25*size,size,bold=True,fill=WHITE,center=True,region=region)

def card(x,y,w,h):
    add(rect(x+3,y+3,w,h,NAVY,6,.12))
    add(rect(x,y,w,h,WHITE,6))

def scene(kind,x,y,w,h,region):
    """Original vector drawings, normalised to a 196 by 52 canvas."""
    add(f'<g transform="translate({x} {y}) scale({w/196} {h/52})">')
    bg = NAVY if kind in ('missiles','kyiv','bridge','markets','drone','ship') else '#e2e8dd'
    add(rect(0,0,196,52,bg,6))
    if kind == 'missiles':
        add(rect(0,0,196,52,'url(#night)'))
        for i,(sx,ex,apex) in enumerate(((8,52,26),(38,86,18),(70,118,30))):
            add(path(f'M {sx} 50 Q {(sx+ex)/2} {apex} {ex} 50',stroke='#d94f4f',sw=2))
            add(circle(ex-4,48,3,GOLD))
        add(rect(150,34,20,18,'#11182d'))
        add(rect(155,40,10,12,'#3a4666'))
    elif kind == 'quake':
        add(rect(0,0,196,52,'#efe9da'))
        add(path('M 0 30 H 30 l 6 -18 l 5 34 l 6 -40 l 6 30 l 5 -8 H 196',stroke=RED,sw=2))
        add(rect(20,8,54,12,'#ffffff',2))
        # magnitude readout is placed by the lettering pass below
    elif kind == 'cop':
        add(circle(76,26,22,TEAL))
        add(path('M 54 26 H 98 M 76 4 Q 57 26 76 48 M 76 4 Q 95 26 76 48',stroke=PAPER))
        add(rect(126,7,7,30,WHITE,3)); add(rect(128,19,3,20,RED)); add(circle(129.5,40,6,RED))
        add(circle(163,26,14,WHITE,NAVY))
        add(path('M 163 26 L 163 15 M 163 26 L 171 30',stroke=NAVY,sw=2))
    elif kind == 'bridge':
        add(rect(0,0,196,52,'url(#night)'))
        add(path('M 0 40 Q 98 10 196 40',stroke='#5a678f',sw=4))
        add(path('M 40 40 V 22 M 98 24 V 8 M 156 40 V 22',stroke='#5a678f',sw=3))
        add(path('M 78 8 L 96 30 M 108 6 L 122 26',stroke=RED,sw=2))
        add(circle(98,6,3,GOLD))
    elif kind == 'kyiv':
        add(rect(0,0,196,52,'url(#night)'))
        add('<ellipse cx="115" cy="50" rx="70" ry="21" fill="url(#fire)"/>')
        for i,bh in enumerate((17,23,15,28,20,32,19,26,17,23,30,18)):
            xx=5+i*16
            add(rect(xx,52-bh,12,bh,'#11182d'))
            add(rect(xx+4,48-bh,3,4,GOLD))
        for i in range(8):
            xx=7+i*23
            add(path(f'M {xx} 2 Q {xx+12} 10 {xx+24} 31',stroke=RED,sw=1.5))
    elif kind == 'drone':
        add(rect(0,0,196,52,'#12203a'))
        add(rect(60,20,44,12,'#628aaa',2))
        add(path('M 60 20 L 44 8 M 104 20 L 120 8 M 60 32 L 44 44 M 104 32 L 120 44',stroke='#8aa5c4',sw=2))
        add('<ellipse cx="82" cy="42" rx="26" ry="8" fill="url(#fire)"/>')
        add(path('M 150 10 Q 168 18 160 40',stroke=GOLD,sw=1.5,extra='stroke-dasharray="3 3"'))
    elif kind == 'ship':
        add(rect(0,0,196,52,'#0f2740'))
        add(path('M 30 40 H 130 L 122 48 H 40 Z',NAVY))
        add(rect(60,28,34,12,'#38547f'))
        add(rect(88,20,14,8,'#38547f'))
        add('<ellipse cx="104" cy="30" rx="20" ry="14" fill="url(#fire)" opacity=".85"/>')
        add(path('M 150 12 H 190 M 150 20 H 182 M 150 28 H 188',stroke='#2a4468',sw=2))
    elif kind == 'plane':
        add(rect(0,0,196,52,'#cfe0ea'))
        add(path('M 30 30 L 150 30 L 168 26 150 22 30 22 Z','#eef3f6',NAVY))
        add(path('M 74 22 L 92 8 104 8 92 22 Z','#eef3f6',NAVY))
        add(path('M 78 30 L 94 44 104 44 94 30 Z','#eef3f6',NAVY))
        add(path('M 22 18 L 40 26 M 14 34 L 34 30',stroke=RED,sw=2))
        add(circle(166,24,4,RED))
    elif kind == 'flags':
        add(rect(0,0,196,52,'#eef0e4'))
        add(path('M 30 8 V 44 M 98 8 V 44',stroke=NAVY,sw=2))
        add(rect(30,8,34,20,RED))
        add(circle(47,18,5,GOLD))
        add(rect(98,8,34,14,'#ffffff'))
        add(circle(115,15,6,RED))
        add(path('M 140 26 Q 168 12 194 24',stroke=TEAL,sw=2))
    elif kind == 'markets':
        add(path('M 10 40 L 50 30 L 90 34 L 130 16 L 170 20 L 186 6',stroke=RED,sw=3))
        add(path('M 10 46 H 190',stroke='#3a4666',sw=1))
        for i,(vx,vh) in enumerate(((20,10),(60,16),(100,12),(140,26),(180,18))):
            add(rect(vx,52-vh,10,vh,'#3a4666',1,.5))
    elif kind == 'cricket':
        add(path('M 48 7 L 69 42',stroke='#b18c55',sw=12))
        add(path('M 42 0 L 48 10',stroke=NAVY,sw=6))
        add(circle(30,40,5,RED))
        add(path('M 20 48 H 178',stroke=GREEN,sw=2))
    elif kind == 'legal':
        add(path('M 98 4 V 14',stroke=NAVY,sw=3))
        add(path('M 60 14 H 136',stroke=NAVY,sw=5))
        add(path('M 68 14 L 84 38 H 52 Z',TEAL))
        add(path('M 128 14 L 144 38 H 112 Z',TEAL))
        add(rect(48,42,100,6,NAVY))
    add('</g>')
    if kind == 'quake':
        block('M 6.7',x+w*.11,y+9,w*.3,14,11,bold=True,fill=RED,region=region)
        block('108 km deep',x+w*.55,y+11,w*.4,12,8,region=region)
    elif kind == 'markets':
        block('2-YEAR LOW',x+w*.66,y+4,w*.32,12,9,bold=True,fill=WHITE,region=region)
        block('$55,122',x+w*.66,y+18,w*.32,14,9,bold=True,fill=GOLD,region=region)
    elif kind == 'bridge':
        block('"WILL NOT STAY"',x+w*.34,y+6,w*.5,14,10,bold=True,fill=WHITE,region=region)
    elif kind == 'cop':
        pill('OVERTIME',x+w*.70,y+2,w*.26,16,RED,8,region)
    elif kind == 'missiles':
        block('3 DOWNED',x+w*.72,y+6,w*.26,12,9,bold=True,fill=GOLD,region=region)
    elif kind == 'plane':
        pass
    elif kind == 'flags':
        pass
    elif kind == 'cricket':
        block('124*',x+w*.5,y+2,w*.42,32,25,bold=True,serif=True,fill=RED,region=region)

# (place, kicker, provenance, headline, body, sources, scene kind, caption chip)
LEADS = [
 ('ANTALYA, TÜRKIYE · CLIMATE','COP31: OVERTIME, NO DEAL','CONFIRMED',
  'Climate summit runs into Saturday with no deal on fossil fuels',
  'Plenary suspended Friday 22:29, resumed Saturday. Draft drops fossil-fuel language; Panama threatens to block it.',
  'UN News, AFP, Al Jazeera','cop','Plenary status'),
 ('RIYADH · WAR','3 MISSILES DOWNED','CONFIRMED',
  'Saudi air defences down three ballistic missiles over Riyadh',
  'Downed before dawn Saturday, days after the PIF tower was hit on Thursday. Houthis threaten Jeddah and Red Sea ports.',
  'Al Jazeera, AFP, SPA','missiles','Sat before dawn'),
 ('JUNÍN, PERU · EARTHQUAKE','QUAKE M 6.7','CONFIRMED',
  'Magnitude-6.7 earthquake shakes central Peru',
  'Struck 00:09 UTC — 19:09 Friday local — 108 km deep near Carhuamayo, felt in Lima. No deaths, damage or tsunami risk.',
  'USGS, Gestión','quake','00:09 UTC'),
]

FEATURES = [
 ('KYIV · WAR','OFFICIAL','Zelensky: the Crimea bridge "will not stay"','Interview given Friday, aired into Saturday; warns of double-tap strikes.','NBC, Kyiv Independent','bridge'),
 ('KRYVYI RIH · WAR','CONFIRMED','Ballistic strike on Kryvyi Rih kills two, hurts dozens','A boy and a young medic died; the toll rose past 58 in a "double-tap".','AP, DW','kyiv'),
 ('TEHRAN · DIPLOMACY','OFFICIAL','Iran: enriched uranium stock "stays in the country"','Araghchi still sees a "fair solution" with Washington on the table.','Iran newspaper, Reuters','flags'),
 ('HORMUZ · WAR','CLAIM','Iran says it shot down a US drone','IRGC names an MQ-9; Washington does not confirm it.','IRIB, Tasnim','drone'),
 ('WASHINGTON · TECH','CONFIRMED','Trump vows a "tremendous tax" on data centres abroad','US firms building AI data centres overseas would pay; no details given.','CNBC, AP','legal'),
 ('BEIJING · DIPLOMACY','CONFIRMED','China tells Japan to "correct" its words on Taiwan','Guo Jiakun\'s remarks came Friday; Tokyo says its stance is unchanged.','Straits Times, CGTN','flags'),
 ('DAVAO · AVIATION','CONFIRMED','Jet lands safely after engine fire alert','Air Niugini 767 from Hong Kong diverted past midnight; 146 safe.','AP, CNA','plane'),
 ('CANBERRA · DIPLOMACY','CONFIRMED','Australia and China agree to talks on AI','Agreed at the leaders\' meeting with Li Qiang; Albanese ends 11-day trip.','ABC, PM.gov.au','flags'),
 ('WELLINGTON · CRICKET','CONFIRMED','Rahul hits an unbeaten 124 against New Zealand','124* at tea, India 344/2 replying to 368; tons in all four SENA lands.','AFP, The Hindu','cricket'),
 ('LAS VEGAS · F1','CONFIRMED','Russell fastest; Verstappen to stewards','1:34.041 in a damp Friday session; their contact is under review.','F1.com, FIA','markets'),
]

BRIEFS = [
 ('COPENHAGEN','Denmark expels Russia\'s defence attaché over a thwarted killing plot.','AP, BBC'),
 ('EU · COP31','EU warns the draft risks turning COP31 into a "fossil summit".','AFP, Euronews'),
 ('PANAMA','Minister threatens to block any COP31 text without fossil-fuel language.','UN News'),
 ('JAKARTA','Indonesia\'s PLN signs six clean-power purchase agreements.','Antara'),
 ('SAUDI ARABIA','Houthis threaten Jeddah and all Saudi Red Sea ports.','Al Jazeera'),
 ('WASHINGTON','Vance says the February Iran strikes were "Trump\'s call".','Reuters'),
 ('GULF OF FINLAND','Cargo ship ablaze after a drone strike; crew evacuates.','Reuters'),
 ('COLOMBIA','"El Chapo Isidro" captured; 11 die in the operation.','AP'),
 ('GAZA','Strike on a food truck kills three; aid convoys pause.','Al Jazeera'),
 ('BRUSSELS','EU and Indonesia seal a long-negotiated trade deal.','EU Council'),
 ('JEFFERSON CITY','Missouri judge approves Bayer\'s $7.25bn Roundup settlement.','AFP, AP'),
 ('ST. LOUIS','Jury hands Bayer a defence win in a weedkiller cancer trial.','AP'),
 ('SEJONG','Five cars of a freight train derail; no one is hurt.','Yonhap'),
 ('TAIPEI','Legislative Yuan passes the NT$20,000 universal cash payout.','Taipei Times'),
 ('NEW DELHI','Pakistan minister joins an SCO forum — first visit since 2023.','Dawn'),
 ('ODISHA','Cyclone Akvan\'s remnants move inland; rain alerts continue.','IMD'),
 ('THE HAGUE','Rights groups urge sanctions after the ICJ\'s Rohingya genocide finding.','AP'),
 ('PYONGYANG','Kim tours teaching-aid factory construction sites.','KCNA'),
 ('TOKYO','Takaichi\'s approval holds above 70% for a third month.','Nikkei'),
 ('BANGKOK','Flood alert along the Chao Phraya and Noi rivers.','The Nation'),
 ('PORT LOUIS','AU roundtable on African risk financing and the risk premium.','Al Jazeera'),
 ('MELBOURNE','One dead, three teens arrested after city stabbings.','ABC'),
 ('SAN FRANCISCO','S&P and Nasdaq slide further as the AI rout deepens.','Reuters'),
]

CONTINENTS = [
 [(-168,71),(-157,72),(-144,69),(-135,60),(-128,55),(-124,48),(-124,40),(-117,32),(-111,29),(-106,23),(-99,17),(-91,18),(-88,16),(-84,10),(-78,8),(-81,18),(-86,22),(-81,25),(-80,32),(-75,36),(-70,43),(-59,48),(-54,53),(-62,59),(-72,61),(-80,68),(-92,72),(-104,69),(-114,72),(-129,70),(-145,73)],
 [(-81,12),(-72,12),(-65,9),(-58,6),(-51,4),(-48,-1),(-40,-3),(-35,-7),(-38,-15),(-41,-22),(-48,-28),(-53,-33),(-58,-39),(-65,-48),(-68,-55),(-74,-51),(-75,-43),(-73,-35),(-71,-26),(-75,-16),(-80,-6),(-79,1)],
 [(-17,36),(-5,36),(5,37),(12,33),(22,32),(31,31),(34,27),(35,20),(42,13),(51,12),(48,5),(43,-1),(40,-10),(35,-18),(33,-26),(25,-34),(18,-35),(12,-28),(9,-19),(7,-8),(1,4),(-7,5),(-14,11),(-17,20),(-16,29)],
 [(-10,36),(-9,43),(-2,44),(1,49),(8,54),(9,59),(16,68),(24,71),(31,70),(29,61),(39,56),(46,51),(40,44),(29,41),(27,37),(23,39),(23,35),(19,40),(15,42),(13,46),(8,44),(7,40),(2,42),(-2,36)],
 [(30,71),(49,68),(68,73),(93,77),(112,73),(132,70),(155,66),(178,66),(177,59),(163,56),(157,50),(145,47),(141,40),(133,35),(128,40),(124,33),(121,25),(113,21),(109,10),(104,1),(99,5),(98,16),(92,22),(87,21),(80,8),(76,9),(72,20),(65,25),(58,24),(51,12),(43,14),(35,29),(36,40),(44,48),(49,56),(37,62)],
 [(-53,82),(-36,83),(-20,76),(-24,68),(-42,60),(-51,61),(-59,68),(-60,75)],
 [(112,-22),(114,-15),(124,-14),(130,-11),(136,-13),(142,-11),(147,-18),(152,-24),(153,-31),(147,-38),(139,-39),(132,-33),(123,-34),(115,-31)],
 [(47,-13),(50,-15),(50,-21),(47,-26),(44,-24),(44,-18)],
 [(130,31),(134,34),(137,36),(140,41),(143,44),(145,43),(141,37),(137,33)],
 [(166,-34),(172,-36),(176,-40),(173,-42),(168,-46),(165,-45),(169,-40)],
 [(95,5),(105,-4),(115,-7),(123,-8),(133,-6),(140,-5),(147,-8),(151,-6),(142,-2),(131,-3),(119,-4),(110,-2),(103,1)],
]

def world_map():
    x,y,w,h=14,638,300,190
    add(rect(x,y,w,h,NAVY,6))
    def xy(lon,lat):
        return x+8+(lon+180)/360*284, y+12+(85-lat)/145*162
    for lat in (-30,0,30,60):
        yy=xy(0,lat)[1]
        add(path(f'M {x+8} {yy} H {x+w-8}',stroke='#38415a'))
    for poly in CONTINENTS:
        pts=[xy(lon,lat) for lon,lat in poly]
        mid=lambda a,b: ((a[0]+b[0])/2,(a[1]+b[1])/2)
        start=mid(pts[-1],pts[0]); d=f'M {start[0]:.2f} {start[1]:.2f}'
        for i,p in enumerate(pts):
            end=mid(p,pts[(i+1)%len(pts)])
            d+=f' Q {p[0]:.2f} {p[1]:.2f} {end[0]:.2f} {end[1]:.2f}'
        add(path(d+' Z',PAPER,'none'))
    pins=[(1,30.7,36.9,178,100),(2,46.7,24.5,225,118),(3,-76.2,-11.5,70,138),
          (4,30.5,50.4,186,44),(5,33.4,47.6,158,28),(6,51.4,35.7,214,96),
          (7,56.3,26.6,238,132),(8,-77,38.9,44,96),(9,116.4,39.9,262,44),
          (10,125.6,7.1,250,140),(11,149.1,-35.3,285,160),(13,-115.1,36.2,44,110),
          (14,12.6,55.7,140,20),(15,4.4,50.8,132,44),(16,-79.5,9,56,140),
          (17,106.8,-6.2,244,158),(18,44.2,15.3,206,146),(19,-90.2,38.6,28,46),
          (20,25,60.2,152,12),(21,-74.1,4.7,64,152),(22,34.5,31.5,170,86),
          (23,4.3,52.1,124,28),(24,-92.2,38.6,32,60),(25,-90.2,38.6,40,74),
          (26,127.3,36.5,272,68),(27,121.5,25,258,90),(28,77.2,28.6,224,72),
          (29,85.8,20.3,232,152),(30,4.3,52.1,116,12),(31,125.8,39,280,26),
          (32,139.7,35.7,292,54),(33,100.5,13.7,226,170),(34,57.5,-20.2,212,182),
          (35,144.9,-37.8,293,186),(36,-122.4,37.8,34,124)]
    for n,lon,lat,dx,dy in pins:
        ax,ay=xy(lon,lat); px,py=x+dx,y+dy
        add(path(f'M {ax:.2f} {ay:.2f} L {px} {py}',stroke=RED))
        add(circle(ax,ay,2,RED)); number(n,px,py,6.5,'map')
    add(circle(45,868,20,NAVY)); number(12,45,868,7,'space-inset')
    block('WELLINGTON',77,846,225,13,9,bold=True,region='space-inset')
    block('Cricket: Rahul 124* · India 344/2',77,862,225,12,8,region='space-inset')
    block('Numbered pins: the 23 brief stories · schematic map',14,897,300,12,7.5,region='legend')
    block('Red circles: story numbers on this page',14,910,300,12,7.5,region='legend')

def brief(n,place,story,source,x,y):
    number(n,x+7,y+7,6.5,'briefs')
    xx=x+19; ww=290; size=9.5
    words=[(word,True,False) for word in place.split()]
    words += [(word,False,False) for word in story.split()]
    words += [(word,False,True) for word in ('('+source+')').split()]
    rows=[[]]; widths=[0]
    for word,bold,italic in words:
        use_size=10 if bold else 8 if italic else size
        runw=measure(word,use_size,bold,False,italic)
        gap=measure(' ',size) if rows[-1] else 0
        if widths[-1]+gap+runw>ww:
            rows.append([]); widths.append(0); gap=0
        rows[-1].append((word,use_size,bold,italic,gap,runw))
        widths[-1]+=gap+runw
    assert len(rows)<=2, (place,len(rows))
    box=(xx,y,xx+ww,y+len(rows)*11.875)
    assert not any(intersects(box,b['box']) for b in PLACED), place
    assert box[2]<=1010 and box[3]<=922
    PLACED.append({'region':'briefs','box':box,'text':f'{place} {story} ({source})','size':size})
    for i,row in enumerate(rows):
        cursor=xx
        for word,fs,bold,italic,gap,rw in row:
            cursor+=gap
            add(f'<text x="{cursor:g}" y="{y+10+i*11.875:g}" font-family="{SANS}" font-size="{fs}" font-weight="{700 if bold else 400}" font-style="{"italic" if italic else "normal"}" fill="{RED if bold else MUTED if italic else NAVY}">{esc(word)}</text>')
            cursor+=rw
        assert cursor<=xx+ww+.01

def build():
    PARTS.clear(); PLACED.clear(); SHORTENED.clear(); REGIONS.clear()
    add('<svg xmlns="http://www.w3.org/2000/svg" width="2048" height="2048" viewBox="0 0 2048 2048"><defs><linearGradient id="night" x2="0" y2="1"><stop stop-color="#10182d"/><stop offset="1" stop-color="#38415a"/></linearGradient><radialGradient id="fire"><stop stop-color="#e28d44" stop-opacity=".9"/><stop offset="1" stop-color="#b23a3a" stop-opacity="0"/></radialGradient></defs><g transform="scale(2)">')
    add(rect(0,0,1024,1024,PAPER))
    block('THE WORLD IN ONE DAY',14,2,280,10,8,bold=True,region='masthead')
    block('36 STORIES · 7 REGIONS · EVERY ONE DATED SATURDAY 21 NOVEMBER 2026',400,2,610,10,8,region='masthead')
    block('Saturday 21 November 2026',14,14,996,65,52,minimum=52,bold=True,serif=True,center=True,region='masthead')
    block('COP31 overruns with no fossil-fuel deal · three missiles downed over Riyadh · a magnitude-6.7 quake shakes Peru · Zelensky: the Crimea bridge "will not stay"',14,80,996,15,12,minimum=10.5,serif=True,italic=True,fill=RED,center=True,region='strapline')
    add(rect(14,97,996,29,'#ebe5d6',4))
    stats=[('3','ballistic missiles downed over Riyadh'),('M 6.7','quake shakes Peru; no damage'),('58+','hurt in the Kryvyi Rih strike'),('146','safe after a jet engine fire alert'),('$55,122','Bitcoin\'s 2-year low, early Saturday'),('124*','Rahul\'s unbeaten ton vs New Zealand')]
    for i,(v,caption) in enumerate(stats):
        xx=14+i*166
        block(v,xx+3,96,160,22,20,minimum=15,bold=True,fill=RED,center=True,region='stats')
        block(caption,xx+3,118,160,10,7.5,center=True,region='stats')
    labels=[('WAR 7',RED),('CLIMATE 5',TEAL),('DIPLOMACY 5',NAVY),('ASIA-PACIFIC 6',NAVY),('AMERICAS 6',RED),('EUROPE 4',NAVY),('MARKETS & SPORT 3',GOLD)]
    for i,(label,c) in enumerate(labels):
        pill(label,14+i*143,132,135,16,c,7.5,'regions')
    for i,(place,kicker,prov,head,body,source,kind,caption) in enumerate(LEADS):
        x=14+i*337; y=156; r=f'hero-{i+1}'
        card(x,y,322,177); scene(kind,x,y,322,69,r)
        pill(caption,x+8,y+51,104,14,RED if i==0 else TEAL if i==1 else RED,7.5,r)
        pill(prov,x+118,y+51,88,14,PROV_COLORS[prov],7.5,r)
        number(i+1,x+15,y+80,7,r)
        block(place,x+28,y+74,270,11,8,bold=True,region=r)
        pill(kicker,x+10,y+88,168,14,RED if i!=1 else TEAL,8,r)
        block(head,x+10,y+105,302,37,15,minimum=13,bold=True,serif=True,lines=2,region=r)
        block(body,x+10,y+144,302,22,9,minimum=8.5,lines=2,region=r)
        block('('+source+')',x+10,y+166,302,10,8,italic=True,region=r)
    cw=(996-4*8)/5
    for i,(kicker,prov,head,body,source,kind) in enumerate(FEATURES):
        x=14+(i%5)*(cw+8); y=341+(i//5)*140; r=f'feature-{i+4}'
        card(x,y,cw,132); scene(kind,x,y,cw,50,r)
        pill(f'{i+4:02}  {kicker}',x+10,y+33,cw-20,17,RED if prov=='CLAIM' else NAVY,10.5,r)
        pill(prov,x+10,y+53,74,13,PROV_COLORS[prov],7.5,r)
        block(head,x+10,y+69,cw-20,29,11.5,minimum=10.5,bold=True,lines=2,region=r)
        block(body,x+10,y+99,cw-20,24,8.5,lines=2,region=r)
        block('('+source+')',x+10,y+123,cw-20,9,7,italic=True,region=r)
    block('WHERE IT HAPPENED',14,617,300,16,12,bold=True,region='map-header')
    block('ALSO ON SATURDAY 21 NOVEMBER — 23 MORE STORIES',330,617,680,16,12,bold=True,region='brief-header')
    world_map()
    for i,(place,story,src) in enumerate(BRIEFS):
        col=i//12; row=i%12; x=330+col*344; y=636+row*23.75
        add(rect(x,y-1,336,23.75,WHITE if row%2==0 else '#eee9df',2))
        brief(i+14,place,story,src,x,y)
    add(rect(14,933,996,37,'#eae2d3',4))
    pill('DATE CHECK',24,942,91,18,RED,9,'date')
    block('These happened earlier but were carried into Saturday: the Kryvyi Rih strike (Friday evening) · Zelensky\'s interview was given Friday · Peru\'s quake was 19:09 Friday local · Trump\'s briefing, China\'s remarks to Japan, the Copenhagen expulsion, Cyclone Akvan\'s landfall and Russell\'s session were all Friday.',125,938,875,26,9,lines=2,region='date')
    add(path('M 14 979 H 1010',stroke=NAVY))
    block('Every story happened, or was first reported, on Saturday 21 November 2026 in some time zone. Claims are attributed, not stated as fact. CONFIRMED = 2+ outlets · OFFICIAL = on record · CLAIM = one side. · Original drawings. 2026-11-21',14,987,996,12,7.5,center=True,region='footer')
    add('</g></svg>')
    assert len(LEADS)+len(FEATURES)+len(BRIEFS)==36
    for i,a in enumerate(PLACED):
        assert 14<=a['box'][0]<=a['box'][2]<=1010, a
        for b in PLACED[i+1:]:
            assert not intersects(a['box'],b['box']), (a,b)
    return ''.join(PARTS)

def render_bytes(svg):
    png=cairosvg.svg2png(bytestring=svg.encode('utf-8'),output_width=2048,output_height=2048)
    with Image.open(BytesIO(png)) as original:
        image=original.convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS)
        output=BytesIO(); image.save(output,format='PNG',optimize=True)
    return output.getvalue()

if __name__=='__main__':
    svg=build()
    first=render_bytes(svg)
    second=render_bytes(build())
    assert first==second, 'Non-deterministic render'
    assert len(first)<=1024*1024, f'PNG exceeds 1 MiB: {len(first)}'
    with Image.open(BytesIO(first)) as check:
        assert check.size==(1024,1024) and check.mode=='RGB'
    output_dir=os.environ.get('MAKEFUN_OUTPUT_DIR','.')
    os.makedirs(output_dir,exist_ok=True)
    with open(os.path.join(output_dir,'entry.png'),'wb') as output:
        output.write(first)
    print(f'Rendered entry.png: 1024x1024 RGB; {len(PLACED)} text blocks checked; {len(first)} bytes')
    print(f'overflows: 0; shortened blocks: {len(SHORTENED)}')
    for region,original,short in SHORTENED:
        print(f'  {region}: {short}')
    print('collisions: 0')
