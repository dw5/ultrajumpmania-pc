#!/bin/bash
# Run once on the host, only for tools/play-emulator.sh: the emulator's keys don't work on Wayland.
# Lets mr64 use the desktop's X11 server. Programs in mr64 can then see input to other X11 apps.
# To undo: incus config device remove mr64 x11 && xhost -si:localuser:"$USER"
set -e
incus start mr64 2>/dev/null || true
incus exec mr64 -- bash -c 'mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix'
incus config device add mr64 x11 proxy bind=container connect=unix:/tmp/.X11-unix/X0 listen=unix:/tmp/.X11-unix/X0 uid=1000 gid=1000 mode=0700 security.uid=1000 security.gid=1000
xhost +si:localuser:"$USER"
