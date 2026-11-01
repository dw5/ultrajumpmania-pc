#!/bin/bash
# Puts the player on a star in the hack and the port, taps A, and captures what follows.
# star.sh <state> <level> "x y z yaw"  Writes build/oracle/star/{e,p}N.png and sheet.png.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ST=$1; LEVEL=$2; SPOT=$3; N=${N:-10}; GAP=${GAP:-4}; OUT=$ROOT/build/oracle/star; mkdir -p "$OUT"
W=$ROOT/build/oracle/w$ST; ROM="$ROOT/../Ultra Jump Mania - Simpleflip Island.z64"; U=$HOME/.local/share/sm64coopdx; M=$U/mods
SAVE=$U/sm64_save_file.bin; CONF=$U/sm64config.txt; cp -p "$SAVE" "$OUT/save.bak"; cp -p "$CONF" "$OUT/conf.bak"
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
S="$HOME/.local/share/mupen64plus/save"; mkdir -p "$S"
cleanup() { pkill -x sm64coopdx; pkill mupen64plus; pkill -x Xvfb; rm -rf "$M/ujm-spots" "$M/ujm-warp"; cp -p "$OUT/save.bak" "$SAVE"; cp -p "$OUT/conf.bak" "$CONF"; }
trap cleanup EXIT
trap 'exit 1' TERM INT
tap() { xdotool keydown "$1"; sleep 0.2; xdotool keyup "$1"; }
Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 2

python3 -I "$ROOT/tests/spots.py" "$ROOT/build/oracle/$ST.st" "$OUT/s.st" "$ROM" $SPOT
rm -f "${S:?}"/*.st0
/usr/games/mupen64plus --configdir "$W" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio dummy ${EMUOPTS:-} "$W/level.z64" > "$OUT/emu.log" 2>&1 &
sleep 6; xdotool key F5; sleep 1; F=$(ls -t "$S"/*.st0 | head -1); cp "$OUT/s.st" "$F"; xdotool key F7
for i in $(seq 1 "$N"); do sleep "$GAP"; import -window root "$OUT/e$i.png"; [ "$i" = "$QUIT" ] && { sleep 3; xdotool keydown s; sleep 0.12; xdotool keyup s; sleep 0.5; import -window root "$OUT/e$i.c.png"; }; tap l; done
xdotool key F5; sleep 2; cp "$F" "$OUT/emu-end.st"; pkill mupen64plus; sleep 1
python3 -I "$ROOT/tests/emu-end.py" "$OUT/emu-end.st" "$ROM"

cp -r "$ROOT/tests/ujm-spots" "$M/"; T="{${SPOT// /,},1},"
sed -i "s/^local SPOTS = .*/local SPOTS = {$T}/; s/^local LEVEL = .*/local LEVEL = $LEVEL/; s/^local AREA = .*/local AREA = ${AREA:-0}/" "$M/ujm-spots/main.lua"
[ -n "${WARP6:-}" ] && sed -i "s/^local WARP6 = .*/local WARP6 = true/" "$M/ujm-spots/main.lua"
cp -r "$ROOT/tests/ujm-warp" "$M/"; sed -i "s/^local LEVEL = .*/local LEVEL = $LEVEL/" "$M/ujm-warp/main.lua"
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
stdbuf -oL ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" --enable-mod ujm-spots --enable-mod ujm-warp > "$OUT/port.log" 2>&1 &
[ -n "${NOACT:-}" ] || { sleep 45; tap comma; sleep 10; tap comma; }
for t in $(seq 1 60); do grep -q "SPOT 1" "$OUT/port.log" && break; sleep 2; done
for i in $(seq 1 "$N"); do sleep "$GAP"; import -window root "$OUT/p$i.png"; [ "$i" = "${PQUIT:-}" ] && { xdotool keydown s; sleep 0.05; xdotool keyup s; sleep 0.5; import -window root "$OUT/p$i.c.png"; }; tap l; done
grep "END " "$OUT/port.log" | tail -1
cd "$OUT"; L=""; for i in $(seq 1 "$N"); do L="$L e$i.png p$i.png"; done; montage $L -tile 4x -geometry 240x180+1+1 sheet.png
