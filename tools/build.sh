#!/bin/bash
# Builds the engine and assembles the mod.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ROMS=$ROOT/..
ENGINE=$ROOT/third_party/sm64coopdx
SRC="$ROOT/third_party/ultra-jump-mania-mod/extracted/ultra jump mania"
OUT="$ROOT/build/ultra jump mania"
USERDIR=$HOME/.local/share/sm64coopdx

cp -n "$ROMS/Super Mario 64 (U) [!].z64" "$ENGINE/baserom.us.z64"
make -C "$ENGINE" -j"$(nproc)"

rm -rf "$OUT"; mkdir -p "$ROOT/build"; cp -r "$SRC" "$OUT"
python3 -I "$ROOT/tools/rom2tari.py" "$ROMS/Ultra Jump Mania - Simpleflip Island.z64" \
    "$ROMS/Super Mario 64 (U) [!].z64" "$ENGINE/data/dynos_mgr_builtin.cpp" "$OUT/actors/mario"

mkdir -p "$USERDIR/mods"
cp -n "$ROMS/Super Mario 64 (U) [!].z64" "$USERDIR/baserom.us.z64"
rm -rf "$USERDIR/mods/ultra jump mania"; cp -r "$OUT" "$USERDIR/mods/"
