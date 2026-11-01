#!/usr/bin/env python3
# Compares a compiled level's vertices, lights and textures in the mod with the hack's RAM.
# compare-level.py state rom levels/<name> <area> <segment>
import re
import struct
import sys
import zlib
from importlib import util

spec = util.spec_from_file_location('ramdump', __file__.replace('compare-level.py', 'ramdump.py'))
SEGMENTS = 0x8033b400


def png_rgba(path):
    d = open(path, 'rb').read()
    p, idat, w, h, ct, bits = 8, b'', 0, 0, 0, 8
    plte, trns = b'', b''
    while p < len(d):
        n, t = struct.unpack('>I4s', d[p:p + 8])
        c = d[p + 8:p + 8 + n]
        if t == b'IHDR':
            w, h, bits, ct = struct.unpack('>IIBB', c[:10])
        elif t == b'IDAT':
            idat += c
        elif t == b'PLTE':
            plte = c
        elif t == b'tRNS':
            trns = c
        p += 12 + n
    raw, ch = zlib.decompress(idat), {6: 4, 2: 3, 0: 1, 4: 2, 3: 1}[ct]
    rowbytes = (w * ch * bits + 7) // 8
    ch = max(1, ch * bits // 8)
    out, prev, q = bytearray(), bytearray(rowbytes), 0
    for _ in range(h):
        f, line = raw[q], bytearray(raw[q + 1:q + 1 + rowbytes])
        q += 1 + rowbytes
        for i in range(len(line)):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out += line
        prev = line
    if ct == 3:
        rgba = bytearray()
        for row in range(h):
            for x in range(w):
                i = out[row * rowbytes + x * bits // 8] >> (8 - bits - x * bits % 8) & ((1 << bits) - 1)
                rgba += plte[i * 3:i * 3 + 3] + bytes((trns[i] if i < len(trns) else 255,))
        return w, h, 6, bytes(rgba)
    return w, h, ct, bytes(out)


def main():
    state, rompath, level, area, seg = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5], 16)
    mod = util.module_from_spec(spec)
    sys.argv = ['x']
    src = open(spec.origin).read().rsplit('\nmain()', 1)[0]
    exec(compile(src, spec.origin, 'exec'), mod.__dict__)
    ram = mod.rdram(state, open(rompath, 'rb').read())
    base = struct.unpack('>I', ram[(SEGMENTS & 0xffffff) + seg * 4:(SEGMENTS & 0xffffff) + seg * 4 + 4])[0]
    print('segment', hex(seg), 'at', hex(base))
    name = level.rstrip('/').split('/')[-1]
    text = open(f'{level}/areas/{area}/custom.model.inc.c').read()
    vb = verts = bad = 0
    examples = []
    for m in re.finditer(r'Vtx VB_\w+?_0x([0-9a-f]+)\[\] = \{(.*?)\n\};', text, re.S):
        a = base + (int(m[1], 16) & 0xffffff)
        vb += 1
        for i, v in enumerate(re.finditer(r'\{\{\{ *(-?\d+), *(-?\d+), *(-?\d+) *\}, *(-?\d+), *\{ *(-?\d+), *(-?\d+) *\}, *\{ *(\d+), *(\d+), *(\d+), *(\d+) *\}', m[2])):
            x, y, z, f, s, t, r, g, b, al = map(int, v.groups())
            want = struct.pack('>hhhhhhBBBB', x, y, z, f, s, t, r, g, b, al)
            got = ram[a + i * 16:a + i * 16 + 16]
            verts += 1
            if want != got:
                bad += 1
                if len(examples) < 6:
                    examples.append((m[1], i, want.hex(), got.hex()))
    print('vertex buffers', vb, 'vertices', verts, 'different', bad, examples[:2])
    lights = bad_l = 0
    for m in re.finditer(r'(Light_t|Ambient_t) Light_\w+?_0x([0-9a-f]+) = \{\s*\{ *(\d+), *(\d+), *(\d+)\}', text):
        a = base + (int(m[2], 16) & 0xffffff)
        lights += 1
        if tuple(ram[a:a + 3]) != tuple(map(int, m.groups()[2:5])):
            bad_l += 1
            print(' light', m[2], m.groups()[2:5], ram[a:a + 8].hex())
    print('lights', lights, 'different', bad_l)
    import glob
    import os
    tex = bad_t = 0
    for f in sorted(glob.glob(f'{level}/{name}_{area}_0x*_custom.*.png')):
        mm = re.search(r'_0x([0-9a-f]+)_custom\.(rgba16|rgba32|ia16|ia8|ia4|i8|i4)\.png', os.path.basename(f))
        if not mm or mm[2] not in ('rgba16', 'rgba32'):
            continue
        w, h, ct, px = png_rgba(f)
        a = base + (int(mm[1], 16) & 0xffffff)
        size = 2 if mm[2] == 'rgba16' else 4
        diffs = 0
        for i in range(w * h):
            if ct == 6:
                r, g, b, al = px[i * 4:i * 4 + 4]
            elif ct == 2:
                r, g, b, al = *px[i * 3:i * 3 + 3], 255
            elif ct == 4:
                r = g = b = px[i * 2]
                al = px[i * 2 + 1]
            else:
                r = g = b = px[i]
                al = 255
            if size == 4:
                got = tuple(ram[a + i * 4:a + i * 4 + 4])
                if got != (r, g, b, al):
                    diffs += 1
            else:
                v = ram[a + i * 2] << 8 | ram[a + i * 2 + 1]
                if abs((v >> 11) * 255 // 31 - r) > 8 or abs((v >> 6 & 31) * 255 // 31 - g) > 8 or abs((v >> 1 & 31) * 255 // 31 - b) > 8 or (al > 127) != bool(v & 1):
                    diffs += 1
        tex += 1
        if diffs:
            bad_t += 1
            print(' texture', mm[1], mm[2], f'{w}x{h}', 'different pixels', diffs)
    print('textures', tex, 'different', bad_t)


main()
