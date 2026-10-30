#!/bin/bash
# Run on the host, once. Shares the GPU, Wayland display and audio with mr64.
# Undo with: incus config device remove mr64 gpu wayland pulse
set -e
incus exec mr64 -- bash -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libpulse0 libwayland-client0 libwayland-cursor0 libwayland-egl1 libxkbcommon0 libdecor-0-0 libegl1; install -d -o dev -g dev -m 700 /home/dev/rt'
# Debian 13's own Mesa does not recognise Panther Lake GPUs.
incus exec mr64 -- bash -c 'echo "deb http://deb.debian.org/debian trixie-backports main" > /etc/apt/sources.list.d/backports.list; apt-get update -qq; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq -t trixie-backports libgl1-mesa-dri libegl-mesa0 libglx-mesa0 mesa-libgallium libgbm1 mesa-vulkan-drivers'
incus config device add mr64 gpu gpu mode=0666
incus config device add mr64 wayland proxy bind=container connect=unix:/run/user/1000/wayland-0 listen=unix:/home/dev/rt/wayland-0 uid=1000 gid=1000 mode=0700 security.uid=1000 security.gid=1000
incus config device add mr64 pulse proxy bind=container connect=unix:/run/user/1000/pulse/native listen=unix:/home/dev/rt/pulse-native uid=1000 gid=1000 mode=0700 security.uid=1000 security.gid=1000
