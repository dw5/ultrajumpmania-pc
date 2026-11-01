#!/usr/bin/env python3
# Compares a level's objects between the hack's RAM (tests/ramdump.py output) and the port's dump.
import json
import sys

emu = json.load(open(sys.argv[1]))
port = []
for line in open(sys.argv[2]):
    p = line.split()
    if p[1] == 'O':
        port.append((p[2], float(p[3]), float(p[4]), float(p[5]), p[6]))
    elif p[1] == 'M':
        print('port player', p[2:])
print('emu player', emu['level'], hex(emu['action']), emu['pos'], emu['health'])
real = [o for o in emu['objects'] if abs(o['pos'][1]) < 30000 and o['bhv'] >> 20 != 0x804]
print('objects: emu', len(real), 'of', len(emu['objects']), 'port', len(port))
used = set()
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 12
for o in real:
    best = min(((abs(o['pos'][0] - q[1]) + abs(o['pos'][1] - q[2]) + abs(o['pos'][2] - q[3]), i) for i, q in enumerate(port) if i not in used), default=None)
    if best and best[0] <= TOL:
        used.add(best[1])
        print(' match', hex(o['bhv']), hex(o['params']), o['pos'], '->', port[best[1]][0], port[best[1]][4])
    else:
        print(' ONLY EMU', hex(o['bhv']), hex(o['params']), o['pos'], hex(o['model']))
for i, q in enumerate(port):
    if i not in used:
        print(' ONLY PORT', q)
