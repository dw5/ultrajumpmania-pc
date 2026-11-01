#!/usr/bin/env python3
# Compares the mod's dialogs, course names and act names byte by byte with the hack's RAM, using the engine's character table.
# compare-text.py state rom engine moddir
import os
import re
import struct
import sys

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ramdump.py')).read().rsplit('\nmain()', 1)[0]
g = {'__file__': __file__}
exec(src, g)
state, rom, engine, mod = sys.argv[1:5]
r = g['rdram'](state, open(rom, 'rb').read())
seg2 = struct.unpack('>I', r[0x33b408:0x33b40c])[0] & 0xffffff
table = open(engine + '/src/game/level_info.c', encoding='utf8').read()
chars = sorted(((m[1].encode().decode('unicode_escape') if '\\' in m[1] else m[1], int(m[2], 16)) for m in
                re.finditer(r'^ *SM64_CHAR\("([^"]+)", *(0x[0-9A-Fa-f]+)', table, re.M)), key=lambda c: -len(c[0]))


def encode(text):
    out, unknown, i = bytearray(), set(), 0
    while i < len(text):
        for s, c in chars:
            if text.startswith(s, i):
                out.append(c)
                i += len(s)
                break
        else:
            unknown.add(text[i])
            i += 1
    return bytes(out), unknown


def cstr(off):
    end = r.index(b'\xff', off)
    return r[off:end]


def show(b):
    back = {c: s for s, c in reversed(chars)}
    return ''.join(back.get(c, '{%02x}' % c) for c in b).replace('\n', '/')


bad = total = 0
text = open(mod + '/dialogs.lua', encoding='utf8').read()
for m in re.finditer(r'smlua_text_utils_dialog_replace\(DIALOG_(\d+),\s*\d+,\s*(\d+),\s*(-?\d+),\s*(-?\d+),\s*\("(.*?)"\)\)', text, re.S):
    i = int(m[1])
    e = r[seg2 + 0xffc8 + 16 * i:seg2 + 0xffd8 + 16 * i]
    layout = (e[4], *struct.unpack('>hh', e[6:10]))
    want = cstr(seg2 + (struct.unpack('>I', e[12:16])[0] & 0xffffff))
    got, unknown = encode(m[5].replace('\\\n', '\n'))
    total += 1
    if want != got or unknown or layout != (int(m[2]), int(m[3]), int(m[4])):
        bad += 1
        n = next((k for k, (a, b) in enumerate(zip(want, got)) if a != b), min(len(want), len(got)))
        print('dialog', i, 'at', n, 'hack', show(want[max(0, n - 12):n + 16]), '| mod', show(got[max(0, n - 12):n + 16]), sorted(unknown), layout)
print('dialogs', total, 'different', bad)

# Names: every quoted string of courses.lua must exist in the hack's segment 2, apart from the padding.
seg = r[seg2:seg2 + 0x18a0e]
miss = total = 0
for m in re.finditer(r'"([^"]*)"', open(mod + '/courses.lua', encoding='utf8').read()):
    got, unknown = encode(m[1].strip())
    total += 1
    if got and (got + b'\xff' not in seg or unknown):
        miss += 1
        print('name not in hack', repr(m[1]), sorted(unknown))
print('names', total, 'not found', miss)
