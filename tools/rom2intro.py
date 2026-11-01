#!/usr/bin/env python3
# Puts the hack's logo into the engine's intro and restores the boot splash.
# The hack patches the logo function to draw the display list at LOGO_DL. The
# hack skips the Mario head, so after the splash the game goes to Select File.
import os
import re
import struct
import sys

SEG7 = 0x3F80000
LOGO_DL = 0x1BEB0


def seg7(a):
    if a >> 24 != 7:
        raise SystemExit(f'not a segment 7 address: {a:#x}')
    return a & 0xffffff


def logo(s):
    verts, textures, body = {}, {}, []
    a = LOGO_DL
    while True:
        c = s[a]
        w0, w1 = struct.unpack('>II', s[a:a + 8])
        a += 8
        if c == 0xB8:
            body.append('gsSPEndDisplayList()')
            break
        elif c == 0xBF:
            body.append(f'gsSP1Triangle({s[a - 3] // 10}, {s[a - 2] // 10}, {s[a - 1] // 10}, 0x0)')
        elif c == 0x04:
            n, v = (s[a - 7] >> 4) + 1, s[a - 7] & 15
            verts[seg7(w1)] = max(verts.get(seg7(w1), 0), n)
            body.append(f'gsSPVertex(intro_ujm_vtx_{seg7(w1):05x}, {n}, {v})')
        elif c == 0xFD:
            textures[seg7(w1)] = 1
            body.append(f'gsDPSetTextureImage(G_IM_FMT_RGBA, G_IM_SIZ_16b, 1, intro_ujm_tex_{seg7(w1):05x})')
        elif c == 0x03:
            body.append({0x86: 'gsSPLight(&intro_ujm_light.l, 1)', 0x88: 'gsSPLight(&intro_ujm_light.a, 2)'}[s[a - 7]])
        elif c == 0xB7:
            body.append(f'gsSPSetGeometryMode({w1})')
        elif c == 0xBB:
            body.append(f'gsSPTexture({w1 >> 16}, {w1 & 0xffff}, {(w0 >> 11) & 7}, {(w0 >> 8) & 7}, {w0 & 255})')
        elif c in (0xE6, 0xE7, 0xE8, 0xF2, 0xF3, 0xF5, 0xFB, 0xFC):
            # RDP commands have no pointers and the same encoding on PC.
            body.append(f'{{{{ {w0:#x}, {w1:#x} }}}}')
        else:
            raise SystemExit(f'unknown F3D command {c:#x} at seg7 {a - 8:#x}')

    out = ['\n']
    amb, dif = s[0xC940:0xC943], s[0xC948:0xC94B]
    d = struct.unpack('bbb', s[0xC950:0xC953])
    out.append(f'static const Lights1 intro_ujm_light = gdSPDefLights1({amb[0]}, {amb[1]}, {amb[2]}, '
               f'{dif[0]}, {dif[1]}, {dif[2]}, {d[0]}, {d[1]}, {d[2]});\n')
    for v, n in sorted(verts.items()):
        rows = []
        for i in range(n):
            x, y, z, f, u, t, r, g, b, al = struct.unpack('>hhhHhhBBBB', s[v + i * 16:v + i * 16 + 16])
            rows.append(f'    {{{{{{{x}, {y}, {z}}}, {f}, {{{u}, {t}}}, {{{r}, {g}, {b}, {al}}}}}}},\n')
        out.append(f'static const Vtx intro_ujm_vtx_{v:05x}[] = {{\n' + ''.join(rows) + '};\n')
    for t in textures:
        size = 4096 if t >= 0xE160 else 2048
        data = ', '.join(str(b) for b in s[t:t + size])
        out.append(f'ALIGNED8 static const u8 intro_ujm_tex_{t:05x}[] = {{ {data} }};\n')
    out.append('const Gfx intro_ujm_logo_dl[] = {\n' + ''.join(f'    {c},\n' for c in body) + '};\n')
    return ''.join(out)


