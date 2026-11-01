#!/bin/bash
# Run on the host. Plays the original hack in mupen64plus in mr64, to compare with the port.
# Uses X11: on Wayland only Space reached the emulator. Run tools/setup-x11.sh once first.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$ROOT/build/mupen"
: > "$ROOT/build/mupen/InputAutoCfg.ini"
cat > "$ROOT/build/mupen/mupen64plus.cfg" <<'C'
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
Z Trig = "key(107)"
B Button = "key(44)"
A Button = "key(108)"
C Button R = "key(275)"
C Button L = "key(276)"
C Button D = "key(274)"
C Button U = "key(273)"
R Trig = "key(99)"
L Trig = "key(120)"
X Axis = "key(97,100)"
Y Axis = "key(119,115)"
C
incus start mr64 2>/dev/null
exec incus exec mr64 --cwd /home/dev/code/MR64/ultrajumpmania-pc -- su dev -c '
export DISPLAY=:0 SDL_VIDEODRIVER=x11 XDG_RUNTIME_DIR=/home/dev/rt PULSE_SERVER=unix:/home/dev/rt/pulse-native SDL_AUDIODRIVER=pulseaudio
exec /usr/games/mupen64plus --configdir build/mupen --datadir /usr/share/games/mupen64plus --nosaveoptions --windowed --resolution 960x720 "../Ultra Jump Mania - Simpleflip Island.z64"'
