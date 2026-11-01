#!/usr/bin/env python3
# Runs the same frame-exact inputs in the hack and the port, to compare physics frame by frame.
#   traj.py gen in.st out.st rom main.lua   writes a state with an input script and logger injected, and the port's mod
#   traj.py cmp out.st rom port.log         compares the logs
import gzip
import math
import os
import struct
import sys

A, B, Z = 0x8000, 0x4000, 0x2000
UP, DOWN, LEFT, RIGHT, NONE = (0, 80), (0, -80), (-80, 0), (80, 0), (0, 0)
CONTROLLER, MARIO, LAKITU = 0x8033af90, 0x8033b170, 0x8033c698
CODE, TABLE, LOG, COUNT = 0x80600000, 0x80601000, 0x80700000, 0x80600ff0


def script():
    s = [(20, NONE, 0), (40, UP, 0)]
    s += [(4, UP, A), (21, UP, 0), (4, UP, A), (24, UP, 0), (4, UP, A), (20, UP, 0), (130, DOWN, 0), (30, NONE, 0)]  # triple jump, back
    s += [(40, DOWN, 0), (30, NONE, 0), (8, NONE, Z), (6, NONE, Z | A), (60, NONE, 0)]  # backflip
    s += [(30, UP, 0), (2, UP, Z), (6, UP, Z | A), (50, NONE, 0)]  # long jump
    s += [(30, RIGHT, 0), (4, LEFT, 0), (4, LEFT, A), (45, NONE, 0)]  # side flip
    s += [(30, DOWN, 0), (4, DOWN, B), (50, NONE, 0)]  # dive
    s += [(30, UP, 0), (4, UP, A), (6, UP, 0), (4, UP, B), (50, NONE, 0)]  # jump kick
    s += [(30, LEFT, 0), (4, LEFT, Z), (4, LEFT, Z | B), (50, NONE, 0)]  # slide kick
    s += [(4, NONE, B), (8, NONE, 0), (4, NONE, B), (8, NONE, 0), (4, NONE, B), (30, NONE, 0)]  # punches
    s += [(8, NONE, A), (6, NONE, 0), (4, NONE, Z), (50, NONE, 0)]  # ground pound
    s += [(90, (56, 56), 0), (10, (56, 56), A), (60, (-40, 20), 0), (30, NONE, 0)]  # diagonal, into whatever is there
    s += [(120, (-56, -56), 0), (10, NONE, A), (40, NONE, 0)]
    s += [(60, UP, 0), (4, UP, A), (20, UP, A), (60, DOWN, 0), (40, NONE, 0)]
    if os.environ.get('TRAJ_NEST'):  # into the hub's tightest corner of walls, from the side
        s = [(20, NONE, 0), (60, DOWN, 0), (4, DOWN, A), (30, DOWN, 0), (40, LEFT, 0), (40, RIGHT, 0), (60, DOWN, 0)]
        s += [(4, DOWN, A), (30, DOWN, 0), (100, (56, -56), 0), (100, (-56, -56), 0), (6, DOWN, Z | A), (40, DOWN, 0)]
        s += [(4, DOWN, B), (40, DOWN, 0), (60, UP, 0), (60, DOWN, 0), (30, NONE, 0)]
    frames, previous = [], 0
    for count, stick, buttons in s:
        for i in range(count):
            frames.append((stick, buttons, buttons & ~previous))
            previous = buttons
    return frames


def adjust(raw):
    # adjust_analog_stick
    x = raw[0] - 6 if raw[0] >= 8 else raw[0] + 6 if raw[0] <= -8 else 0
    y = raw[1] - 6 if raw[1] >= 8 else raw[1] + 6 if raw[1] <= -8 else 0
    mag = math.sqrt(x * x + y * y)
    if mag > 64:
        x, y, mag = x * 64 / mag, y * 64 / mag, 64.0
    return x, y, mag


def j(t):
    return 0x08000000 | (t & 0x0fffffff) >> 2


def locate(raw, rom):
    words = rom[0xf5580:0xf5580 + 64]
    return raw.find(b''.join(words[i:i + 4][::-1] for i in range(0, 64, 4))) - 0x378800


