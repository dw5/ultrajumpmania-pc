#!/bin/bash
# Runs the port off-screen in LEVEL (default the hub) and AREA, and writes its object dump to build/oracle/<NAME>.port.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEVEL=${LEVEL:-16}
NAME=${NAME:-$LEVEL}
OUT=$ROOT/build/oracle; mkdir -p "$OUT"
M=$HOME/.local/share/sm64coopdx/mods; rm -rf "$M/ujm-dump" "$M/ujm-warp"; cp -r "$ROOT/tests/ujm-dump" "$M/"; sed -i "s/^local AREA = .*/local AREA = ${AREA:-0}/" "$M/ujm-dump/main.lua"
EN=(--enable-mod ujm-dump)
if [ "$LEVEL" != 16 ]; then cp -r "$ROOT/tests/ujm-warp" "$M/"; sed -i "s/^local LEVEL = .*/local LEVEL = $LEVEL/" "$M/ujm-warp/main.lua"; EN+=(--enable-mod ujm-warp); fi
pkill -f 'Xvfb :9'; pkill sm64coopdx; Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 2
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
timeout 90 ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" "${EN[@]}" > "$OUT/$NAME.log" 2>&1 &
sleep 45; xdotool key comma; sleep 10; xdotool key comma; sleep ${WAIT:-10}
import -window root "$OUT/$NAME.port.png"
pkill sm64coopdx; pkill -f 'Xvfb :9'; rm -rf "$M/ujm-dump" "$M/ujm-warp"
grep -a 'DUMP' "$OUT/$NAME.log" | sed 's/.*DUMP /DUMP /' > "$OUT/$NAME.port"
