#!/bin/bash
# Boots the hack in mupen64plus on a virtual display, enters a level and saves a state to
# build/oracle/<level>.st, to read the original's RAM with tests/ramdump.py. LEVEL picks the
# level through a patched copy of the ROM.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEVEL=${LEVEL:-16}
OUT=$ROOT/build/oracle; W=$OUT/w$LEVEL; rm -rf "$W"; mkdir -p "$W"
HACK="$ROOT/../Ultra Jump Mania - Simpleflip Island.z64"
: > "$W/InputAutoCfg.ini"
cat > "$W/mupen64plus.cfg" <<C
[Core]
SaveStatePath = "$W/"
SaveSRAMPath = "$W/"
SharedDataPath = "$W/"
[Input-SDL-Control1]
version = 2
mode = 0
device = -1
plugged = True
plugin = 2
mouse = False
AnalogDeadzone = "4096,4096"
AnalogPeak = "32768,32768"
Start = "key(32)"
A Button = "key(108)"
B Button = "key(44)"
Z Trig = "key(107)"
X Axis = "key(97,100)"
Y Axis = "key(119,115)"
C
python3 -I - "$HACK" "$W/level.z64" "$LEVEL" <<'P'
import sys
r = bytearray(open(sys.argv[1], 'rb').read())
for i in range(0x2a6000, 0x2ac000, 4):
    if r[i + 1] == 4 and r[i + 2:i + 4] == b'\0\x10' and r[i] == 0x13:
        r[i + 3] = int(sys.argv[3])
open(sys.argv[2], 'wb').write(r)
P
pkill -f 'Xvfb :9'; sleep 1
Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 &
sleep 1
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
/usr/games/mupen64plus --configdir "$W" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio dummy --sshotdir "$W" "$W/level.z64" > "$W/emu.log" 2>&1 &
EMU=$!
sleep 14; xdotool key space; sleep 3
tap() { xdotool keydown "$1"; sleep 0.2; xdotool keyup "$1"; }
tap l; sleep 2; tap l; sleep ${WAIT1:-9}
if [ -n "$ACT" ]; then tap l; sleep 8; fi
import -window root "$OUT/$LEVEL.png"
xdotool key F5; sleep 3
kill $EMU; pkill -f 'Xvfb :9'
f=$(ls -t "$HOME"/.local/share/mupen64plus/save/*.st0 | head -1); [ -f "$f" ] && mv "$f" "$OUT/$LEVEL.st"
