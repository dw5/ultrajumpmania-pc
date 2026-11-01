#!/bin/bash
# Screenshots the hack at spots: emu-at.sh <level> <outdir> "x y z yaw" ... from build/oracle/<level>.st
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEVEL=$1; OUT=$2; shift 2; mkdir -p "$OUT"; OUT=$(realpath "$OUT")
W=$ROOT/build/oracle/w$LEVEL
ROM="$ROOT/../Ultra Jump Mania - Simpleflip Island.z64"
pkill -f 'Xvfb :9'; sleep 1; Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 1
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
n=0
for s in "$@"; do
  n=$((n+1))
  python3 -I "$ROOT/tests/spots.py" "$ROOT/build/oracle/$LEVEL.st" "$OUT/s.st" "$ROM" $s
  S="$HOME/.local/share/mupen64plus/save"; mkdir -p "$S"; rm -f "${S:?}"/*.st0
  /usr/games/mupen64plus --configdir "$W" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio dummy $EMUPLUGINS "$W/level.z64" > "$OUT/emu$n.log" 2>&1 &
  E=$!; sleep 6
  N=$(ls -t "$HOME"/.local/share/mupen64plus/save 2>/dev/null | head -0); xdotool key F5; sleep 1; F=$(ls -t "$S"/*.st0 | head -1); cp "$OUT/s.st" "$F"; xdotool key F7; sleep ${HOLD:-7}; import -window root "$OUT/e$n.png"; kill $E; sleep 1
done
pkill -f 'Xvfb :9'; rm -f "$OUT/s.st"
