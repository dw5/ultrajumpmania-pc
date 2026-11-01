#!/bin/bash
# Screenshots the port at spots: port-at.sh <level> <outdir> "x y z yaw [1]" ... (1: at exactly y, not on the floor). Writes floor heights to <outdir>/spots.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEVEL=$1; OUT=$2; shift 2; mkdir -p "$OUT"; OUT=$(realpath "$OUT")
CONF=$HOME/.local/share/sm64coopdx/sm64config.txt; cp -p "$CONF" "$OUT/conf.bak"
M=$HOME/.local/share/sm64coopdx/mods
cleanup() { pkill -x sm64coopdx; pkill -f 'Xvfb :9'; rm -rf "$M/ujm-spots" "$M/ujm-warp"; cp -p "$OUT/conf.bak" "$CONF"; }
trap cleanup EXIT
trap 'exit 1' TERM INT
M=$HOME/.local/share/sm64coopdx/mods; rm -rf "$M/ujm-spots" "$M/ujm-warp"; cp -r "$ROOT/tests/ujm-spots" "$M/"
T=""; for s in "$@"; do T="$T{${s// /,}},"; done
sed -i "s/^local SPOTS = .*/local SPOTS = {$T}/; s/^local LEVEL = .*/local LEVEL = $LEVEL/" "$M/ujm-spots/main.lua"
[ -n "$FREEZESCROLL" ] && sed -i "s/^local FREEZE = .*/local FREEZE = {$FREEZESCROLL}/" "$M/ujm-spots/main.lua"
EN=(--enable-mod ujm-spots)
if [ "$LEVEL" != 16 ]; then cp -r "$ROOT/tests/ujm-warp" "$M/"; sed -i "s/^local LEVEL = .*/local LEVEL = $LEVEL/" "$M/ujm-warp/main.lua"; EN+=(--enable-mod ujm-warp); fi
pkill -f 'Xvfb :9'; pkill sm64coopdx; Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 2
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
stdbuf -oL ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" "${EN[@]}" > "$OUT/port.log" 2>&1 &
P=$!; sleep 45; DISPLAY=:9 xdotool key comma; sleep 10; DISPLAY=:9 xdotool key comma
tail -f "$OUT/port.log" --pid=$P 2>/dev/null | while read -r l; do case "$l" in *SPOT*) n=$(echo "$l" | sed 's/.*SPOT[^0-9]*\([0-9]*\).*/\1/'); sleep ${DELAY:-2.5}; DISPLAY=:9 import -window root "$OUT/p$n.png"; echo "$l" | sed 's/.*SPOT/SPOT/' >> "$OUT/spots"; [ "$n" = "$COUNT" ] && kill $P;; esac; done
