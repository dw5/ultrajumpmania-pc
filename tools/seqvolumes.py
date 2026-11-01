#!/usr/bin/env python3
# The mod registers every sequence at volume 75. The hack uses the volume each sequence sets itself.
import os
import re
import sys

mod = sys.argv[1]
path = os.path.join(mod, 'main.lua')
text = open(path).read()


def volume(m):
    data = open(os.path.join(mod, 'sound', m[3] + '.m64'), 'rb').read()
    # Sequence commands are read up to the first channel setup. 0xdb sets the volume.
    p = 0
    while p < min(len(data), 64):
        if data[p] == 0xdb and 0 < data[p + 1] <= 127:
            return f'{m[1]}{data[p + 1]}{m[2]}"{m[3]}"'
        p += 1
    return m[0]


text = re.sub(r'(smlua_audio_utils_replace_sequence\(0x\w+, 0x\w+, )75(, )"(\w+)"', volume, text)
open(path, 'w').write(text)
