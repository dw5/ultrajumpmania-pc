#!/bin/bash
# Frame-exact physics comparison in Simpleflip Island between the hack and the port. See traj.py.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$ROOT/build/oracle; W=$OUT/w16; ROM="$ROOT/../Ultra Jump Mania - Simpleflip Island.z64"; SRC=${SRC:-9}
python3 -I "$ROOT/tests/traj.py" gen "$OUT/$SRC.st" "$OUT/traj.in.st" "$ROM" "$ROOT/tests/ujm-traj/main.lua" "${SRC}" || exit 1
pkill -f 'Xvfb :9'; sleep 1; Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 1
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
S="$HOME/.local/share/mupen64plus/save"; rm -f "${S:?}"/*.st0
/usr/games/mupen64plus --configdir "$W" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio dummy "$W/level.z64" > "$OUT/traj.emu.log" 2>&1 &
E=$!; sleep 6; xdotool key F5; sleep 1; F=$(ls -t "$S"/*.st0 | head -1); cp "$OUT/traj.in.st" "$F"; xdotool key F7
sleep ${EMUWAIT:-45}; import -window root "$OUT/traj.emu.png"; xdotool key F5; sleep 3; cp "$F" "$OUT/traj.out.st"; kill $E; sleep 1
WARP="--enable-mod ujm-warp"; [ "$SRC" = 16 ] && WARP=""
M=$HOME/.local/share/sm64coopdx/mods; rm -rf "$M/ujm-traj" "$M/ujm-warp"; cp -r "$ROOT/tests/ujm-traj" "$ROOT/tests/ujm-warp" "$M/"
sed -i "s/^local LEVEL = .*/local LEVEL = ${SRC%%a*}/" "$M/ujm-warp/main.lua"
SAVE=$HOME/.local/share/sm64coopdx/sm64_save_file.bin; CONF=$HOME/.local/share/sm64coopdx/sm64config.txt; cp -p "$SAVE" "$OUT/save.bak"; cp -p "$CONF" "$OUT/conf.bak"
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
stdbuf -oL timeout 200 ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" --enable-mod ujm-traj ${WARP} > "$OUT/traj.port.log" 2>&1 &
sleep 45; xdotool key comma; sleep 10; xdotool key comma; sleep 120; import -window root "$OUT/traj.port.png"; pkill sm64coopdx; sleep 1
pkill -f 'Xvfb :9'; rm -rf "$M/ujm-traj" "$M/ujm-warp"; cp -p "$OUT/save.bak" "$SAVE"; cp -p "$OUT/conf.bak" "$CONF"
python3 -I "$ROOT/tests/traj.py" cmp "$OUT/traj.out.st" "$ROM" "$OUT/traj.port.log"
