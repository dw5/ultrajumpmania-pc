#!/bin/bash
# Enters a level through a warp in the hack: emu-enter.sh <name> "x y z". Saves build/oracle/<name>.st.
# Starts from build/oracle/${SRC:-16}.st.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEVEL=$1; AT=$2; OUT=$ROOT/build/oracle; W=$OUT/w16
ROM="$ROOT/../Ultra Jump Mania - Simpleflip Island.z64"
python3 -I "$ROOT/tests/spots.py" "$OUT/${SRC:-16}.st" "$OUT/enter.st" "$ROM" $AT 0
pkill -f 'Xvfb :9'; sleep 1; Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 1
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
S="$HOME/.local/share/mupen64plus/save"; rm -f "${S:?}"/*.st0
/usr/games/mupen64plus --configdir "$W" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio dummy "$W/level.z64" > "$OUT/enter.log" 2>&1 &
E=$!; sleep 6; xdotool key F5; sleep 1; F=$(ls -t "$S"/*.st0 | head -1); cp "$OUT/enter.st" "$F"; xdotool key F7; sleep 6
import -window root "$OUT/$LEVEL.a.png"
xdotool keydown l; sleep 0.2; xdotool keyup l; sleep 9
import -window root "$OUT/$LEVEL.png"
xdotool key F5; sleep 2; cp "$F" "$OUT/$LEVEL.st"; kill $E; pkill -f 'Xvfb :9'
