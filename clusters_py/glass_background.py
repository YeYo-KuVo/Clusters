"""Render frosted panels over artwork without modifying the source image."""
from array import array
from pathlib import Path
import struct
import subprocess

# Cream veil over the displayed art; saved originals stay untouched.
BACKGROUND_FADE = 0.22


def read_bitmap(path):
    data = Path(path).read_bytes()
    offset = struct.unpack_from('<I', data, 10)[0]
    width, height = struct.unpack_from('<ii', data, 18)
    bits, compression = struct.unpack_from('<HI', data, 28)
    if bits not in (24, 32) or compression != 0:
        raise ValueError('Expected an uncompressed RGB bitmap')
    rows = abs(height)
    stride = ((width * bits + 31) // 32) * 4
    pixels = bytearray(width * rows * 3)
    for y in range(rows):
        source_y = y if height < 0 else rows-1-y
        row = data[offset+source_y*stride:offset+(source_y+1)*stride]
        for x in range(width):
            src, dst = x*(bits//8), (y*width+x)*3
            pixels[dst:dst+3] = bytes((row[src+2], row[src+1], row[src]))
    return width, rows, pixels


def frost(width, height, pixels, panels, radius=8, opacity=0.62):
    """Box blur the underlying art, then blend a translucent white surface."""
    stride = width + 1
    integrals = [array('I', [0]) * ((height+1)*stride) for _ in range(3)]
    for channel, integral in enumerate(integrals):
        for y in range(height):
            running = 0
            prev, current = y*stride, (y+1)*stride
            for x in range(width):
                running += pixels[(y*width+x)*3+channel]
                integral[current+x+1] = integral[prev+x+1] + running
    output = bytearray(pixels)
    for left, top, panel_width, panel_height in panels:
        right, bottom = left+panel_width, top+panel_height
        for y in range(max(0, top), min(height, bottom)):
            for x in range(max(0, left), min(width, right)):
                # Rounded mask, with a narrow antialiased edge.
                cx = min(max(x+0.5, left+radius), right-radius)
                cy = min(max(y+0.5, top+radius), bottom-radius)
                distance = ((x+0.5-cx)**2 + (y+0.5-cy)**2)**0.5
                coverage = min(1, max(0, radius+0.5-distance))
                if not coverage:
                    continue
                x0, x1 = max(0, x-7), min(width, x+8)
                y0, y1 = max(0, y-7), min(height, y+8)
                area = (x1-x0)*(y1-y0)
                dst = (y*width+x)*3
                for channel, integral in enumerate(integrals):
                    total = (integral[y1*stride+x1] - integral[y0*stride+x1]
                             - integral[y1*stride+x0] + integral[y0*stride+x0])
                    tinted = total/area*(1-opacity) + 255*opacity
                    output[dst+channel] = round(pixels[dst+channel]*(1-coverage) + tinted*coverage)
    return output


def render_background(asset, width, height, panels, directory):
    directory = Path(directory)
    bitmap = directory/'scaled.bmp'
    if asset is None:
        w, h = width, height
        pixels = bytearray((248, 243, 238)) * (w*h)
    else:
        # PNG originals are retained at full resolution; only the runtime copy is
        # scaled. Cover the viewport without stretching leaves, flowers or fruit.
        header = Path(asset).read_bytes()[:24]
        if header[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Background originals must be PNG files')
        source_width, source_height = struct.unpack('>II', header[16:24])
        scale = max(width/source_width, height/source_height)
        scaled_width = max(width, round(source_width*scale))
        scaled_height = max(height, round(source_height*scale))
        subprocess.run(['/usr/bin/sips', '-z', str(scaled_height), str(scaled_width),
                        '-s', 'format', 'bmp', str(asset), '--out', str(bitmap)],
                       check=True, timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if (scaled_width, scaled_height) != (width, height):
            subprocess.run(['/usr/bin/sips', '-c', str(height), str(width), str(bitmap),
                            '--out', str(bitmap)], check=True, timeout=5,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        w, h, pixels = read_bitmap(bitmap)
        cream = (248, 243, 238)
        for channel, tint in enumerate(cream):
            table = bytes(round(value*(1-BACKGROUND_FADE) + tint*BACKGROUND_FADE)
                          for value in range(256))
            pixels[channel::3] = pixels[channel::3].translate(table)
    result = frost(w, h, pixels, panels)
    output = directory/'glass.ppm'
    output.write_bytes(f'P6\n{w} {h}\n255\n'.encode() + result)
    return output
