#!/usr/bin/env python3
# Reads the player and object list from a mupen64plus save state of the hack (US addresses).
import gzip
import json
import struct
import sys
import zipfile

ROM_PROBE = 0xf5580, 0x80378800  # engine segment: ROM offset and RAM address


def rdram(path, rom):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    elif raw[:2] == b'PK':
        z = zipfile.ZipFile(path)
        raw = z.read(z.namelist()[0])
    # RDRAM is stored as little endian words. Find it from a piece of code at a known address.
    words = rom[ROM_PROBE[0]:ROM_PROBE[0] + 64]
    probe = b''.join(words[i:i + 4][::-1] for i in range(0, 64, 4))
    base = raw.find(probe) - (ROM_PROBE[1] & 0xffffff)
    data = raw[base:base + 0x800000]
    return b''.join(data[i:i + 4][::-1] for i in range(0, len(data), 4))


def main():
    ram = rdram(sys.argv[1], open(sys.argv[2], 'rb').read())
    u32 = lambda a: struct.unpack('>I', ram[a & 0xffffff:(a & 0xffffff) + 4])[0]
    s16 = lambda a: struct.unpack('>h', ram[a & 0xffffff:(a & 0xffffff) + 2])[0]
    f32 = lambda a: struct.unpack('>f', ram[a & 0xffffff:(a & 0xffffff) + 4])[0]
    mario = 0x8033b170
    out = {'level': s16(0x8032ddf8), 'area': s16(0x8033bac6) if False else None,
           'action': u32(mario + 0xc), 'pos': [f32(mario + 0x3c + i * 4) for i in range(3)],
           'health': s16(mario + 0xae), 'objects': []}
    pool = 0x8033c118 if len(sys.argv) > 3 else 0x8033d488
    for i in range(240):
        o = pool + i * 0x260
        if s16(o + 0x74) & 1:
            out['objects'].append({'bhv': u32(o + 0x20c), 'pos': [round(f32(o + 0xa0 + k * 4), 1) for k in range(3)],
                                   'params': u32(o + 0x188), 'model': u32(o + 0x14)})
    json.dump(out, sys.stdout)


main()
