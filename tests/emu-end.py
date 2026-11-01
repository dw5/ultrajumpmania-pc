#!/usr/bin/env python3
# Prints where the hack ended up in a save state: emu-end.py state rom
import os
import struct
import sys

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ramdump.py')).read().rsplit('\nmain()', 1)[0]
g = {'__file__': __file__}
exec(src, g)
r = g['rdram'](sys.argv[1], open(sys.argv[2], 'rb').read())
u = lambda a: struct.unpack('>I', r[a:a + 4])[0]
area = u(0x32ddcc)
pos = [int(struct.unpack('>f', r[0x33b1ac + 4 * k:0x33b1b0 + 4 * k])[0]) for k in range(3)]
print('EMU level', struct.unpack('>h', r[0x32ddf8:0x32ddfa])[0], 'area', r[area & 0xffffff] if area else 0,
      'action %x' % u(0x33b17c), 'pos', *pos, 'stars', struct.unpack('>h', r[0x33b21a:0x33b21c])[0])
