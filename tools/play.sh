#!/bin/bash
# Run on the host. Starts the game in mr64 on the host's Wayland display.
incus start mr64 2>/dev/null
exec incus exec mr64 --env UJM_KEYLOG="${UJM_KEYLOG:-}" --cwd /home/dev/code/MR64/ultrajumpmania-pc/third_party/sm64coopdx/build/us_pc -- su dev -c '
export XDG_RUNTIME_DIR=/home/dev/rt WAYLAND_DISPLAY=wayland-0 SDL_VIDEODRIVER=wayland PULSE_SERVER=unix:/home/dev/rt/pulse-native SDL_AUDIODRIVER=pulseaudio
[ -n "$UJM_KEYLOG" ] || unset UJM_KEYLOG
exec ./sm64coopdx --windowed --width 1280 --height 720 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Tari --server 7777 --enable-mod "ultra jump mania" --enable-mod ujm-controls'
