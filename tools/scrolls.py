#!/usr/bin/env python3
# Connects the levels' scrolling textures. The mod places RM_Scroll_Texture
# objects whose parameter is a vertex address, but only ships placeholders for
# the add_scroll_target calls they need, so nothing scrolls without these.
# As in the hack's own behaviour, X is the vertex count; see patch_engine.py.
import glob
import os
import re
import sys

OBJECT = re.compile(r'OBJECT(?:_WITH_ACTS)?\([^,]*,\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),[^)]*?(0x[0-9a-fA-F]+),\s*(?:RM|editor)_Scroll_Texture')
VTX = re.compile(r'Vtx (VB_\w+?_0x([0-9a-fA-F]+))\[\] = \{(.*?)\n\};', re.S)


def main():
    levels, out = sys.argv[1:3]
    lines, missing = [], 0
    for level in sorted(glob.glob(os.path.join(levels, '*'))):
        script = os.path.join(level, 'script.c')
        if not os.path.exists(script):
            continue
        # Segment 0x0E addresses repeat between areas, so each scroller only targets its own area.
        text = open(script, errors='ignore').read()
        sections = re.split(r'const LevelScript local_objects_\w+?_(\d+)_\[\]', text)
        for area, body in zip(sections[1::2], sections[2::2]):
            buffers = []
            model = os.path.join(level, 'areas', area, 'custom.model.inc.c')
            if os.path.exists(model):
                for m in VTX.finditer(open(model, errors='ignore').read()):
                    buffers.append((int(m[2], 16), m[3].count('{{{'), m[1]))
            buffers.sort()
            seen = set()
            for m in OBJECT.finditer(body):
                count, addr = abs(int(m[1])), int(m[4], 16)
                if addr in seen:
                    continue
                seen.add(addr)
                start = addr
                for base, size, name in buffers:
                    if count <= 0:
                        break
                    if base <= start < base + size * 16:
                        offset = (start - base) // 16
                        take = min(count, size - offset)
                        lines.append(f'add_scroll_target({addr:#x}, "{name}", {offset}, {take})')
                        count -= take
                        start = base + size * 16
                if count > 0:
                    missing += 1
    with open(out, 'a') as f:
        f.write('\n' + '\n'.join(lines) + '\n')
    print(f'scroll targets {len(lines)}, objects without vertices {missing}')


main()
