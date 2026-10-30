#!/bin/bash
# Downloads the engine and the mod into third_party/.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ENGINE=$ROOT/third_party/sm64coopdx
MOD=$ROOT/third_party/ultra-jump-mania-mod
MOD_MD5=e23a02c0e7a63e771a80796b7dc6ad1a

mkdir -p "$ROOT/third_party"
[ -d "$ENGINE" ] || git clone -q --depth 1 --branch v1.5.1 https://github.com/coop-deluxe/sm64coopdx.git "$ENGINE"

mkdir -p "$MOD"
[ -f "$MOD/ultra_jump_mania.zip" ] || curl -sSL -m 180 https://gamebanana.com/dl/1108963 -o "$MOD/ultra_jump_mania.zip"
echo "$MOD_MD5  $MOD/ultra_jump_mania.zip" | md5sum -c --quiet
[ -d "$MOD/extracted" ] || { mkdir -p "$MOD/extracted"; unzip -qo "$MOD/ultra_jump_mania.zip" -d "$MOD/extracted"; }
