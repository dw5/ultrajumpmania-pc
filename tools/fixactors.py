#!/usr/bin/env python3
# Makes the mod's custom.* actor sources compile in DynOS: renames them and
# points display lists at vertex buffers by address, since the mod's exporter
# only defined each buffer once, under the name of the first object using it.
import os
import re
import sys

VB_DEF = re.compile(r'Vtx (VB_\w+?_0x([0-9a-fA-F]+))\[\] = \{(.*?)\n\};', re.S)
VB_USE = re.compile(r'gsSPVertex\((VB_\w+?_0x([0-9a-fA-F]+)),')


def fix_model(src):
    bufs = []
    for m in VB_DEF.finditer(src):
        bufs.append((int(m[2], 16), m[3].count('{{{') * 16, m[1]))
    names = {b[2] for b in bufs}
    missing = 0

    def use(m):
        nonlocal missing
        if m[1] in names:
            return m[0]
        a = int(m[2], 16)
        for start, size, name in bufs:
            if start <= a < start + size:
                return f'gsSPVertex({name}+{a - start},' if a > start else f'gsSPVertex({name},'
        missing += 1
        return m[0]
    return VB_USE.sub(use, src), missing


def fix_geo(src):
    # Some geo nodes hold a small junk number instead of a display list address.
    return re.sub(r'DL_\w+?_0x([0-9a-fA-F]+)\b',
                  lambda m: 'NULL' if int(m[1], 16) < 0x100000 else m[0], src)


def main():
    src, out = sys.argv[1:3]
    total = 0
    for d in sorted(os.listdir(src)):
        a = os.path.join(src, d)
        if not os.path.isdir(a) or not os.path.exists(os.path.join(a, 'custom.geo.inc.c')):
            continue
        b = os.path.join(out, d)
        model, missing = fix_model(open(os.path.join(a, 'custom.model.inc.c')).read())
        total += missing
        open(os.path.join(b, 'model.inc.c'), 'w').write(model)
        open(os.path.join(b, 'geo.inc.c'), 'w').write(fix_geo(open(os.path.join(a, 'custom.geo.inc.c')).read()))
        open(os.path.join(b, 'texture.inc.c'), 'w').write(open(os.path.join(a, 'textureNew.inc.c')).read())
    print(f'unresolved vertex buffers: {total}')


main()
