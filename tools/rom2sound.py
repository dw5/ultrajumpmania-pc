#!/usr/bin/env python3
"""Rebuild the engine's sound banks from the hack ROM, keeping the engine's extra character banks."""
import struct, sys, zlib

ROM_CTL = 0x57b720
ROM_TBL = 0x593560
ROM_BANKS = 38
ENV_END = (0, 0xfffd, 0xfffe, 0xffff)


def be32(r, p): return struct.unpack('>I', r[p:p + 4])[0]
def align(b, n=16): b.extend(b'\0' * (-len(b) % n))


class Bank:
    """Converts one big-endian 32-bit ROM bank body to the engine's little-endian 64-bit layout."""

    def __init__(self, r, base, ninst, ndrums):
        self.r, self.base, self.out = r, base, bytearray()
        self.memo = {}
        self.ninst, self.ndrums = ninst, ndrums

    def p(self, o): return self.base + o

    def book(self, o):
        r, p = self.r, self.p(o)
        order, npred = struct.unpack('>ii', r[p:p + 8])
        n = 8 * order * npred
        addr = len(self.out)
        self.out += struct.pack('<ii', order, npred)
        self.out += struct.pack(f'<{n}h', *struct.unpack(f'>{n}h', r[p + 8:p + 8 + n * 2]))
        align(self.out)
        return addr

    def loop(self, o):
        r, p = self.r, self.p(o)
        start, end, count, pad = struct.unpack('>IIiI', r[p:p + 16])
        addr = len(self.out)
        self.out += struct.pack('<IIiI', start, end, count, pad)
        if count:
            self.out += struct.pack('<16h', *struct.unpack('>16h', r[p + 16:p + 48]))
        align(self.out)
        return addr

    def sample(self, o):
        if not o:
            return 0
        if ('s', o) in self.memo:
            return self.memo['s', o]
        r, p = self.r, self.p(o)
        addr_, loop, book, size = struct.unpack('>IIII', r[p + 4:p + 20])
        b, l = self.book(book), self.loop(loop)
        addr = len(self.out)
        self.out += struct.pack('<QQQQIxxxx', 0, addr_, l, b, size)
        self.memo['s', o] = addr
        return addr

    def env(self, o):
        if ('e', o) in self.memo:
            return self.memo['e', o]
        r, p = self.r, self.p(o)
        addr = len(self.out)
        while True:
            self.out += r[p:p + 4]
            if struct.unpack('>H', r[p:p + 2])[0] in ENV_END:
                break
            p += 4
        align(self.out)
        self.memo['e', o] = addr
        return addr

    def sound(self, p):
        s, t = struct.unpack('>If', self.r[p:p + 8])
        return s, t

    def instrument(self, o):
        r, p = self.r, self.p(o)
        env = self.env(be32(r, p + 4))
        snd = [self.sound(p + 8 + i * 8) for i in range(3)]
        addrs = [(self.sample(s), t) for s, t in snd]
        a = len(self.out)
        self.out += bytes((0, r[p + 1], r[p + 2], r[p + 3])) + b'\0' * 4 + struct.pack('<Q', env)
        for s, t in addrs:
            self.out += struct.pack('<Qfxxxx', s, t)
        return a

    def drum(self, o):
        r, p = self.r, self.p(o)
        s, t = self.sound(p + 4)
        sa = self.sample(s)
        env = self.env(be32(r, p + 12))
        a = len(self.out)
        self.out += bytes((r[p], r[p + 1], 0, 0)) + b'\0' * 4 + struct.pack('<QfxxxxQ', sa, t, env)
        return a

    def build(self):
        r = self.r
        self.out += b'\0' * (8 + 8 * self.ninst)
        align(self.out)
        for i in range(self.ninst):
            o = be32(r, self.base + 4 + i * 4)
            if o:
                struct.pack_into('<Q', self.out, 8 + i * 8, self.instrument(o))
        align(self.out)
        d = be32(r, self.base)
        if self.ndrums and d:
            poses = [self.drum(be32(r, self.p(d) + i * 4)) if be32(r, self.p(d) + i * 4) else 0 for i in range(self.ndrums)]
            align(self.out)
            struct.pack_into('<Q', self.out, 0, len(self.out))
            for x in poses:
                self.out += struct.pack('<Q', x)
            align(self.out)
        return bytes(self.out)


def main():
    rom_path, ctl_in, tbl_in, ctl_out, tbl_out = sys.argv[1:6]
    r = open(rom_path, 'rb').read()
    ctl, tbl = zlib.decompress(open(ctl_in, 'rb').read()), zlib.decompress(open(tbl_in, 'rb').read())
    count = struct.unpack('<H', ctl[2:4])[0]

    # ctl: hack banks first, then the engine's extra banks unchanged.
    head_size = (8 + count * 16 + 15) & ~15
    data = bytearray()
    entries = []
    for i in range(ROM_BANKS):
        o, ln = struct.unpack('>II', r[ROM_CTL + 4 + i * 8:ROM_CTL + 12 + i * 8])
        p = ROM_CTL + o
        ninst, ndrums, shared, date = struct.unpack('>IIII', r[p:p + 16])
        start = head_size + len(data)
        data += struct.pack('<IIII', ninst, ndrums, shared, date) + Bank(r, p + 16, ninst, ndrums).build()
        align(data)
        entries.append((start, head_size + len(data) - start))
    for i in range(ROM_BANKS, count):
        o, ln = struct.unpack('<QI', ctl[8 + i * 16:8 + i * 16 + 12])
        start = head_size + len(data)
        data += ctl[o:o + ln]
        align(data)
        entries.append((start, ln))
    head = bytearray(ctl[:8])
    for o, ln in entries:
        head += struct.pack('<QIxxxx', o, ln)
    align(head)
    align(data, 64)

    # tbl: the hack's samples are appended so the runtime ROM loader cannot overwrite them.
    t_off, t_len = struct.unpack('>II', r[ROM_TBL + 4:ROM_TBL + 12])
    samples = r[ROM_TBL + t_off:ROM_TBL + t_off + t_len]
    new_tbl = bytearray(tbl)
    align(new_tbl, 64)
    at = len(new_tbl)
    new_tbl += samples
    align(new_tbl, 64)
    for i in range(ROM_BANKS):
        struct.pack_into('<QI', new_tbl, 8 + i * 16, at, t_len)

    open(ctl_out, 'wb').write(zlib.compress(bytes(head) + bytes(data), 9))
    open(tbl_out, 'wb').write(zlib.compress(bytes(new_tbl), 9))
    print(f'ctl {len(ctl)} -> {len(head) + len(data)}, tbl {len(tbl)} -> {len(new_tbl)}')
    print(f'{len(new_tbl):#x}')


main()
