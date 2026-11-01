#!/usr/bin/env python3
# Compares each area's warp nodes in the mod's level script with the hack's RAM. Run from the repo root.
import re
import struct
import sys

sys.argv = ['x']
g = {'__file__': 'tests/ramdump.py'}
exec(open('tests/ramdump.py').read().rsplit('\nmain()', 1)[0], g)
rom = open('../Ultra Jump Mania - Simpleflip Island.z64', 'rb').read()


def w(r, a):
    return struct.unpack('>I', r[a:a + 4])[0]


for st, name in (('16', 'castle_grounds'), ('9', 'bob'), ('17', 'bitdw')):
    r = g['rdram'](f'build/oracle/{st}.st', rom)
    cur = w(r, 0x32ddcc) & 0xffffff
    base = cur - r[cur] * 0x3c
    s = open(f'build/ultra jump mania/levels/{name}/script.c').read()
    mod = {}
    for m in re.finditer(r'local_warps_\w+?_(\d+)_\[\] = \{(.*?)\n\};', s, re.S):
        mod[int(m[1])] = {tuple(map(int, n.groups())) for n in re.finditer(r'WARP_NODE\((\d+),(\d+),(\d+),(\d+),', m[2])}
    if not mod:
        for m in re.finditer(r'AREA\((\d+),(.*?)END_AREA\(\)', s, re.S):
            mod[int(m[1])] = {tuple(map(int, n.groups())) for n in re.finditer(r'WARP_NODE\((\d+),(\d+),(\d+),(\d+),', m[2])}
    for a in sorted(mod):
        p, ram, n = w(r, base + a * 0x3c + 0x14) & 0xffffff, set(), 0
        while p and n < 300 and p < 0x7ffff0:
            ram.add(tuple(r[p:p + 4]))
            p, n = w(r, p + 8) & 0xffffff, n + 1
        d = ram ^ mod[a]
        print(st, 'area', a, 'warps', len(ram), len(mod[a]), 'same' if not d else ('DIFF', sorted(d)[:10]))
