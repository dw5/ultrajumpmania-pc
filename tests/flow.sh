#!/bin/bash
# Shots of the boot, Select File, act select and pause screens in the hack and the port: flow.sh <outdir>.
# The port's save is moved aside for the run, so both start empty.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$1; mkdir -p "$OUT"; OUT=$(realpath "$OUT"); W=$ROOT/build/oracle/w16
tap() { xdotool keydown "$1"; sleep 0.2; xdotool keyup "$1"; }
shot() { import -window root "$OUT/$1.png"; }
pkill -f 'Xvfb :9'; sleep 1; Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 1
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
/usr/games/mupen64plus --configdir "$W" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio dummy "$W/level.z64" > "$OUT/emu.log" 2>&1 &
E=$!
sleep 6; shot e1boot; sleep 8; shot e2title; xdotool key space; sleep 3; shot e3file; tap l; sleep 2; tap l; sleep 9; shot e4hub
tap space; sleep 2; shot e5pause; tap space; sleep 2; kill $E; sleep 1
S=$HOME/.local/share/sm64coopdx/sm64_save_file.bin; [ -f "$S" ] && mv "$S" "$S.flowbak"
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" > "$OUT/port.log" 2>&1 &
P=$!
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do sleep 5; shot "t$i"; done
xdotool key space; sleep 3; shot p3file; tap l; sleep 2; shot p3b; tap l; sleep 9; shot p4hub
tap space; sleep 2; shot p5pause; tap space; sleep 1
kill $P; sleep 1; pkill -f 'Xvfb :9'; rm -f "$S"; [ -f "$S.flowbak" ] && mv "$S.flowbak" "$S"
cd "$OUT"; montage e1boot.png e2title.png e3file.png e4hub.png e5pause.png t[0-9]*.png p3file.png p3b.png p4hub.png p5pause.png -tile 6x4 -geometry 266x200+1+1 m.png