def gen(state, out, rom_path, lua):
    data = open(state, 'rb').read()
    buf = bytearray(gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data)
    base = locate(buf, open(rom_path, 'rb').read())
    rd = lambda a: struct.unpack('<I', buf[base + (a & 0xffffff):base + (a & 0xffffff) + 4])[0]
    def wr(a, v):
        buf[base + (a & 0xffffff):base + (a & 0xffffff) + 4] = struct.pack('<I', v & 0xffffffff)
    frames = script()
    for k, v in enumerate(map(float, os.environ.get('TRAJ_START', '').split())):
        wr(MARIO + 0x3c + k * 4, struct.unpack('>I', struct.pack('>f', v))[0])
    start = [struct.unpack('>f', struct.pack('>I', rd(MARIO + 0x3c + k * 4)))[0] for k in range(3)]
    yaw = struct.unpack('>h', struct.pack('>H', rd(MARIO + 0x2c) & 0xffff))[0]
    print('start', [round(v) for v in start], yaw, 'action', hex(rd(MARIO + 0xc)))
    obj = rd(MARIO + 0x88)
    bhv = rd(obj + 0x20c)
    native = next(a + 4 for a in range(bhv, bhv + 64, 4) if rd(a) == 0x08000000 and rd(a + 4) == 0x0c000000) + 4
    update = rd(native)
    print('bhv_mario_update', hex(update))
    code = [
        0x3c088060,                # lui t0, 0x8060
        0x8d090ff0,                # lw t1, 0xff0(t0)
        0x292a0000 | len(frames),  # slti t2, t1, count
        0x11400000 | 25,           # beqz t2, done
        0x00095900,                # sll t3, t1, 4
        0x00096080,                # sll t4, t1, 2
        0x016c5820,                # add t3, t3, t4
        0x01685820,                # add t3, t3, t0
        0x3c0e8034,                # lui t6, 0x8034  (controller, with negative offsets)
        # lw t4, 0x1000+k(t3), then store to gControllers[0] and to [2], the copy dialogs read
        0x8d6c1000, 0xadccaf90, 0xadccafc8,
        0x8d6c1004, 0xadccaf94, 0xadccafcc,
        0x8d6c1008, 0xadccaf98, 0xadccafd0,
        0x8d6c100c, 0xadccaf9c, 0xadccafd4,
        0x8d6c1010, 0xadccafa0, 0xadccafd8,
        0x00096980,                # sll t5, t1, 6
        0x3c0f8070,                # lui t7, 0x8070
        0x01ed6820,                # add t5, t7, t5
        0x25290001,                # addiu t1, t1, 1
        0xad090ff0,                # sw t1, 0xff0(t0)
        0x3c0f8034,                # lui t7, 0x8034  (mario, with negative offsets)
        0x00000000,
        # done is patched below, after the log copy
    ]
    copy = [(MARIO + o, d) for o, d in ((0x0c, 0), (0x3c, 4), (0x40, 8), (0x44, 12), (0x4c, 16), (0x54, 20), (0x2c, 24))]
    copy += [(LAKITU + o, d) for o, d in ((0, 28), (4, 32), (8, 36), (12, 40), (16, 44), (20, 48))]
    for src, dst in copy:
        code += [0x8de80000 | ((src - 0x80340000) & 0xffff), 0xada80000 | dst]  # lw t0 / sw t0, dst(t5)
    # Stick direction follows the camera. Pin its yaw, so that camera differences don't reach the physics.
    if not os.environ.get('FREECAM'):
        code += [0x8df80000 | ((MARIO + 0x90 - 0x80340000) & 0xffff), 0x8f180024, 0xa7000002]  # lw t8, area / lw t8, camera / sh zero, yaw
    done = len(code)
    code += [j(update), 0]
    code[3] = 0x11400000 | (done - 4)
    for i, w in enumerate(code):
        wr(CODE + i * 4, w)
    wr(COUNT, 0)
    for i, (stick, down, pressed) in enumerate(frames):
        x, y, mag = adjust(stick)
        entry = (((stick[0] & 0xffff) << 16) | (stick[1] & 0xffff),
                 *(struct.unpack('>I', struct.pack('>f', v))[0] for v in (x, y, mag)),
                 (down << 16) | pressed)
        for k, w in enumerate(entry):
            wr(TABLE + i * 20 + k * 4, w)
    wr(native, CODE)
    open(out, 'wb').write(gzip.compress(bytes(buf)))
    with open(lua, 'w') as f:
        f.write('-- name: UJM Trajectory\n-- description: Test only. Generated by tests/traj.py.\nlocal F = {\n')
        for stick, down, pressed in frames:
            x, y, mag = adjust(stick)
            f.write(f'{{{stick[0]},{stick[1]},{x!r},{y!r},{mag!r},{down},{pressed}}},\n')
        f.write('''}
local t, n = 0, 0
local START = @START@
local AREA = @AREA@
local MOVE = @MOVE@
local wait = 0
local PIN = @PIN@
hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or m.action == ACT_UNINITIALIZED then return end
    if n == 0 and gNetworkPlayers[0].currLevelNum ~= START then return end
    if n == 0 and AREA ~= 0 and gNetworkPlayers[0].currAreaIndex ~= AREA then
        wait = wait + 1
        if wait == 60 then warp_to_level(START, AREA, 1); wait = 0 end
        return
    end
    t = t + 1
    if MOVE and t == 298 then
        m.pos.x, m.pos.y, m.pos.z = MOVE[1], MOVE[2], MOVE[3]
        m.vel.x, m.vel.y, m.vel.z, m.forwardVel = 0, 0, 0, 0
        m.faceAngle.y = MOVE[4]
        set_mario_action(m, ACT_IDLE, 0)
    end
    if t < 300 or n >= #F then return end
    n = n + 1
    local f, c = F[n], m.controller
    if PIN then m.area.camera.yaw = 0 end
    c.rawStickX, c.rawStickY, c.stickX, c.stickY, c.stickMag, c.buttonDown, c.buttonPressed = f[1], f[2], f[3], f[4], f[5], f[6], f[7]
    local w = collision_get_temp_wall_collision_data()
    w.x, w.y, w.z, w.offsetY, w.radius = m.pos.x, m.pos.y, m.pos.z, 60, 50
    find_wall_collisions(w)
    if w.numWalls > 4 then print("NESTWALLS", n - 1, w.numWalls) end
    local l = gLakituState
    print(string.format("TRAJ %d %x %.3f %.3f %.3f %.3f %.3f %d %.2f %.2f %.2f %.2f %.2f %.2f", n - 1, m.action, m.pos.x, m.pos.y, m.pos.z, m.vel.y, m.forwardVel, m.faceAngle.y, l.curFocus.x, l.curFocus.y, l.curFocus.z, l.curPos.x, l.curPos.y, l.curPos.z))
end)
'''.replace('@START@', sys.argv[6].split('a')[0]).replace('@AREA@', sys.argv[6].split('a')[1] if 'a' in sys.argv[6] else '0').replace('@MOVE@', 'nil' if os.environ.get('FREECAM') else '{%r, %r, %r, %d}' % (*start, yaw)).replace('@PIN@', 'false' if os.environ.get('FREECAM') else 'true'))
    print('frames', len(frames))


