#!/bin/bash
# Starts the game directly, without a container.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT/third_party/sm64coopdx/build/us_pc" || exit 1
exec ./sm64coopdx --windowed --width 1280 --height 720 --skip-update-check --no-discord --skip-intro --hide-loading-screen --playername Tari --server 7777 --enable-mod "ultra jump mania"
