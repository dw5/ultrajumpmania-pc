#!/bin/bash
# Runs tests/ujm-wallscan in the port: wallscan.sh <level> <area>. Lists how many walls the player's wall checks can hit.
ROOT=$(cd "$(dirname "$0")/.." && pwd); OUT=$ROOT/build/oracle; LEVEL=$1; AREA=$2
U=$HOME/.local/share/sm64coopdx; M=$U/mods; CONF=$U/sm64config.txt; cp -p "$CONF" "$OUT/conf.bak"
cleanup() { pkill -x sm64coopdx; pkill -x Xvfb; rm -rf "$M/ujm-wallscan" "$M/ujm-warp"; cp -p "$OUT/conf.bak" "$CONF"; }
trap cleanup EXIT
trap 'exit 1' TERM INT
pkill -x sm64coopdx; pkill -x Xvfb; rm -rf "$M/ujm-wallscan" "$M/ujm-warp"; cp -r "$ROOT/tests/ujm-wallscan" "$M/"
sed -i "s/^local LEVEL = .*/local LEVEL = $LEVEL/; s/^local AREA = .*/local AREA = $AREA/" "$M/ujm-wallscan/main.lua"
EN=(--enable-mod ujm-wallscan --enable-mod "ultra jump mania")
if [ "$LEVEL" != 16 ]; then cp -r "$ROOT/tests/ujm-warp" "$M/"; sed -i "s/^local LEVEL = .*/local LEVEL = $LEVEL/" "$M/ujm-warp/main.lua"; EN+=(--enable-mod ujm-warp); fi
Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 2
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
stdbuf -oL ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 "${EN[@]}" > "$OUT/wallscan.log" 2>&1 &
sleep 45; xdotool key comma; sleep 10; xdotool key comma
for _ in $(seq 1 120); do grep -q SCANDONE "$OUT/wallscan.log" && break; sleep 10; done
grep -E "SCAN |WALK |CHECK" "$OUT/wallscan.log" | cut -c1-200
