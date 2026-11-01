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

# Use the hack's sound banks and samples instead of vanilla's.
git -C "$ENGINE" checkout -- sound/sound_data_compressed.ctl sound/sound_data_compressed.tbl sound/sound_data.c
SIZE=$(python3 -I "$ROOT/tools/rom2sound.py" "$ROMS/Ultra Jump Mania - Simpleflip Island.z64" \
    "$ENGINE/sound/sound_data_compressed.ctl" "$ENGINE/sound/sound_data_compressed.tbl" \
    "$ENGINE/sound/sound_data_compressed.ctl" "$ENGINE/sound/sound_data_compressed.tbl" | tail -1)
sed -i "s/#define SAMPLES_SIZE .*/#define SAMPLES_SIZE $SIZE/" "$ENGINE/sound/sound_data.c"

# Use the hack's logo and show the boot splash.
git -C "$ENGINE" checkout -- levels/entry.c levels/intro/leveldata.c levels/intro/script.c levels/intro/geo.c levels/menu/script.c src/menu/intro_geo.c src/game/rendering_graph_node.c src/engine/level_script.c
python3 -I "$ROOT/tools/rom2intro.py" "$ROMS/Ultra Jump Mania - Simpleflip Island.z64" "$ENGINE"

# Single player, and the hack's HUD.
git -C "$ENGINE" checkout -- src/engine/extended_bounds.h src/engine/surface_collision.h levels/ending/script.c src/game/hud.c lang/English.ini src/pc/configfile.c src/game/behaviors/blue_coin.inc.c src/game/skybox.c src/pc/djui/djui_chat_box.c src/pc/djui/djui_chat_message.c src/pc/djui/djui_interactable.c src/menu/ingame_text.c src/menu/star_select.c src/game/behaviors/texscroll.inc.c src/pc/controller/controller_keyboard.c src/menu/file_select.c src/pc/gfx/gfx_sdl.c src/pc/gfx/gfx_pc.c src/game/mario_actions_cutscene.c src/game/mario.c src/game/ingame_menu.c src/audio/external.c src/engine/surface_collision.c src/game/mario_actions_stationary.c src/game/mario_step.c src/game/mario_actions_moving.c src/game/interaction.c src/game/level_update.c src/game/behaviors/spawn_star.inc.c src/game/behaviors/whomp.inc.c src/game/shadow.c src/game/camera.c levels/level_defines.h src/engine/surface_load.c src/pc/network/network.c src/game/hardcoded.c
python3 -I "$ROOT/tools/patch_engine.py" "$ENGINE" "$ROMS/Ultra Jump Mania - Simpleflip Island.z64"
make -C "$ENGINE" -j"$(nproc)"

rm -rf "$OUT"; mkdir -p "$ROOT/build"; cp -r "$SRC" "$OUT"
python3 -I "$ROOT/tools/fixactors.py" "$OUT/actors" "$OUT/actors"
# The castle level uses two engine painting lists the level compiler can't see,
# so it fails to compile and the vanilla castle would be used.
sed -i '/inside_castle_seg7_dl_070234C0\|inside_castle_seg7_dl_07023520/d' "$OUT/levels/castle_inside/areas/1/geo.inc.c"
python3 -I "$ROOT/tools/scrolls.py" "$OUT/levels" "$OUT/moving_textures.lua"
python3 -I "$ROOT/tools/seqvolumes.py" "$OUT"
# The ROM's exports replace the mod's versions of these models.
rm -rf "$OUT/actors/star" "$OUT/actors/transparent_star"
python3 -I "$ROOT/tools/rom2tari.py" "$ROMS/Ultra Jump Mania - Simpleflip Island.z64" \
    "$ROMS/Super Mario 64 (U) [!].z64" "$ENGINE/data/dynos_mgr_builtin.cpp" "$OUT/actors"
python3 -I "$ROOT/tools/rom2tex.py" "$ROMS/Ultra Jump Mania - Simpleflip Island.z64" \
    "$ROMS/Super Mario 64 (U) [!].z64" "$ENGINE" "$OUT/textures" | tail -1

mkdir -p "$USERDIR/mods"
# Full output like the N64, unless the volume was changed from the old default.
[ -f "$USERDIR/sm64config.txt" ] && sed -i 's/^master_volume 80$/master_volume 127/' "$USERDIR/sm64config.txt"
cp -n "$ROMS/Super Mario 64 (U) [!].z64" "$USERDIR/baserom.us.z64"
rm -rf "$USERDIR/mods/ultra jump mania" "$USERDIR/mods/ujm-controls"
cp -r "$OUT" "$ROOT/mods/ujm-controls" "$USERDIR/mods/"