def cmp(out, rom_path, log):
    src = open(__file__.replace('traj.py', 'ramdump.py')).read().replace('\nmain()\n', '\n')
    g = {}
    exec(compile(src, 'ramdump', 'exec'), g)
    ram = g['rdram'](out, open(rom_path, 'rb').read())
    n = struct.unpack('>I', ram[COUNT & 0xffffff:(COUNT & 0xffffff) + 4])[0]
    emu = []
    for i in range(n):
        a = (LOG & 0xffffff) + i * 64
        act, x, y, z, vy, fv, face, *cam = struct.unpack('>IfffffI6f', ram[a:a + 52])
        emu.append((act, x, y, z, vy, fv, struct.unpack('>h', struct.pack('>H', face & 0xffff))[0], *cam))
    port = {}
    for line in open(log, errors='ignore'):
        p = line.split()
        if len(p) == 15 and p[0] == 'TRAJ':
            port[int(p[1])] = (int(p[2], 16), *map(float, p[3:8]), int(p[8]), *map(float, p[9:15]))
    print('frames emu', n, 'port', len(port))
    first, worst = None, 0
    for i in range(min(n, len(port))):
        e, q = emu[i], port[i]
        d = max(abs(e[k] - q[k]) for k in (1, 2, 3))
        worst = max(worst, d)
        if first is None and (e[0] != q[0] or d > 0.5 or abs(e[4] - q[4]) > 0.5 or abs(e[5] - q[5]) > 0.5):
            first = i
    print('largest position difference', round(worst, 2), 'first divergence', first)
    if first is not None:
        for i in range(max(0, first - 2), min(first + 3, n, len(port))):
            print(i, 'E', hex(emu[i][0]), [round(v, 2) for v in emu[i][1:7]])
            print(i, 'P', hex(port[i][0]), [round(v, 2) for v in port[i][1:7]])
    # The camera is still settling from its entry for the first frames.
    for i in range(60, min(n, len(port))):
        if max(abs(emu[i][k] - port[i][k]) for k in range(7, 13)) > 1:
            print('first camera difference at frame', i)
            for k in range(max(0, i - 2), min(i + 6, n)):
                print(k, 'E cam', [round(v, 1) for v in emu[k][7:]], 'mario', [round(v) for v in emu[k][1:4]])
                print(k, 'P cam', [round(v, 1) for v in port[k][7:]])
            break
    print('actions', len({e[0] for e in emu}), sorted(hex(a) for a in {e[0] for e in emu}))


if sys.argv[1] == 'gen':
    gen(*sys.argv[2:6])
else:
    cmp(*sys.argv[2:5])
