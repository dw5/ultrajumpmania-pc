#!/bin/bash
# Free flies in the port off-screen and logs how far the camera stays from the player. Screenshots go to build/oracle/fly.
ROOT=$(cd "$(dirname "$0")/.." && pwd); OUT=$ROOT/build/oracle/fly; mkdir -p "$OUT"
U=$HOME/.local/share/sm64coopdx; M=$U/mods; CONF=$U/sm64config.txt; cp -p "$CONF" "$OUT/conf.bak"
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
cleanup() { pkill -x sm64coopdx; pkill -x Xvfb; rm -rf "$M/ujm-fly"; cp -p "$OUT/conf.bak" "$CONF"; }
trap cleanup EXIT
trap 'exit 1' TERM INT
Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 2
cp -r "$ROOT/tests/ujm-fly" "$M/"
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
stdbuf -oL ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" --enable-mod ujm-fly > "$OUT/port.log" 2>&1 &
sleep 25; xdotool keydown l; sleep 0.2; xdotool keyup l; sleep 25
import -window root "$OUT/z.png"; xdotool keydown Shift_L; sleep 0.2; xdotool keyup Shift_L; sleep 1
import -window root "$OUT/y.png"; xdotool keydown w; sleep 0.5; import -window root "$OUT/a.png"; sleep 0.5; import -window root "$OUT/b.png"; xdotool keyup w; sleep 2; import -window root "$OUT/c.png"
xdotool keydown d; sleep 1; xdotool keyup d; xdotool keydown l; sleep 1; xdotool keyup l; sleep 2; import -window root "$OUT/d.png"
grep "^FLY" "$OUT/port.log" | awk '{print $4}' | tr '\n' ' '; echo
cd "$OUT"; montage z.png y.png a.png b.png c.png d.png -tile 6x1 -geometry 160x120+1+1 sheet.png