def main():
    hack, engine = sys.argv[1:3]
    s = open(hack, 'rb').read()[SEG7:SEG7 + 0x80000]

    path = os.path.join(engine, 'levels/intro/leveldata.c')
    open(path, 'a').write(logo(s))

    path = os.path.join(engine, 'src/menu/intro_geo.c')
    src = open(path).read()
    if 'intro_seg7_dl_0700B3A0' not in src:
        raise SystemExit('logo display list not found in intro_geo.c')
    src = src.replace('intro_seg7_dl_0700B3A0', 'intro_ujm_logo_dl')
    open(path, 'w').write(src.replace('static s16 sIntroFrameCounter;',
                                      'extern const Gfx intro_ujm_logo_dl[];\nstatic s16 sIntroFrameCounter;', 1))

    # The hack clears this function pointer, so it shows no copyright.
    path = os.path.join(engine, 'levels/intro/geo.c')
    src = open(path).read()
    if 'GEO_ASM(0, geo_intro_tm_copyright)' not in src:
        raise SystemExit('copyright node not found in intro geo')
    open(path, 'w').write(src.replace('GEO_ASM(0, geo_intro_tm_copyright)', 'GEO_ASM(0, NULL)'))

    path = os.path.join(engine, 'levels/entry.c')
    src = open(path).read()
    open(path, 'w').write(src.replace('#if 1\n', '#if 0\n', 1))

    path = os.path.join(engine, 'levels/intro/script.c')
    src, n = re.subn(r'( *)EXIT_AND_EXECUTE\(([^,]*, _introSegmentRomStart, _introSegmentRomEnd), level_intro_mario_head_regular\),',
                     r'\1EXIT_AND_EXECUTE(/*seg*/ 0x14, _menuSegmentRomStart, _menuSegmentRomEnd, level_main_menu_entry_1),',
                     open(path).read(), count=1)
    if n != 1:
        raise SystemExit('splash exit not found in intro script')
    # The hack's head scripts skip Goddard and go to Select File, which is where SAVE & QUIT lands.
    for name in ('regular', 'dizzy'):
        old = f'const LevelScript level_intro_mario_head_{name}[] = {{\n    INIT_LEVEL(),\n'
        if old not in src:
            raise SystemExit(f'{name} head script not found in intro script')
        src = src.replace(old, old + '    JUMP(script_intro_L1),\n', 1)
    open(path, 'w').write(src)

    path = os.path.join(engine, 'levels/menu/script.c')
    src = open(path).read()
    old = '    SET_REG(/*value*/ LEVEL_CASTLE_GROUNDS),\n    EXIT_AND_EXECUTE(/*seg*/ 0x15'
    if old not in src:
        raise SystemExit('menu exit not found in menu script')
    src = src.replace(old, '    CALL(/*arg*/ 0, /*func*/ lvl_ujm_reset_perm_models),\n' + old, 1)
    open(path, 'w').write(src.replace('const LevelScript level_main_menu_entry_1[] = {',
                                      'extern s32 lvl_ujm_reset_perm_models(s16 arg, s32 unused);\n'
                                      'const LevelScript level_main_menu_entry_1[] = {', 1))

    # The first FREE_LEVEL_POOL ends permanent model loading, and the splash and
    # menu now run first. Without this, the player and common models die on level load.
    path = os.path.join(engine, 'src/engine/level_script.c')
    src = open(path).read()
    marker = 'static void level_cmd_load_model_from_geo(void) {'
    if marker not in src:
        raise SystemExit('model loader not found in level_script.c')
    open(path, 'w').write(src.replace(marker, 's32 lvl_ujm_reset_perm_models(UNUSED s16 arg, UNUSED s32 unused) {\n'
                                      '    sFinishedLoadingPerm = false;\n    return 0;\n}\n\n' + marker, 1))

    # The engine never renders a camera before the first level, so it dereferences gCamera unchecked.
    path = os.path.join(engine, 'src/game/rendering_graph_node.c')
    src = open(path).read()
    old = 'if (mtxf_inverse_non_affine(invCameraMatrix, gCamera->mtx)) {'
    if old not in src:
        raise SystemExit('camera check not found in rendering_graph_node.c')
    open(path, 'w').write(src.replace(old, 'if (gCamera && mtxf_inverse_non_affine(invCameraMatrix, gCamera->mtx)) {'))


main()
