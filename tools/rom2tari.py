#!/usr/bin/env python3
"""Export the hack's changed models from the ROM as DynOS actors."""
import os, re, struct, sys, zlib

SEG4 = 0x11a35b8
SEG4_END = 0x11fff00
VAN_SEG17 = 0x1279b0
MODEL_CMD = 0x2abce0

# Folder, builtin geo it overrides, geo address, segment bases in the ROM.
EXPORTS = [
    ('mario', 'mario_geo', None, {0x04: SEG4}),
    ('goomba', 'goomba_geo', 0x0400002c, {0x04: SEG4}),
    ('ujm_star', 'star_geo', 0x16000ea0, {0x16: 0x218da0, 0x03: 0xab2450}),
    ('ujm_transparent_star', 'transparent_star_geo', 0x16000f6c, {0x16: 0x218da0, 0x03: 0xab2450}),
]
SEGS = {}

CC = ['COMBINED', 'TEXEL0', 'TEXEL1', 'PRIMITIVE', 'SHADE', 'ENVIRONMENT', '1', 'NOISE', '0']
CC_B = ['COMBINED', 'TEXEL0', 'TEXEL1', 'PRIMITIVE', 'SHADE', 'ENVIRONMENT', 'CENTER', 'K4', '0']
CC_C = ['COMBINED', 'TEXEL0', 'TEXEL1', 'PRIMITIVE', 'SHADE', 'ENVIRONMENT', 'SCALE',
        'COMBINED_ALPHA', 'TEXEL0_ALPHA', 'TEXEL1_ALPHA', 'PRIMITIVE_ALPHA', 'SHADE_ALPHA',
        'ENV_ALPHA', 'LOD_FRACTION', 'PRIM_LOD_FRAC', 'K5']
AC = ['COMBINED', 'TEXEL0', 'TEXEL1', 'PRIMITIVE', 'SHADE', 'ENVIRONMENT', '1', '0']
AC_C = ['LOD_FRACTION', 'TEXEL0', 'TEXEL1', 'PRIMITIVE', 'SHADE', 'ENVIRONMENT', 'PRIM_LOD_FRAC', '0']


def u32(r, p): return struct.unpack('>I', r[p:p + 4])[0]
def s16(r, p): return struct.unpack('>h', r[p:p + 2])[0]
def off(a): return SEGS[a >> 24] + (a & 0xffffff)


