"""Antialiased rounded tile surfaces using PNG alpha instead of Tk polygons."""
import math
import struct
import tkinter as tk
import zlib


def _coverage(x, y, width, height, radius, inset=0):
    half_w, half_h = width/2-inset, height/2-inset
    radius = max(0, min(radius, half_w, half_h))
    dx = abs(x-width/2)-(half_w-radius)
    dy = abs(y-height/2)-(half_h-radius)
    distance = math.hypot(max(dx, 0), max(dy, 0)) + min(max(dx, dy), 0)-radius
    return max(0, min(1, 0.5-distance))


def rounded_png(width, height, radius, fill, outline, border=2):
    def rgb(color):
        return tuple(int(color[i:i+2], 16) for i in (1, 3, 5)) if color else (0, 0, 0)
    fill_rgb, outline_rgb = rgb(fill), rgb(outline)
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            outer = _coverage(x+0.5, y+0.5, width, height, radius)
            inner = _coverage(x+0.5, y+0.5, width, height, max(0, radius-border), border)
            f = inner if fill else 0
            o = max(0, outer-inner) if outline else 0
            if not outline and fill:
                f = outer
            alpha = f+o
            color = [round((fill_rgb[c]*f+outline_rgb[c]*o)/alpha) if alpha else 0
                     for c in range(3)]
            rows.extend((*color, round(alpha*255)))
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            +chunk(b'IDAT', zlib.compress(bytes(rows)))+chunk(b'IEND', b''))


def smooth_rectangle(canvas, x1, y1, x2, y2, radius=8, fill='', outline='', width=2, **options):
    # Keep Tk image references alive and reuse surfaces across updates.
    if not hasattr(canvas, '_tile_images'):
        canvas._tile_images = {}
    key = (round(x2-x1), round(y2-y1), radius, fill, outline, width)
    if key not in canvas._tile_images:
        canvas._tile_images[key] = tk.PhotoImage(master=canvas, data=rounded_png(*key), format='PNG')
    return canvas.create_image(x1, y1, image=canvas._tile_images[key], anchor='nw', **options)
