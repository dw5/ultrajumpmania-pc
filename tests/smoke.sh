#!/bin/bash
# Starts the game off-screen, walks forward and saves screenshots to build/shots.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$ROOT/build/shots; mkdir -p "$OUT"; rm -f "$OUT"/*
pkill Xvfb; Xvfb :9 -screen 0 1280x720x24 >/dev/null 2>&1 & sleep 2
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=disk SDL_DISKAUDIOFILE=/tmp/audio.raw
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
timeout 100 ./sm64coopdx --windowed --width 1280 --height 720 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" --enable-mod ujm-controls > /tmp/run.log 2>&1 &
GP=$!; sleep 45; import -window root "$OUT/idle.png"
xdotool key comma; sleep 1; xdotool keydown w; sleep 13; import -window root "$OUT/walk.png"; xdotool keyup w; xdotool keydown space; sleep 0.4; xdotool keyup space; sleep 2; import -window root "$OUT/pause.png"
kill -0 $GP && echo ALIVE || echo DEAD
kill $GP; wait $GP 2>/dev/null; pkill Xvfb
echo "errors: $(grep -c ERROR /tmp/run.log)"
