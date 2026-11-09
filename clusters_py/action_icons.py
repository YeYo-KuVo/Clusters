"""Antialiased 24-unit icons, rendered without a symbol font."""
import math
from pathlib import Path
import struct
import tkinter as tk
import zlib


SKULL_ICON_PATH = Path(__file__).with_name('assets') / 'icons' / 'ui' / 'skull.png'
SPROUT_ICON_PATH = Path(__file__).with_name('assets') / 'icons' / 'ui' / 'hei matai.png'


def _arc(cx, cy, radius, start, extent, steps=48):
    return [(cx+radius*math.cos(math.radians(start+extent*i/steps)),
             cy+radius*math.sin(math.radians(start+extent*i/steps))) for i in range(steps+1)]


def _cubic(a, b, c, d, steps=32):
    return [tuple((1-t)**3*a[k] + 3*(1-t)**2*t*b[k] + 3*(1-t)*t*t*c[k] + t**3*d[k]
                  for k in range(2)) for t in (i/steps for i in range(1, steps+1))]


def _inside(x, y, polygons):
    for points in polygons:
        inside = False
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
                inside = not inside
        if inside:
            return True
    return False


def _paths(label):
    if label in ('SoundOn', 'SoundOff'):
        paths = [[(11, 4), (6, 8), (3, 8), (3, 16), (6, 16), (11, 20), (11, 4)]]
        if label == 'SoundOn':
            paths += [_arc(11, 12, 5, -50, 100, 20), _arc(11, 12, 9, -50, 100, 24)]
        else:
            paths += [[(16, 9), (22, 15)], [(22, 9), (16, 15)]]
        return paths
    if label in ('BackgroundOn', 'BackgroundOff'):
        paths = [[(4, 3), (20, 3), (21, 4), (21, 20), (20, 21), (4, 21), (3, 20), (3, 4), (4, 3)],
                 [(3, 17), (9, 11), (14, 16), (17, 13), (21, 17)],
                 _arc(16, 8, 1.4, 0, 360, 16)]
        if label == 'BackgroundOff':
            paths += [[(2, 2), (22, 22)]]
        return paths
    if label == 'ResultPlaying':
        return [[(3, 4), (10, 4), (10, 11), (3, 11), (3, 4)],
                [(3, 14), (10, 14), (10, 21), (3, 21), (3, 14)],
                [(13, 14), (20, 14), (20, 21), (13, 21), (13, 14)],
                [(17, 2), (22, 7), (17, 12), (12, 7), (17, 2)]]
    if label == 'ResultCorrect':
        # An original fishhook silhouette with a curled bowl and three sprout leaves.
        hook = [(12, 7)]
        hook += _cubic((12, 7), (8, 12), (17, 12), (18, 17))
        hook += _cubic((18, 17), (20, 23), (8, 25), (5, 19))
        hook += _cubic((5, 19), (2, 13), (8, 11), (10, 15))
        hook += _cubic((10, 15), (11, 18), (7, 19), (6, 16))
        hook += _cubic((6, 16), (6, 21), (15, 21), (14, 17))
        hook += _cubic((14, 17), (13, 14), (8, 12), (12, 7))
        left = [(10, 9)] + _cubic((10, 9), (5, 10), (2, 7), (2, 5))
        left += _cubic((2, 5), (6, 4), (10, 6), (10, 9))
        upper = [(11.5, 7)] + _cubic((11.5, 7), (8, 5), (9, 2), (11, 0.5))
        upper += _cubic((11, 0.5), (14, 2), (15, 5), (11.5, 7))
        right = [(13, 9)] + _cubic((13, 9), (14, 5), (18, 3), (22, 4))
        right += _cubic((22, 4), (21, 8), (17, 11), (13, 9))
        return [hook, left, upper, right]
    if label == 'Home':
        # One continuous house outline avoids overlapping roof/wall strokes.
        return [[(3, 11), (12, 3), (21, 11), (19, 11), (19, 21),
                 (14.5, 21), (14.5, 15), (9.5, 15), (9.5, 21),
                 (5, 21), (5, 11), (3, 11)]]
    if label == 'Undo':
        curve = [(20, 20), (20, 16)]
        curve += _cubic((20, 16), (20, 12), (17, 9), (13, 9))
        return [curve + [(4, 9)], [(9, 4), (4, 9), (9, 14)]]
    if label == 'Reset':
        return [[(17, 12), (3, 12)], [(9, 6), (3, 12), (9, 18)],
                [(21, 4), (21, 20)]]
    if label in ('Lock', 'Unlock'):
        body = []
        for cx, cy, start in [(7, 13, 180), (17, 13, 270), (17, 19, 0), (7, 19, 90)]:
            body += _arc(cx, cy, 2, start, 90, 8)
        body.append(body[0])
        if label == 'Unlock':
            shackle = [(8, 11), (8, 7)] + _arc(12, 7, 4, 180, 180, 24)[1:] + [(16, 11)]
        else:
            shackle = [(8, 11), (8, 7)] + _arc(12, 7, 4, 180, 170, 24)[1:]
        return [body, shackle]
    return None


def icon_png(label, color, size=26):
    # The supplied skull is artwork, not a generated or recolored path icon.
    if label == 'ResultRetry':
        return SKULL_ICON_PATH.read_bytes()
    if label == 'ResultCorrect':
        return SPROUT_ICON_PATH.read_bytes()
    paths = _paths(label)
    if paths is None:
        return None
    scale = size/24
    segments = [(a[0]*scale, a[1]*scale, b[0]*scale, b[1]*scale)
                for path in paths for a, b in zip(path, path[1:])]
    filled = label == 'ResultCorrect'
    stroke_radius = 1
    polygons = [[(x*scale, y*scale) for x, y in path] for path in paths] if filled else []
    rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            distance = size
            for ax, ay, bx, by in segments:
                dx, dy = bx-ax, by-ay
                t = max(0, min(1, ((x+0.5-ax)*dx+(y+0.5-ay)*dy)/(dx*dx+dy*dy or 1)))
                distance = min(distance, math.hypot(x+0.5-ax-t*dx, y+0.5-ay-t*dy))
            if filled:
                coverage = 0.5+distance if _inside(x+0.5, y+0.5, polygons) else 0.5-distance
            else:
                coverage = stroke_radius*scale+0.5-distance
            alpha = round(255*max(0, min(1, coverage)))
            rows.extend((*rgb, alpha))
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            +chunk(b'IDAT', zlib.compress(bytes(rows)))+chunk(b'IEND', b''))


def draw_action_icon(canvas, label, cx, cy, color, size=26, **options):
    if label not in ('ResultRetry', 'ResultCorrect') and _paths(label) is None:
        return False
    if not hasattr(canvas, '_action_images'):
        canvas._action_images = {}
    key = label, color, size
    if key not in canvas._action_images:
        photo = tk.PhotoImage(master=canvas, data=icon_png(label, color, size), format='PNG')
        canvas._action_images[key] = photo
    canvas.create_image(cx, cy, image=canvas._action_images[key], **options)
    return True
