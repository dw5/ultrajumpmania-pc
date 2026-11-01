#!/bin/bash
# Plays the same scripted inputs in the emulator (left) and the port (right) and
# records them side by side to build/sidebyside.mp4. Needs mupen64plus, ffmpeg, xdotool.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$ROOT/build/sidebyside; rm -rf "$OUT"; mkdir -p "$OUT"
HACK="$ROOT/../Ultra Jump Mania - Simpleflip Island.z64"
CFG=$OUT/mupen; mkdir -p "$CFG"
cat > "$CFG/InputAutoCfg.ini" <<'I'
I
cat > "$CFG/mupen64plus.cfg" <<'C'
[Input-SDL-Control1]
version = 2
mode = 0
device = -1
plugged = True
plugin = 2
mouse = False
AnalogDeadzone = "4096,4096"
AnalogPeak = "32768,32768"
Start = "key(13)"
Z Trig = "key(122)"
B Button = "key(306)"
A Button = "key(304)"
C Button R = "key(108)"
C Button L = "key(106)"
C Button D = "key(107)"
C Button U = "key(105)"
R Trig = "key(99)"
L Trig = "key(120)"
X Axis = "key(97,100)"
Y Axis = "key(119,115)"
C
# LEVEL=9 starts both in that level: the emulator on a patched copy of the ROM
# (its menu's start level), the port through the test-only warp mod.
ENABLE=()
if [ -n "$LEVEL" ]; then
    python3 -I - "$HACK" "$OUT/level.z64" "$LEVEL" <<'P'
import sys
r = bytearray(open(sys.argv[1], 'rb').read())
hits = [i for i in range(0x2a6000, 0x2ac000, 4) if r[i + 1] == 4 and r[i + 2:i + 4] == b'\0\x10' and r[i] == 0x13]
print('start level commands', [hex(i) for i in hits])
for i in hits:
    r[i + 3] = int(sys.argv[3])
open(sys.argv[2], 'wb').write(r)
P
    HACK=$OUT/level.z64
    U=$HOME/.local/share/sm64coopdx/mods/ujm-warp; rm -rf "$U"; cp -r "$ROOT/tests/ujm-warp" "$U"
    sed -i "s/^local LEVEL = .*/local LEVEL = $LEVEL/" "$U/main.lua"
    ENABLE=(--enable-mod ujm-warp)
fi
pkill Xvfb; sleep 1
Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 &
Xvfb :10 -screen 0 640x480x24 >/dev/null 2>&1 &
sleep 2
export LIBGL_ALWAYS_SOFTWARE=1

DISPLAY=:9 SDL_AUDIODRIVER=dummy /usr/games/mupen64plus --configdir "$CFG" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio dummy --sshotdir "$OUT" "$HACK" > "$OUT/emu.log" 2>&1 &
EMU=$!
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
DISPLAY=:10 SDL_AUDIODRIVER=dummy ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Tari --server 7777 --enable-mod "ultra jump mania" --enable-mod ujm-controls "${ENABLE[@]}" > "$OUT/port.log" 2>&1 &
PORT=$!
cd "$OUT"
ffmpeg -loglevel error -y -f x11grab -framerate 15 -video_size 640x480 -i :9 -f x11grab -framerate 15 -video_size 640x480 -i :10 \
    -filter_complex hstack -t "${DURATION:-90}" -pix_fmt yuv420p "$ROOT/build/sidebyside.mp4" &
FF=$!

emu()  { DISPLAY=:9  xdotool "$@"; }
port() { DISPLAY=:10 xdotool "$@"; }
both_hold() { emu keydown "$1"; port keydown "$2"; sleep "$3"; emu keyup "$1"; port keyup "$2"; }
tap_emu() { emu keydown "$1"; sleep 0.15; emu keyup "$1"; sleep "${2:-1}"; }
shot() { DISPLAY=:9 import -window root "$OUT/$1-emu.png"; DISPLAY=:10 import -window root "$OUT/$1-port.png"; }

# Logo, then file A in both.
tap_both() { emu keydown "$1"; port keydown "$2"; sleep 0.6; emu keyup "$1"; port keyup "$2"; sleep "$3"; }
sleep 12; shot 1-select
tap_both Return space 3; tap_both Shift_L l 3; tap_both Shift_L l 1; tap_both Shift_L l ${SPAWN_WAIT:-8}
shot 2-spawn
if [ -n "$LEVEL" ]; then sleep 8; shot 2b-actselect; tap_both Return l 30; shot 2c-level; fi
both_hold w w 4;           shot 3-walk
tap_both Shift_L l 1;      shot 4-jump
both_hold a a 2;           shot 5-left
both_hold d d 4;           shot 6-right
both_hold w w 6;           shot 7-run
tap_both Return space 2;   shot 8-pause
wait $FF
kill $EMU $PORT 2>/dev/null; pkill Xvfb; rm -rf "$HOME/.local/share/sm64coopdx/mods/ujm-warp"
ls "$OUT"/*.png | wc -l
