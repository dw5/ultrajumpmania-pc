#!/usr/bin/env python3
# Writes a mupen64plus save state with the player moved: spots.py in.st out.st rom x y z yaw
import gzip
import os
import struct
import sys
from importlib import util

raw = gzip.open(sys.argv[1]).read() if open(sys.argv[1], 'rb').read(2) == b'\x1f\x8b' else open(sys.argv[1], 'rb').read()
rom = open(sys.argv[3], 'rb').read()
words = rom[0xf5580:0xf5580 + 64]
probe = b''.join(words[i:i + 4][::-1] for i in range(0, 64, 4))
base = raw.find(probe) - 0x378800
x, y, z, yaw = float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), int(sys.argv[7])
buf = bytearray(raw)
def rd(a): return struct.unpack('<I', buf[base + (a & 0xffffff):base + (a & 0xffffff) + 4])[0]
def wr(a, v): buf[base + (a & 0xffffff):base + (a & 0xffffff) + 4] = struct.pack('<I', v)
def wf(a, v): wr(a, struct.unpack('>I', struct.pack('>f', v))[0])
M = 0x8033b170
for i, v in enumerate((x, y, z)):
    wf(M + 0x3c + i * 4, v)
    wf(M + 0x48 + i * 4, 0.0)
wf(M + 0x54, 0.0)
obj = rd(M + 0x88)
for i, v in enumerate((x, y, z)):
    wf(obj + 0xa0 + i * 4, v)
w = rd(M + 0x2c)  # faceAngle[0], faceAngle[1]
wr(M + 0x2c, (w & 0xffff0000) | (yaw & 0xffff))
if os.environ.get('HEAL'):
    wr(M + 0xac, (rd(M + 0xac) & 0xffff0000) | 0x880)
if os.environ.get('WARP6'):
    # Points the warp the player is about to touch at level 6, like the hub's unused warp 240: WARP6=<warp id>.
    node = rd(rd(0x8032ddcc) + 0x14)
    while node:
        if rd(node) >> 24 == int(os.environ['WARP6']):
            wr(node, (rd(node) & 0xff000000) | (6 << 16) | (1 << 8) | 50)
        node = rd(node + 8)
if os.environ.get('NOWATER'):
    # Makes the water quads of Simpleflip Island's area 1 fully transparent.
    ram = bytearray(b''.join(buf[i:i + 4][::-1] for i in range(base, base + 0x800000, 4)))
    mark = struct.pack('>8h', -14930, -16154, -9149, -16154, -9149, -3805, -14930, -3805)
    p = ram.find(mark)
    while p >= 0:
        print('water quad', hex(p))
        ram[p + len(mark) + 2:p + len(mark) + 4] = b'\0\0'
        p = ram.find(mark, p + 1)
    buf[base:base + 0x800000] = b''.join(ram[i:i + 4][::-1] for i in range(0, 0x800000, 4))
if os.environ.get('FREEZESCROLL'):
    # Stops the sea planes of Simpleflip Island's area 1 scrolling and restores their first UVs.
    PLANES = {0xe081490: [(1899, -387), (-999, -387), (-999, 1255), (1899, 1255), (1759, -79), (-521, -79), (-521, 999), (1759, 999)],
              0xe081510: [(3189, -1118), (-2289, -1118), (-2289, 1986), (3189, 1986), (2926, -535), (-1385, -535), (-1385, 1502), (2926, 1502)]}
    seg = rd(0x8033b400 + 0x0e * 4)
    for param, uvs in PLANES.items():
        for i in range(240):
            o = 0x8033d488 + i * 0x260
            if rd(o + 0x188) == param:
                w = rd(o + 0x74)
                wr(o + 0x74, w & 0xffff)
                print('froze scroll object', hex(o))
        a = 0x80000000 | (seg + (param & 0xffffff))
        for i, (u, v) in enumerate(uvs):
            wr(a + i * 16 + 8, (u & 0xffff) << 16 | (v & 0xffff))
open(sys.argv[2], 'wb').write(gzip.compress(bytes(buf)))
