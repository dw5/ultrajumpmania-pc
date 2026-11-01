#!/bin/bash
# Collects level 17's red coins in the hack and the port, then its star. Writes build/oracle/star/sheet.png.
ROOT=$(cd "$(dirname "$0")/.." && pwd); OUT=$ROOT/build/oracle/star; mkdir -p "$OUT"; cd "$ROOT"
ROM="$ROOT/../Ultra Jump Mania - Simpleflip Island.z64"; W=$ROOT/build/oracle/w17; U=$HOME/.local/share/sm64coopdx; M=$U/mods
SAVE=$U/sm64_save_file.bin; CONF=$U/sm64config.txt; cp -p "$SAVE" "$OUT/save.bak"; cp -p "$CONF" "$OUT/conf.bak"
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
S="$HOME/.local/share/mupen64plus/save"; mkdir -p "$S"
cleanup() { pkill -x sm64coopdx; pkill mupen64plus; pkill -x Xvfb; rm -rf "$M/ujm-spots" "$M/ujm-warp"; cp -p "$OUT/save.bak" "$SAVE"; cp -p "$OUT/conf.bak" "$CONF"; }
trap cleanup EXIT
trap 'exit 1' TERM INT
tap() { xdotool keydown "$1"; sleep 0.2; xdotool keyup "$1"; }
COINS=("4270 597 -9358" "329 1906 -7730" "-1774 -22 -8511" "-3589 -22 -9535" "288 1363 -6831" "787 158 -5229" "103 15 -893" "384 58 5138")
STAR="4597 634 -9350"
Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 2
rm -f "${S:?}"/*.st0
/usr/games/mupen64plus --configdir "$W" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio dummy "$W/level.z64" > "$OUT/emu.log" 2>&1 &
sleep 6; xdotool key F5; sleep 1; F=$(ls -t "$S"/*.st0 | head -1); cp "$ROOT/build/oracle/17.st" "$OUT/s.st"
for c in "${COINS[@]}" "$STAR"; do
    HEAL=1 python3 -I tests/spots.py "$OUT/s.st" "$OUT/s2.st" "$ROM" $c 0; cp "$OUT/s2.st" "$F"; xdotool key F7; sleep 0.25; xdotool key F5; sleep 0.7; cp "$F" "$OUT/s.st"
done
for i in 1 2 3 4 5 6; do sleep 4; import -window root "$OUT/e$i.png"; tap l; done
xdotool key F5; sleep 2; cp "$F" "$OUT/emu-end.st"; pkill mupen64plus; sleep 1
python3 -I tests/emu-end.py "$OUT/emu-end.st" "$ROM"

cp -r tests/ujm-spots tests/ujm-warp "$M/"; T=""; for c in "${COINS[@]}" "$STAR"; do T="$T{${c// /,},0,1},"; done
sed -i "s/^local SPOTS = .*/local SPOTS = {$T}/; s/^local LEVEL = .*/local LEVEL = 17/; s/^local STEP = .*/local STEP = 8/" "$M/ujm-spots/main.lua"
sed -i "s/^local LEVEL = .*/local LEVEL = 17/" "$M/ujm-warp/main.lua"
cd third_party/sm64coopdx/build/us_pc
stdbuf -oL ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" --enable-mod ujm-spots --enable-mod ujm-warp > "$OUT/port.log" 2>&1 &
sleep 25; tap l
for t in $(seq 1 80); do grep -q "SPOT 9" "$OUT/port.log" && break; sleep 2; done
for i in 1 2 3 4 5 6; do sleep 4; import -window root "$OUT/p$i.png"; tap l; done
grep -E "^(SPOT 9|END)" "$OUT/port.log" | tail -2
cd "$OUT"; L=""; for i in 1 2 3 4 5 6; do L="$L e$i.png p$i.png"; done; montage $L -tile 4x -geometry 240x180+1+1 sheet.png
