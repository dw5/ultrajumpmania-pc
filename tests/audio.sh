#!/bin/bash
# Records the music of an area from the hack and the port with SDL's disk audio driver, then compares them.
# audio.sh <level> [seconds]  uses build/oracle/<level>.st. Level 16 starts in the hub, others warp there.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEVEL=$1; SECS=${2:-40}; OUT=$ROOT/build/oracle/audio; mkdir -p "$OUT"
W=$ROOT/build/oracle/w$LEVEL; ROM="$ROOT/../Ultra Jump Mania - Simpleflip Island.z64"
export LIBGL_ALWAYS_SOFTWARE=1 DISPLAY=:9 SDL_AUDIODRIVER=disk
CONF=$HOME/.local/share/sm64coopdx/sm64config.txt; M=$HOME/.local/share/sm64coopdx/mods; cp -p "$CONF" "$OUT/conf.bak"
cleanup() { pkill -x sm64coopdx; pkill mupen64plus; pkill -x Xvfb; rm -rf "$M/ujm-warp" "$M/ujm-audio"; cp -p "$OUT/conf.bak" "$CONF"; }
trap cleanup EXIT
trap 'exit 1' TERM INT
sed -i "s/^master_volume .*/master_volume ${MASTER:-127}/" "$CONF"
Xvfb :9 -screen 0 640x480x24 >/dev/null 2>&1 & sleep 2

S="$HOME/.local/share/mupen64plus/save"; mkdir -p "$S"; rm -f "${S:?}"/*.st0
SDL_DISKAUDIOFILE="$OUT/emu.raw" /usr/games/mupen64plus --configdir "$W" --datadir /usr/share/games/mupen64plus --nosaveoptions --noosd --resolution 640x480 --audio mupen64plus-audio-sdl "$W/level.z64" > "$OUT/emu.log" 2>&1 &
sleep 6; xdotool key F5; sleep 1; F=$(ls -t "$S"/*.st0 | head -1); cp "$ROOT/build/oracle/$LEVEL.st" "$F"; xdotool key F7; sleep 1
[ -n "$PAUSE" ] && { xdotool keydown space; sleep 0.3; xdotool keyup space; sleep 2; }
[ -n "$PAUSE" ] && import -window root "$OUT/emu-paused.png"
A=$(stat -c %s "$OUT/emu.raw"); sleep "$SECS"; tail -c +$((A + 1)) "$OUT/emu.raw" > "$OUT/emu.pcm"; import -window root "$OUT/emu-end.png"; pkill mupen64plus; sleep 1

cp -r "$ROOT/tests/ujm-audio" "$M/"
EN=(--enable-mod ujm-audio); if [ "$LEVEL" != 16 ]; then cp -r "$ROOT/tests/ujm-warp" "$M/"; sed -i "s/^local LEVEL = .*/local LEVEL = ${LEVEL%%a*}/" "$M/ujm-warp/main.lua"; EN+=(--enable-mod ujm-warp); fi
cd "$ROOT/third_party/sm64coopdx/build/us_pc"
SDL_DISKAUDIOFILE="$OUT/port.raw" ./sm64coopdx --windowed --width 640 --height 480 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Test --server 7777 --enable-mod "ultra jump mania" "${EN[@]}" > "$OUT/port.log" 2>&1 &
sleep 45; xdotool key comma; sleep 10; xdotool key comma; sleep 25
[ -n "$PAUSE" ] && { xdotool keydown space; sleep 0.3; xdotool keyup space; sleep 2; import -window root "$OUT/port-paused.png"; }
A=$(stat -c %s "$OUT/port.raw"); sleep "$SECS"; tail -c +$((A + 1)) "$OUT/port.raw" > "$OUT/port.pcm"; import -window root "$OUT/port-end.png"; pkill -x sm64coopdx
grep -iE "audio|freq|sample" "$OUT/emu.log" | head -5 | cut -c1-110
grep AUDIO "$OUT/port.log" | tail -2
python3 -I "$ROOT/tests/audio.py" "$OUT/emu.pcm" "$OUT/port.pcm"