def png(path, w, h, rgba):
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    raw = b''.join(b'\0' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def rgba16(v):
    c = lambda x: (x << 3) | (x >> 2)
    return bytes((c(v >> 11 & 31), c(v >> 6 & 31), c(v >> 1 & 31), 255 if v & 1 else 0))


def decode(r, a, fmt, siz, w, h, pal):
    p, out = off(a), bytearray()
    bits = 4 << siz
    for i in range(w * h):
        q = i * bits
        if bits == 4:
            v = (r[p + q // 8] >> (4 if i % 2 == 0 else 0)) & 15
        elif bits == 8:
            v = r[p + i]
        elif bits == 16:
            v = struct.unpack('>H', r[p + i * 2:p + i * 2 + 2])[0]
        else:
            out += r[p + i * 4:p + i * 4 + 4]
            continue
        if fmt == 0:
            out += rgba16(v)
        elif fmt == 2:
            out += rgba16(struct.unpack('>H', r[off(pal) + v * 2:off(pal) + v * 2 + 2])[0])
        elif fmt == 3:
            if bits == 4:
                g = (v >> 1) * 255 // 7; al = 255 if v & 1 else 0
            elif bits == 8:
                g = (v >> 4) * 17; al = (v & 15) * 17
            else:
                g = v >> 8; al = v & 255
            out += bytes((g, g, g, al))
        elif fmt == 4:
            g = v * 17 if bits == 4 else v
            out += bytes((g, g, g, g))
        else:
            raise SystemExit(f'texture format {fmt}')
    return bytes(out)


class Model:
    def __init__(self, rom, outdir, root_name):
        self.r, self.out, self.root_name = rom, outdir, root_name
        self.gfx, self.vtx, self.lights, self.tex = {}, {}, {}, {}
        self.geo, self.funcs = {}, {}
        # Texture state carries across calls, since a parent list can load for its children.
        self.pend = self.pal = self.load = self.size = None
        self.tile = {}

    def tex_name(self, a, fmt, siz, w, h, pal):
        key = (a, pal)
        if key not in self.tex:
            n = f'tari_tex_{a & 0xffffff:06x}' + (f'_{pal & 0xffffff:06x}' if pal else '')
            png(os.path.join(self.out, n + '.rgba16.png'), w, h, decode(self.r, a, fmt, siz, w, h, pal))
            self.tex[key] = n
        return self.tex[key]

    def light(self, base):
        n = f'tari_light_{base & 0xffffff:06x}'
        if n not in self.lights:
            p = off(base)
            r = self.r
            self.lights[n] = (r[p], r[p + 1], r[p + 2], r[p + 8], r[p + 9], r[p + 10],
                              *[struct.unpack('b', r[p + 16 + i:p + 17 + i])[0] for i in range(3)])
        return n

    def vert(self, a, n):
        k = (a, n)
        self.vtx[k] = f'tari_vtx_{a & 0xffffff:06x}_{n}'
        return self.vtx[k]

    def emit_texture(self, lines):
        t, ws, hs = self.size
        w, ht = ws + 1, hs + 1
        fmt, siz, _, _, tl = self.tile[t]
        cmt, maskt, shiftt = (tl >> 18) & 3, (tl >> 14) & 15, (tl >> 10) & 15
        cms, masks, shifts = (tl >> 8) & 3, (tl >> 4) & 15, tl & 15
        n = self.tex_name(self.load[0], fmt, siz, w, ht, self.pal if fmt == 2 else 0)
        lines += [f'gsDPSetTextureImage(0, 2, 1, {n})',
                  'gsDPTileSync()',
                  'gsDPSetTile(0, 2, 0, 0, 7, 0, 0, 0, 0, 0, 0, 0)',
                  'gsDPLoadSync()',
                  f'gsDPLoadBlock(7, 0, 0, {w * ht - 1}, {min(2047, (2047 + max(1, w * 2 // 8)) // max(1, w * 2 // 8))})',
                  'gsDPPipeSync()',
                  f'gsDPSetTile(0, 2, {(w * 2 + 7) // 8}, 0, {t}, 0, {cmt}, {maskt}, {shiftt}, {cms}, {masks}, {shifts})',
                  f'gsDPSetTileSize({t}, 0, 0, {(w - 1) << 2}, {(ht - 1) << 2})']

    def dl(self, a):
        if a == 0:
            return 'NULL'
        if a in self.gfx:
            return f'tari_dl_{a & 0xffffff:06x}'
        self.gfx[a] = lines = []
        r, p = self.r, off(a)
        while True:
            h, l = u32(r, p), u32(r, p + 4)
            c = h >> 24
            p += 8
            if c == 0xb8:
                lines.append('gsSPEndDisplayList()')
                break
            if c == 0x06:
                n = self.dl(l)
                if (h >> 16) & 255 == 1:
                    lines.append(f'gsSPBranchList({n})')
                    break
                lines.append(f'gsSPDisplayList({n})')
            elif c == 0x04:
                cnt, v0 = ((h >> 20) & 15) + 1, (h >> 16) & 15
                lines.append(f'gsSPVertex({self.vert(l, cnt)}, {cnt}, {v0})')
            elif c == 0xbf:
                lines.append(f'gsSP1Triangle({(l >> 16 & 255) // 10}, {(l >> 8 & 255) // 10}, {(l & 255) // 10}, 0x0)')
            elif c == 0x03:
                k = (h >> 16) & 255
                if k == 0x86:
                    lines.append(f'gsSPLight(&{self.light(l - 8)}.l, 1)')
                elif k == 0x88:
                    lines.append(f'gsSPLight(&{self.light(l)}.a, 2)')
                else:
                    raise SystemExit(f'movemem {hex(h)}')
            elif c == 0xe7:
                lines.append('gsDPPipeSync()')
            elif c == 0xe6 or c == 0xe8:
                pass
            elif c == 0xfd:
                self.pend = (l, (h >> 21) & 7, (h >> 19) & 3)
            elif c == 0xf0:
                self.pal, self.pend = self.pend[0], None
            elif c == 0xf3:
                self.load, self.pend = self.pend, None
                # Vanilla-style lists set the tile size first, in the parent list.
                if self.size and 0xf2 not in (r[p + i * 8] for i in range(4)):
                    self.emit_texture(lines)
            elif c == 0xf5:
                t = (l >> 24) & 7
                if t != 7:
                    self.tile[t] = ((h >> 21) & 7, (h >> 19) & 3, (l >> 20) & 15, (l >> 14) & 15 if 0 else 0, l)
            elif c == 0xf2:
                t = (l >> 24) & 7
                self.size = (t, ((l >> 12) & 0xfff) >> 2, (l & 0xfff) >> 2)
                if self.load:
                    self.emit_texture(lines)
            elif c == 0xba:
                if (h & 0xffff) != 0x0e02:
                    raise SystemExit(f'setothermode_h {hex(h)}')
            elif c == 0xb9:
                lines.append(f'gsDPSetAlphaCompare({l})')
            elif c == 0xbb:
                lines.append(f'gsSPTexture({l >> 16}, {l & 0xffff}, {(h >> 11) & 7}, {(h >> 8) & 7}, {h & 255})')
            elif c == 0xb6:
                lines.append(f'gsSPClearGeometryMode({l})')
            elif c == 0xb7:
                lines.append(f'gsSPSetGeometryMode({l})')
            elif c == 0xbc:
                lines.append(f'gsSPNumLights({(l - 0x80000000) // 32 - 1})')
            elif c == 0xfb:
                lines.append(f'gsDPSetEnvColor({l >> 24}, {l >> 16 & 255}, {l >> 8 & 255}, {l & 255})')
            elif c == 0xfc:
                w0, w1 = h, l
                f = lambda t, i: t[i] if i < len(t) else '0'
                a0, c0 = (w0 >> 20) & 15, (w0 >> 15) & 31
                b0, d0 = (w1 >> 28) & 15, (w1 >> 15) & 7
                aa0, ac0 = (w0 >> 12) & 7, (w0 >> 9) & 7
                ba0, da0 = (w1 >> 12) & 7, (w1 >> 9) & 7
                a1, c1 = (w0 >> 5) & 15, w0 & 31
                b1, d1 = (w1 >> 24) & 15, (w1 >> 6) & 7
                aa1, ac1 = (w1 >> 21) & 7, (w1 >> 18) & 7
                ba1, da1 = (w1 >> 3) & 7, w1 & 7
                args = [f(CC, a0), f(CC_B, b0), f(CC_C, c0), f(AC, d0), f(AC, aa0), f(AC, ba0), f(AC_C, ac0), f(AC, da0),
                        f(CC, a1), f(CC_B, b1), f(CC_C, c1), f(AC, d1), f(AC, aa1), f(AC, ba1), f(AC_C, ac1), f(AC, da1)]
                lines.append('gsDPSetCombineLERP(' + ', '.join(args) + ')')
            else:
                raise SystemExit(f'gfx cmd {hex(c)} at {hex(p)}')
        return f'tari_dl_{a & 0xffffff:06x}'

    def geo_name(self, a):
        return self.root_name if a == self.root else f'tari_geo_{a & 0xffffff:06x}'

    def walk(self, a):
        if a in self.geo:
            return
        self.geo[a] = o = []
        r, p = self.r, off(a)
        while True:
            c, x = r[p], r[p + 1]
            if c == 0x00:
                t = u32(r, p + 4); self.walk(t); o.append(f'GEO_BRANCH_AND_LINK({self.geo_name(t)})'); p += 8
            elif c == 0x01:
                o.append('GEO_END()'); return
            elif c == 0x02:
                t = u32(r, p + 4); self.walk(t); o.append(f'GEO_BRANCH({x}, {self.geo_name(t)})'); p += 8
                if x == 0:
                    return
            elif c == 0x03:
                o.append('GEO_RETURN()'); return
            elif c == 0x04:
                o.append('GEO_OPEN_NODE()'); p += 4
            elif c == 0x05:
                o.append('GEO_CLOSE_NODE()'); p += 4
            elif c == 0x0b:
                o.append('GEO_NODE_START()'); p += 4
            elif c == 0x0e:
                f = u32(r, p + 4); self.funcs[f] = 1
                o.append(f'GEO_SWITCH_CASE({s16(r, p + 2)}, FUNC_{f:08x})'); p += 8
            elif c == 0x10:
                o.append('GEO_TRANSLATE_ROTATE(%d, %s)' % (x, ', '.join(str(s16(r, p + i)) for i in range(4, 16, 2)))); p += 16
            elif c == 0x11 or c == 0x12:
                n = 'GEO_TRANSLATE_NODE' if c == 0x11 else 'GEO_ROTATION_NODE'
                v = [s16(r, p + i) for i in (2, 4, 6)]; p += 8
                if x & 0x80:
                    o.append(f'{n}_WITH_DL({x & 15}, {v[0]}, {v[1]}, {v[2]}, {self.dl(u32(r, p))})'); p += 4
                else:
                    o.append(f'{n}({x & 15}, {v[0]}, {v[1]}, {v[2]})')
            elif c == 0x13:
                d = u32(r, p + 8)
                o.append(f'GEO_ANIMATED_PART({x}, {s16(r, p + 2)}, {s16(r, p + 4)}, {s16(r, p + 6)}, {self.dl(d) if d else 0})'); p += 12
            elif c == 0x14:
                v = [s16(r, p + i) for i in (2, 4, 6)]; p += 8
                if x & 0x80:
                    o.append(f'GEO_BILLBOARD_WITH_PARAMS_AND_DL({x & 15}, {v[0]}, {v[1]}, {v[2]}, {self.dl(u32(r, p))})'); p += 4
                else:
                    o.append(f'GEO_BILLBOARD_WITH_PARAMS({x & 15}, {v[0]}, {v[1]}, {v[2]})')
            elif c == 0x15:
                o.append(f'GEO_DISPLAY_LIST({x}, {self.dl(u32(r, p + 4))})'); p += 8
            elif c == 0x16:
                o.append(f'GEO_SHADOW({s16(r, p + 2)}, {s16(r, p + 4)}, {s16(r, p + 6)})'); p += 8
            elif c == 0x18:
                f = u32(r, p + 4); self.funcs[f] = 1
                o.append(f'GEO_ASM({s16(r, p + 2)}, FUNC_{f:08x})'); p += 8
            elif c == 0x1c:
                f = u32(r, p + 8); self.funcs[f] = 1
                o.append(f'GEO_HELD_OBJECT({x}, {s16(r, p + 2)}, {s16(r, p + 4)}, {s16(r, p + 6)}, FUNC_{f:08x})'); p += 12
            elif c == 0x1d:
                o.append(f'GEO_SCALE({x}, {u32(r, p + 4)})'); p += 8
            elif c == 0x20:
                o.append(f'GEO_CULLING_RADIUS({s16(r, p + 2)})'); p += 4
            else:
                raise SystemExit(f'geo cmd {hex(c)} at {hex(p)}')


# Engine geo functions in the US ROM (sm64 decomp names).
GEO_FUNCS = {
    0x8029db48: 'geo_switch_anim_state',
    0x80277d6c: 'geo_mirror_mario_backface_culling',
    0x802770a4: 'geo_mirror_mario_set_alpha',
    0x80277150: 'geo_switch_mario_stand_run',
    0x802776d8: 'geo_switch_mario_cap_effect',
    0x802b1bb0: 'geo_move_mario_part_from_parent',
    0x80277294: 'geo_mario_tilt_torso',
    0x802773a4: 'geo_mario_head_rotation',
    0x80277740: 'geo_switch_mario_cap_on_off',
    0x802771bc: 'geo_switch_mario_eyes',
    0x80277824: 'geo_mario_rotate_wing_cap_wings',
    0x802774f4: 'geo_switch_mario_hand',
    0x802775cc: 'geo_mario_hand_foot_scaler',
    0x8027795c: 'geo_switch_mario_hand_grab_pos',
}


def check_funcs(van, source):
    """Confirm the table against vanilla's first Mario geo block (head rotation at 0x170002E0)."""
    src = open(source).read()
    for n in GEO_FUNCS.values():
        if n not in src:
            raise SystemExit(f'{n} missing from port source')
    if u32(van, VAN_SEG17 + 0x2e0 + 4) != 0x802773a4:
        raise SystemExit('vanilla geo table mismatch')


def export(r, names, out, folder, root_name, root):
    os.makedirs(out, exist_ok=True)
    m = Model(r, out, root_name)
    m.root = root if root is not None else u32(r, MODEL_CMD + 4)
    m.walk(m.root)
    missing = [hex(f) for f in m.funcs if f not in names]
    if missing:
        raise SystemExit(f'unnamed geo functions: {missing}')

    with open(os.path.join(out, 'geo.inc.c'), 'w') as f:
        f.write('#include "geo_header.h"\n')
        for a, o in sorted(m.geo.items(), key=lambda kv: kv[0] == m.root):
            f.write(f'const GeoLayout {m.geo_name(a)}[] = {{\n')
            for line in o:
                f.write('   ' + re.sub(r'FUNC_([0-9a-f]{8})', lambda x: names[int(x[1], 16)], line) + ',\n')
            f.write('};\n\n')
    with open(os.path.join(out, 'texture.inc.c'), 'w') as f:
        for n in m.tex.values():
            f.write(f'ALIGNED8 static const Texture {n}[] = {{\n#include "actors/{folder}/{n}.rgba16.inc.c"\n}};\n\n')
    with open(os.path.join(out, 'model.inc.c'), 'w') as f:
        for n, v in m.lights.items():
            f.write(f'static const Lights1 {n} = gdSPDefLights1(\n    {v[0]}, {v[1]}, {v[2]},\n    {v[3]}, {v[4]}, {v[5]}, {v[6]}, {v[7]}, {v[8]}\n);\n\n')
        for (a, n), name in m.vtx.items():
            f.write(f'static const Vtx {name}[] = {{\n')
            p = off(a)
            for i in range(n):
                x, y, z, _, s, t = struct.unpack('>hhhHhh', r[p:p + 12])
                cr, cg, cb, ca = r[p + 12:p + 16]
                f.write(f'    {{{{{{{x}, {y}, {z}}}, 0, {{{s}, {t}}}, {{{cr}, {cg}, {cb}, {ca}}}}}}},\n')
                p += 16
            f.write('};\n\n')
        for a, lines in m.gfx.items():
            f.write(f'const Gfx tari_dl_{a & 0xffffff:06x}[] = {{\n')
            for line in lines:
                f.write(f'    {line},\n')
            f.write('};\n\n')
    print(f'{folder}: geo blocks {len(m.geo)}, display lists {len(m.gfx)}, vertex buffers {len(m.vtx)}, '
          f'lights {len(m.lights)}, textures {len(m.tex)}')


def main():
    hack, van_path, source, out = sys.argv[1:5]
    r, van = open(hack, 'rb').read(), open(van_path, 'rb').read()
    check_funcs(van, source)
    for folder, name, root, segs in EXPORTS:
        SEGS.clear()
        SEGS.update(segs)
        export(r, GEO_FUNCS, os.path.join(out, folder), folder, name, root)


main()
