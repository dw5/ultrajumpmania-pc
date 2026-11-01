#!/usr/bin/env python3
# Overrides every engine texture the hack changed, replacing the mod's copy if it has one. The hack moves and
# decompresses segments, so each vanilla block is located in the hack ROM by
# matching its unchanged contents, then each texture in it is compared to vanilla.
import collections
import os
import re
import struct
import sys
import zlib

ASSET = re.compile(r'ROM_ASSET_LOAD_TEXTURE\(\s*(\w+),\s*"([^"]+)",\s*(0x[0-9a-fA-F]+),\s*(\d+),\s*(0x[0-9a-fA-F]+),\s*(\d+)\)')
FORMAT = re.compile(r'\.(rgba16|rgba32|ia16|ia8|ia4|ia1|i8|i4)\.inc\.c$')
ENDING_BLOCK = 0x49e710
SIZES = {'rgba16': 16, 'rgba32': 32, 'ia16': 16, 'ia8': 8, 'ia4': 4, 'ia1': 1, 'i8': 8, 'i4': 4}


def mio0(r, p):
    if r[p:p + 4] != b'MIO0':
        return None
    size, comp, raw = struct.unpack('>III', r[p + 4:p + 16])
    out, layout, comp, raw = bytearray(), p + 16, p + comp, p + raw
    bit = 0
    while len(out) < size:
        if r[layout + bit // 8] >> (7 - bit % 8) & 1:
            out.append(r[raw])
            raw += 1
        else:
            v = struct.unpack('>H', r[comp:comp + 2])[0]
            comp += 2
            for _ in range((v >> 12) + 3):
                out.append(out[len(out) - (v & 0xfff) - 1])
        bit += 1
    return bytes(out)


def locate(hack, block):
    votes = collections.Counter()
    for off in range(0, len(block) - 64, max(64, len(block) // 40)):
        chunk = block[off:off + 64]
        if len(set(chunk)) < 12:
            continue
        p = hack.find(chunk)
        if p >= 0 and hack.find(chunk, p + 1) < 0:
            votes[p - off] += 1
    if not votes:
        return None
    return votes.most_common(1)[0][0]


def rgba(data, fmt):
    out = bytearray()
    if fmt == 'rgba16':
        for i in range(0, len(data), 2):
            v = data[i] << 8 | data[i + 1]
            out += bytes(((v >> 11) * 255 // 31, (v >> 6 & 31) * 255 // 31, (v >> 1 & 31) * 255 // 31, 255 if v & 1 else 0))
    elif fmt == 'rgba32':
        out += data
    elif fmt == 'ia16':
        for i in range(0, len(data), 2):
            out += bytes((data[i],) * 3 + (data[i + 1],))
    elif fmt == 'ia8':
        for b in data:
            out += bytes(((b >> 4) * 17,) * 3 + ((b & 15) * 17,))
    elif fmt == 'i8':
        for b in data:
            out += bytes((b,) * 4)
    elif fmt == 'ia4':
        for b in data:
            for v in (b >> 4, b & 15):
                out += bytes(((v >> 1) * 255 // 7,) * 3 + (255 if v & 1 else 0,))
    elif fmt == 'i4':
        for b in data:
            for v in (b >> 4, b & 15):
                out += bytes((v * 17,) * 4)
    elif fmt == 'ia1':
        for b in data:
            for i in range(8):
                out += bytes(((b >> (7 - i) & 1) * 255,) * 4)
    return bytes(out)


def write_tex(path, name, w, h, px):
    # DynOS raw texture: type, name, format RGBA, size 32b, dimensions, pixels.
    with open(path, 'wb') as f:
        f.write(bytes((0x15, len(name))) + name.encode())
        f.write(struct.pack('<iiiiI', 0, 3, w, h, len(px)) + px)


def png(w, h, px):
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    raw = b''.join(b'\0' + px[y * w * 4:(y + 1) * w * 4] for y in range(h))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def patch_levels(levels, changed):
    # Compiled levels embed their textures as PNGs, out of reach of .tex overrides.
    patched = 0
    for name in os.listdir(levels):
        path = os.path.join(levels, name)
        if not name.endswith('.lvl'):
            continue
        raw = open(path, 'rb').read()
        if raw[:8] != b'DYNOSBIN':
            continue
        data = zlib.decompress(raw[16:])
        edited = False
        for tex, image in changed.items():
            mark = bytes((0x02, len(tex))) + tex.encode()
            p = data.find(mark)
            while p >= 0:
                q = p + len(mark)
                size = struct.unpack('<I', data[q:q + 4])[0]
                if data[q + 4:q + 8] == b'\x89PNG':
                    data = data[:q] + struct.pack('<I', len(image)) + image + data[q + 4 + size:]
                    edited = True
                    patched += 1
                p = data.find(mark, q)
        if edited:
            with open(path, 'wb') as f:
                f.write(raw[:8] + struct.pack('<Q', len(data)) + zlib.compress(data))
    return patched


def ending(hack, van, engine, out):
    # The hack's end screen replaces the cake entirely, so nothing matches by content. Its
    # level script names the new data: one 320x240 picture in 64x32 tiles (64x16 on the
    # last row). The engine draws 80x20 tiles, so rebuild the picture and cut it up again.
    p = van.find(b'\x18\x0c\x00\x07' + struct.pack('>I', ENDING_BLOCK))
    start = struct.unpack('>I', hack[p + 4:p + 8])[0]
    picture = bytearray(320 * 240 * 4)
    pos = start
    for row in range(8):
        height = 32 if row < 7 else 16
        for col in range(5):
            tile = rgba(hack[pos:pos + 64 * height * 2], 'rgba16')
            pos += 64 * height * 2
            for y in range(height):
                at = (row * 32 + y) * 320 * 4 + col * 64 * 4
                picture[at:at + 64 * 4] = tile[y * 64 * 4:(y + 1) * 64 * 4]
    source = open(os.path.join(engine, 'levels/ending/leveldata.c'), errors='ignore').read()
    vertices = {}
    blocks = {}
    for m in re.finditer(r'ROM_ASSET_LOAD_VTX\((cake_end_vertex_\w+), (0x[0-9a-f]+), \d+, (0x[0-9a-f]+), (\d+)\)', source):
        rom = int(m[2], 16)
        blocks.setdefault(rom, mio0(van, rom))
        data = blocks[rom][int(m[3], 16):int(m[3], 16) + int(m[4])]
        vertices[m[1]] = [struct.unpack('>hh', data[i:i + 4]) for i in range(0, len(data), 16)]
    count = 0
    for m in re.finditer(r'gsDPLoadTextureBlock\((cake_end_texture_\d+),.*?\n\s*gsSPVertex\((cake_end_vertex_\w+),', source):
        quad = vertices[m[2]]
        left, top = min(v[0] for v in quad), 240 - max(v[1] for v in quad)
        px = b''.join(bytes(picture[(top + y) * 320 * 4 + left * 4:(top + y) * 320 * 4 + (left + 80) * 4]) for y in range(20))
        write_tex(os.path.join(out, m[1] + '.tex'), m[1], 80, 20, px)
        count += 1
    print(f'end screen tiles {count}')


def dimensions(source):
    return {m[1]: (int(m[2]), int(m[3])) for m in
            re.finditer(r'define_builtin_tex\((\w+), "[^"]+", (\d+), (\d+),', source)}


def main():
    hack_path, van_path, engine, out = sys.argv[1:5]
    hack, van = open(hack_path, 'rb').read(), open(van_path, 'rb').read()
    table = dimensions(open(os.path.join(engine, 'data/dynos_mgr_builtin_tex.cpp')).read())
    blocks = collections.defaultdict(list)
    for top in ('actors', 'levels', 'bin', 'textures', 'src'):
        for d, _, files in os.walk(os.path.join(engine, top)):
            for f in files:
                if f.endswith(('.c', '.h')):
                    text = open(os.path.join(d, f), errors='ignore').read()
                    for m in ASSET.finditer(text):
                        blocks[int(m[3], 16)].append(m.groups())

    changed = unlocated = skipped = 0
    level_textures = {}
    for rom, assets in sorted(blocks.items()):
        block = mio0(van, rom)
        base = None
        if block is None:
            block = van[rom:rom + max(int(a[4], 16) + int(a[5]) for a in assets)]
        base = locate(hack, block)
        if base is None:
            unlocated += len(assets)
            continue
        for name, path, _, _, seg, size in assets:
            seg, size = int(seg, 16), int(size)
            if base + seg < 0 or hack[base + seg:base + seg + size] == block[seg:seg + size]:
                continue
            fmt = FORMAT.search(path)
            dims = table.get(name)
            target = os.path.join(out, name)
            if not fmt or not dims:
                skipped += 1
                continue
            w, h = dims
            if w * h * SIZES[fmt[1]] // 8 != size:
                skipped += 1
                continue
            px = rgba(hack[base + seg:base + seg + size], fmt[1])
            write_tex(target + '.tex', name, w, h, px)
            if path.startswith('levels/'):
                level_textures[name] = png(w, h, px)
            changed += 1
            print(name)
    ending(hack, van, engine, out)
    patched = patch_levels(os.path.join(os.path.dirname(out), 'levels'), level_textures)
    print(f'patched in compiled levels {patched}')
    print(f'changed {changed}, unusable {skipped}, in unlocated blocks {unlocated}, blocks {len(blocks)}')


main()
