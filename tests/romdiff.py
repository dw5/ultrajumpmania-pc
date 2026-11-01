#!/usr/bin/env python3
# Prints every run of bytes where the hack's code differs from vanilla, disassembled. Run in the container.
import subprocess
import sys
import tempfile

RANGES = [(0x1000, 0xf5580, 0x80245000), (0xf5580, 0x108a40, 0x80378800 - 0xf5580)]


def dis(data, vram):
    with tempfile.NamedTemporaryFile() as f:
        f.write(data)
        f.flush()
        out = subprocess.run(['mips-linux-gnu-objdump', '-D', '-b', 'binary', '-mmips:4300', '-EB', f'--adjust-vma={vram:#x}', f.name],
                             capture_output=True, text=True).stdout
    return [l.split(None, 1)[1] if False else l.strip() for l in out.splitlines() if ':\t' in l]


def main():
    hack, van = (open(p, 'rb').read() for p in sys.argv[1:3])
    for start, end, delta in RANGES:
        p = start
        while p < end:
            if hack[p:p + 4] == van[p:p + 4]:
                p += 4
                continue
            q = p
            same = 0
            while q < end and same < 3:
                same = same + 1 if hack[q:q + 4] == van[q:q + 4] else 0
                q += 4
            q -= same * 4
            print(f'--- rom {p:#x} ram {p + delta:#x} words {(q - p) // 4}')
            if (q - p) <= 160:
                for a, b in zip(dis(van[p:q], p + delta), dis(hack[p:q], p + delta)):
                    print(' V', a.split('\t', 1)[1].replace('\t', ' ')[:60].ljust(60), '| H', b.split('\t', 2)[-1].replace('\t', ' ')[:50])
            p = q


main()
