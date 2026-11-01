#!/usr/bin/env python3
# Single-player and HUD changes to the engine. The port has no use for co-op,
# and the hack always shows the health meter and has no lives counter.
import os
import re
import struct
import sys

SPEAKERS = 0xede58

PATCHES = {
    'src/game/hud.c': [
        ('if (hudDisplayFlags & HUD_DISPLAY_FLAG_LIVES && showHud) {', 'if (FALSE) {'),
        # The hack pins the meter at this position and skips its animations.
        ('if (gPlayerCameraState->action & ACT_FLAG_SWIMMING) {', 'if (TRUE) {'),
        ('void render_hud_power_meter(void) {\n',
         'void render_hud_power_meter(void) {\n'
         '    sPowerMeterHUD.animation = POWER_METER_VISIBLE;\n'
         '    sPowerMeterHUD.x = 45;\n    sPowerMeterHUD.y = 210;\n    sPowerMeterPrevY = 210;\n'),
    ],
    # The hack's scroll objects: X is the vertex count, Z the speed, and Y holds the
    # vertex field (top nibble), mode (next nibble) and cycle (low byte).
    'src/game/behaviors/texscroll.inc.c': [
        ('''    u32 vtxIndex = (u32) o->oBehParams;
''', '''    u32 vtxIndex = (u32) o->oBehParams;

    u16 packed = (u16) (s32) o->oPosY;
    u16 field = packed >> 12;
    speed = (s16) o->oPosZ;
    vertCount = (u16) o->oPosX;
    bhv = field >= 8 ? (field == 8 ? SCROLL_UV_X : SCROLL_UV_Y) : field / 2;
    scrollType = (packed >> 8) & 0xF;
    cycle = packed & 0xFF;
    offset = 0;
'''),
    ],
    # Free fly: Left Shift (the L button) toggles the engine's debug free move, which
    # is otherwise only in development builds. A rises, Z falls, B slows down.
    'src/game/mario_actions_cutscene.c': [
        ('#ifndef DEVELOPMENT\n    if (m->pos[1] <= m->waterLevel - 100) {', '#if 0\n    if (m->pos[1] <= m->waterLevel - 100) {'),
        # Landing needs a floor under Tari: without one the engine stops updating her.
        ('gPlayer1Controller->buttonPressed == L_TRIG && m->marioObj->oTimer > 10',
         'gPlayer1Controller->buttonPressed & L_TRIG && m->marioObj->oTimer > 10 && m->floor != NULL'),
        # Fly from a private position: some objects push the player away even when
        # intangible, and those pushes would otherwise hold Tari in place.
        ('    vec3f_copy(pos, m->pos);\n\n    if (gPlayer1Controller->buttonDown & A_BUTTON) {',
         '    static Vec3f sFlyPos;\n    if (m->marioObj->oTimer <= 1) { vec3f_copy(sFlyPos, m->pos); }\n    vec3f_copy(pos, sFlyPos);\n\n    if (gPlayer1Controller->buttonDown & A_BUTTON) {'),
        ('    vec3f_copy(m->pos, pos);\n\n    m->faceAngle[1] = m->intendedYaw;',
         '    vec3f_copy(m->pos, pos);\n    vec3f_copy(sFlyPos, pos);\n\n    m->faceAngle[1] = m->intendedYaw;'),
        ('    struct WallCollisionData wcd = { 0 };\n    resolve_and_return_wall_collisions_data(pos, 60.0f, 50.0f, &wcd);\n',
         '    // Stay inside the world. No wall collisions, so walls can be flown through.\n'
         '    pos[0] = clamp(pos[0], -32000.0f, 32000.0f);\n'
         '    pos[1] = clamp(pos[1], -32000.0f, 32000.0f);\n'
         '    pos[2] = clamp(pos[2], -32000.0f, 32000.0f);\n'),
    ],
    'src/game/mario.c': [
        ('    /* Developer stuff */\n',
         '    if (m->playerIndex == 0 && m->controller->buttonPressed & L_TRIG && !(m->action & ACT_FLAG_INTANGIBLE)) {\n'
         '        set_mario_action(m, ACT_DEBUG_FREE_MOVE, 0);\n'
         '        m->marioObj->oTimer = 0;\n'
         '    }\n\n'
         '    /* Developer stuff */\n'),
    ],
    # The mod writes the glows' render mode as 3356510680. Compiling its levels saturated that
    # to the signed maximum, which means dither and hard-edge cutout instead of a soft blend.
    'src/pc/gfx/gfx_pc.c': [
        ('    struct CombineMode* cm = &rdp.combine_mode;\n\n    cm->use_alpha ',
         '    if (rdp.other_mode_l == 0x7FFFFFFF) { rdp.other_mode_l = 3356510680u; }\n\n'
         '    struct CombineMode* cm = &rdp.combine_mode;\n\n    cm->use_alpha '),
    ],
    # Text input left on makes desktops treat the game as a text field: KDE's hold-for-accents
    # then takes held keys, which reach the game as single taps. Input boxes turn it back on.
    'src/pc/gfx/gfx_sdl.c': [
        ('    ctx = SDL_GL_CreateContext(wnd);\n', '    ctx = SDL_GL_CreateContext(wnd);\n    SDL_StopTextInput();\n'),
    ],
    # With UJM_KEYLOG=1, also log what reaches the Select File hand.
    'src/menu/file_select.c': [
        ('    // Stop cursor from going offscreen\n',
         '    if (getenv("UJM_KEYLOG") && (rawStickX || rawStickY)) { fprintf(stderr, "hand stick %d %d pos %.0f %.0f\\n", rawStickX, rawStickY, sCursorPos[0], sCursorPos[1]); }\n\n'
         '    // Stop cursor from going offscreen\n'),
    ],
    # UJM_KEYLOG=1 logs what the game receives, for diagnosing input problems.
    'src/pc/controller/controller_keyboard.c': [
        ('bool keyboard_on_key_down(int scancode) {\n',
         'bool keyboard_on_key_down(int scancode) {\n'
         '    if (getenv("UJM_KEYLOG")) { fprintf(stderr, "key down %#x mapped %#x\\n", scancode, keyboard_map_scancode(scancode)); }\n'),
        ('bool keyboard_on_key_up(int scancode) {\n',
         'bool keyboard_on_key_up(int scancode) {\n'
         '    if (getenv("UJM_KEYLOG")) { fprintf(stderr, "key up %#x\\n", scancode); }\n'),
        ('void keyboard_on_all_keys_up(void) {\n',
         'void keyboard_on_all_keys_up(void) {\n'
         '    if (getenv("UJM_KEYLOG")) { fprintf(stderr, "all keys up\\n"); }\n'),
        ('#include <stdbool.h>\n', '#include <stdbool.h>\n#include <stdio.h>\n#include <stdlib.h>\n'),
        # A tap can start and end between two reads, which lost it. Keep it for one read.
        ('static int keyboard_buttons_down;\n', 'static int keyboard_buttons_down;\nstatic int keyboard_buttons_tapped;\n'),
        ('    keyboard_buttons_down |= mapped;\n', '    keyboard_buttons_down |= mapped;\n    keyboard_buttons_tapped |= mapped;\n'),
        ('    keyboard_buttons_down = 0;\n', '    keyboard_buttons_down = 0;\n    keyboard_buttons_tapped = 0;\n'),
        ('''    pad->button |= keyboard_buttons_down;
    const u32 xstick = keyboard_buttons_down & STICK_XMASK;
    const u32 ystick = keyboard_buttons_down & STICK_YMASK;
''', '''    const int buttons = keyboard_buttons_down | keyboard_buttons_tapped;
    keyboard_buttons_tapped = 0;
    pad->button |= buttons;
    const u32 xstick = buttons & STICK_XMASK;
    const u32 ystick = buttons & STICK_YMASK;
'''),
    ],
    # The act select's co-op head icon and "Join" text.
    'src/menu/star_select.c': [
        ('gServerSettings.enablePlayersInLevelDisplay', 'FALSE'),
        ('gServerSettings.enablePlayersInLevelDisplay', 'FALSE'),
        # The hack turns the wooden course sign into the eye, with no number on it.
        ('print_hud_lut_string(HUD_LUT_GLOBAL, 152, 158, courseNum);', ''),
        ('print_hud_lut_string(HUD_LUT_GLOBAL, 143, 158, courseNum);', ''),
    ],
    'src/pc/djui/djui_chat_box.c': [
        ('void djui_chat_box_toggle(void) {\n', 'void djui_chat_box_toggle(void) {\n    return;\n'),
    ],
    'src/pc/djui/djui_chat_message.c': [
        ('void djui_chat_message_create(const char* message) {\n',
         'void djui_chat_message_create(const char* message) {\n    return;\n'),
    ],
    'src/game/ingame_menu.c': [
        # The hack's dialog box is blue, and signs use it too instead of the white one.
        ('gDPSetEnvColor(gDisplayListHead++, 0, 0, 0, 150);', 'gDPSetEnvColor(gDisplayListHead++, 0x12, 0x26, 0x87, 150);'),
        ('gDialogBoxType = DIALOG_TYPE_ZOOM;', 'gDialogBoxType = DIALOG_TYPE_ROTATE;'),
    ],
    'src/pc/djui/djui_interactable.c': [
        ('!gDjuiInMainMenu && gNetworkType != NT_NONE) {\n                if (gServerSettings.enablePlayerList)',
         'FALSE) {\n                if (gServerSettings.enablePlayerList)'),
    ],
}

engine, hack = sys.argv[1:3]
rom = open(hack, 'rb').read()

# Code changes the hack makes to vanilla, found by diffing its ROM. Offsets are in the hack ROM.
def level_table(rom_offset):
    return ', '.join(map(str, rom[rom_offset:rom_offset + 39]))

for name, edits in {
    'src/engine/surface_collision.c': [
        # 0xfe2f8, 0xfe4a0: the highest floor wins, not the first found. The hub's stairs depend on it.
        ('    // set pheight to lowest value\n    if (gLevelValues.fixCollisionBugs) {', '    // set pheight to lowest value\n    if (TRUE) {'),
        ('if (gLevelValues.fixCollisionBugs && (height < *pheight)) {', 'if (height < *pheight) {'),
        ('        floor = surf;\n\n        if (!gLevelValues.fixCollisionBugs) {\n            break;\n        }\n', '        floor = surf;\n'),
    ],
    'src/game/mario_actions_stationary.c': [
        # 0x1a758: standing on a steep floor doesn't push the player off.
        ('if (m->floor && m->floor->normal.y < 0.29237169f) {\n        return mario_push_off_steep_floor(m, ACT_FREEFALL, 0);', 'if (FALSE) {\n        return mario_push_off_steep_floor(m, ACT_FREEFALL, 0);'),
    ],
    'src/game/mario_step.c': [
        # 0x1148a: a slightly wider angle counts as hitting a wall head on in the air.
        ('if (wallDYaw < -0x6000 || wallDYaw > 0x6000) {', 'if (wallDYaw < -0x5F00 || wallDYaw >= 0x5F00) {'),
        ('if (wallDYaw < -0x6000 || wallDYaw > 0x6000) {', 'if (wallDYaw < -0x5F00 || wallDYaw >= 0x5F00) {'),
    ],
    'src/game/mario_actions_moving.c': [
        # 0x23352: B also rolls out of a slide kick.
        ('if (m->input & INPUT_A_PRESSED) {\n        queue_rumble_data_mario(m, 5, 80);\n        return set_jumping_action(m, ACT_FORWARD_ROLLOUT, 0);',
         'if (m->input & (INPUT_A_PRESSED | INPUT_B_PRESSED)) {\n        queue_rumble_data_mario(m, 5, 80);\n        return set_jumping_action(m, ACT_FORWARD_ROLLOUT, 0);'),
    ],
    'src/game/interaction.c': [
        # 0xa951: grabbing below a pole's base starts at its base.
        ('marioObj->oMarioPolePos = m->pos[1] - o->oPosY;\n\n            if (lowSpeed) {', 'marioObj->oMarioPolePos = MAX(m->pos[1] - o->oPosY, 0.0f);\n\n            if (lowSpeed) {'),
    ],
    'src/game/level_update.c': [
        # 0x5b10, 0x5b98: no game over.
        ('if (m->numLives <= 0) {\n        sDelayedWarpOp = WARP_OP_GAME_OVER;\n    } else {', 'if (FALSE) {\n        sDelayedWarpOp = WARP_OP_GAME_OVER;\n    } else {'),
        ('if (m->numLives <= 0) {\n                    sDelayedWarpOp = WARP_OP_GAME_OVER;\n                }\n                sDelayedWarpTimer = 48;', 'sDelayedWarpTimer = 48;'),
        # 0x6f3b, 0x6f50: a table in the hack's code says which levels have an act select.
        ('if (gCurrCourseNum > COURSE_STAGES_MAX || warpCheckpointActive) {\n        return 0;\n    }',
         'static const u8 sActSelectLevels[] = { ' + level_table(0x1202ec0) + ' };\n'
         '    if (gCurrCourseNum < 1 || warpCheckpointActive || gCurrLevelNum >= (s16) ARRAY_COUNT(sActSelectLevels) || sActSelectLevels[gCurrLevelNum] != 1) {\n        return 0;\n    }'),
    ],
    'src/game/mario_actions_cutscene.c': [
        # 0x122b0: no dialogs for reaching a star count.
        ('if (!gBehaviorValues.ShowStarMilestones) { return 0; }', 'return 0;'),
    ],
    'src/game/behaviors/spawn_star.inc.c': [
        # 0xad8af
        ('if (o->oTimer == 30) {\n                o->oAction = 2;', 'if (o->oTimer == 29) {\n                o->oAction = 2;'),
    ],
    'src/game/behaviors/whomp.inc.c': [
        # 0x81dae: a smaller King Whomp.
        ('cur_obj_scale(2.0f);\n        if (o->oSubAction == 0) {', 'cur_obj_scale(1.4921875f);\n        if (o->oSubAction == 0) {'),
    ],
    'src/game/shadow.c': [
        # 0x88b5c: shadows sit above the floor.
        ('return -(s.floorNormalX * vtxX + s.floorNormalZ * vtxZ + s.floorOriginOffset) / s.floorNormalY;',
         'return -(s.floorNormalX * vtxX + s.floorNormalZ * vtxZ + s.floorOriginOffset) / s.floorNormalY + 2.0f * s.floorNormalY;'),
    ],
    'src/game/rendering_graph_node.c': [
        # 0x38528-0x385c8: objects stay visible further past the screen edge.
        ('s16 halfFov = (gCurGraphNodeCamFrustum->fov / 2.0f + 1.0f) * 32768.0f / 180.0f + 0.5f;', 's16 halfFov = (gCurGraphNodeCamFrustum->fov / 2.0f + 1.0f) * 49152.0f / 180.0f + 0.5f;'),
        ('hScreenEdge *= GFX_DIMENSIONS_ASPECT_RATIO;', 'hScreenEdge *= GFX_DIMENSIONS_ASPECT_RATIO * 1.671875f;'),
        # 0xe8e9d, 0xe8edd: the render layer table.
        ('G_RM_AA_ZB_OPA_INTER,', 'G_RM_AA_ZB_XLU_DECAL,'),
        ('G_RM_AA_ZB_OPA_INTER2,', 'G_RM_AA_ZB_XLU_DECAL2,'),
    ],
    'src/game/camera.c': [
        # 0x41ad9: a table in the hack's code says which levels use the course camera settings.
        ('camera_course_processing(c);\n        stub_camera_3(c);',
         'static const u8 sCourseCameraLevels[] = { ' + level_table(0x1202e50) + ' };\n'
         '        if (gCurrLevelNum < (s16) ARRAY_COUNT(sCourseCameraLevels) && sCourseCameraLevels[gCurrLevelNum] == 1) {\n            camera_course_processing(c);\n        }\n        stub_camera_3(c);'),
        # 0x4ac10: any wall can turn the camera, whatever its height.
        ('&& (is_mario_behind_surface(c, wall) == TRUE)\n                    // Also check if the wall is tall enough to cover Mario\n                    && (is_surf_within_bounding_box(wall, -1.f, 150.f, -1.f) == FALSE)) {',
         '&& (is_mario_behind_surface(c, wall) == TRUE)) {'),
    ],
    'levels/level_defines.h': [
        # 0xee0db, 0xee0f0: echo per area.
        ('LEVEL_BOB,              COURSE_BOB,      bob,              generic,  15000,    0x08, 0x08, 0x08,', 'LEVEL_BOB,              COURSE_BOB,      bob,              generic,  15000,    0x00, 0x00, 0x18,'),
        ('castle_grounds,   outside,  25000,    0x08, 0x08, 0x08,', 'castle_grounds,   outside,  25000,    0x0c, 0x08, 0x08,'),
        ('LEVEL_BITDW,            COURSE_BITDW,    bitdw,            sky,      16000,    0x28, 0x28, 0x28,', 'LEVEL_BITDW,            COURSE_BITDW,    bitdw,            sky,      16000,    0x00, 0x28, 0x28,'),
    ],
}.items():
    PATCHES.setdefault(name, []).extend(edits)
PATCHES['src/engine/surface_load.c'] = [
    # 0xffa28: the hack keeps collision at a quarter of the scale, to reach +-32768. Its positions
    # stay full scale, so it behaves like vertices rounded down to 4 and a wider wall range.
    ('    // (v2 - v1) x (v3 - v2)\n    nx = (y2 - y1)',
     '    x1 = (x1 >> 2) << 2; y1 = (y1 >> 2) << 2; z1 = (z1 >> 2) << 2;\n'
     '    x2 = (x2 >> 2) << 2; y2 = (y2 >> 2) << 2; z2 = (z2 >> 2) << 2;\n'
     '    x3 = (x3 >> 2) << 2; y3 = (y3 >> 2) << 2; z3 = (z3 >> 2) << 2;\n\n'
     '    // (v2 - v1) x (v3 - v2)\n    nx = (y2 - y1)'),
    ('surface->lowerY = minY - 5;\n    surface->upperY = maxY + 5;', 'surface->lowerY = minY - 20;\n    surface->upperY = maxY + 20;'),
]
PATCHES['src/engine/surface_collision.c'].extend([
    # 0xfe021, 0xfe6bd: floors and ceilings are looked up at a position rounded down to 4.
    ('    x = (s16) posX;\n    y = (s16) posY;\n    z = (s16) posZ;\n    *pceil = NULL;', '    x = ((s16) posX >> 2) << 2;\n    y = (s16) posY;\n    z = ((s16) posZ >> 2) << 2;\n    *pceil = NULL;'),
    ('    s16 x = (s16) xPos;\n    s16 y = (s16) yPos;\n    s16 z = (s16) zPos;\n\n    *pfloor = NULL;', '    s16 x = ((s16) xPos >> 2) << 2;\n    s16 y = (s16) yPos;\n    s16 z = ((s16) zPos >> 2) << 2;\n\n    *pfloor = NULL;'),
])
# Co-op defaults that differ from the game.
PATCHES['src/pc/network/network.c'] = [
    ('gServerSettings.bubbleDeath = configBubbleDeath;', 'gServerSettings.bubbleDeath = FALSE;'),
    ('gServerSettings.nametags = configNametags;', 'gServerSettings.nametags = FALSE;'),
    ('gServerSettings.bouncyLevelBounds = configBouncyLevelBounds;', 'gServerSettings.bouncyLevelBounds = BOUNCY_LEVEL_BOUNDS_OFF;'),
    ('gServerSettings.stayInLevelAfterStar = configStayInLevelAfterStar;', 'gServerSettings.stayInLevelAfterStar = STAR_LEAVE_LEVEL;'),
    ('gServerSettings.pauseAnywhere = configPauseAnywhere;', 'gServerSettings.pauseAnywhere = FALSE;'),
]
PATCHES['src/game/hardcoded.c'] = [
    ('.fixInvalidShellRides             = TRUE,', '.fixInvalidShellRides             = FALSE,'),
]
PATCHES['src/game/camera.c'].append(
    # 0x3f330: no automatic turn in the radial camera.
    ('camera_approach_s16_symmetric_bool(&yaw, yawGoal, yawVel);', 'camera_approach_s16_symmetric_bool(&yaw, yawGoal, 0);'))
PATCHES['src/game/level_update.c'].extend([
    # 0x6d90: the castle music plays on a new file too.
    ('gNeverEnteredCastle = !save_file_exists(gCurrSaveFileNum - 1) && (gServerSettings.skipIntro == 0);\n    if (gNetworkType == NT_NONE) { gNeverEnteredCastle = true; }', 'gNeverEnteredCastle = false;'),
    ('gNeverEnteredCastle = !save_file_exists(gCurrSaveFileNum - 1) && (gServerSettings.skipIntro == 0);\n    if (gNetworkType == NT_NONE) { gNeverEnteredCastle = true; }', 'gNeverEnteredCastle = false;'),
])
PATCHES['src/audio/external.c'] = [
    # 0xdc0b8: a fade back doesn't reset the music to its default volume.
    ('gSequencePlayers[SEQ_PLAYER_LEVEL].volume =\n                sBackgroundMusicDefaultVolume[sCurrentBackgroundMusicSeqId] / 127.0f;\n', ''),
]
PATCHES['src/game/ingame_menu.c'].append(
    # 0x957a8: dialog text isn't clipped at the screen border.
    ('gDPSetScissor(gDisplayListHead++, G_SC_NON_INTERLACE, 2, 2, SCREEN_WIDTH - BORDER_HEIGHT/2, SCREEN_HEIGHT - BORDER_HEIGHT/2);', 'gDPSetScissor(gDisplayListHead++, G_SC_NON_INTERLACE, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);'))
PATCHES['src/game/ingame_menu.c'].append(
    # 0x98118: no extra life at 150 coins.
    ('gCourseCompleteCoins == 50 || gCourseCompleteCoins == 100 || gCourseCompleteCoins == 150', 'gCourseCompleteCoins == 50 || gCourseCompleteCoins == 100'))

# The hack rewrites menu strings (TARI A...). The engine reads them from the vanilla ROM.
path = os.path.join(engine, 'src/menu/ingame_text.c')
src = open(path).read()
for m in list(re.finditer(r'ROM_ASSET_LOAD_DIALOG\((\w+), (0x[0-9a-f]+), (\d+), (0x[0-9a-f]+), (\d+)\);\n', src)):
    # A physical size above the string's own means a compressed block: those few are
    # single glyphs, so they stay loaded from the vanilla ROM.
    if m[3] != m[5]:
        continue
    data = rom[int(m[2], 16) + int(m[4], 16):int(m[2], 16) + int(m[4], 16) + int(m[5])]
    src = src.replace(m[0], '')
    src = re.sub(rf'(u8 {m[1]}\[\w+\] = ){{ 0xFF }};', rf'\1{{ {", ".join(map(str, data))} }};', src)
open(path, 'w').write(src)

# The hack reassigns dialog voices. Vanilla's Bowser voice also starts the Koopa message
# music, which the hack's locked door dialog must not play.
path = os.path.join(engine, 'src/audio/external.c')
src = open(path).read()
table = re.search(r'u8 sDialogSpeaker\[\] = \{(.*?)\n\};', src, re.S)
count = len(re.findall(r'\bDS_\w+|\b_\b', re.sub(r'/\*.*?\*/|//.*', '', table[1])))
src = src.replace(table[1], '\n    ' + ', '.join(map(str, rom[SPEAKERS:SPEAKERS + count])))
open(path, 'w').write(src)

# The hack keeps the vanilla camera. sm64coopdx would swap in its romhack camera, and the
# mod would turn off the course camera settings.
PATCHES['src/game/camera.c'] += [
    ('static u8 update_romhack_camera_override(struct Camera *c) {\n', 'static u8 update_romhack_camera_override(struct Camera *c) {\n    return FALSE;\n'),
    ('void camera_set_use_course_specific_settings(u8 enable) {\n', 'void camera_set_use_course_specific_settings(u8 enable) {\n    return;\n'),
]

# sm64coopdx resets the render state after every object on every layer. The hack's levels rely
# on it carrying over: area 3's doorway shading is only drawn because culling stays off.
PATCHES.setdefault('src/game/rendering_graph_node.c', []).append(
    ('    geo_append_display_list_to_all_layers(obj_sanitize_gfx);\n', ''))

# sm64coopdx centres the Select File hand. The N64 starts it on the last played file.
PATCHES['src/menu/file_select.c'].append(('    sCursorPos[0] = 0;\n    sCursorPos[1] = 0;\n', ''))

# Like the N64: far objects are hidden and models switch detail levels with distance.
PATCHES['src/game/hardcoded.c'] += [
    ('.InfiniteRenderDistance   = TRUE,', '.InfiniteRenderDistance   = FALSE,'),
    ('.ProcessLODs              = FALSE,', '.ProcessLODs              = TRUE,'),
]

# The pause screen's co-op options hint. R still opens the options.
PATCHES['lang/English.ini'] = [('R_BUTTON = "[R] Button - Options"', 'R_BUTTON = " "')]

# 0xfd434: the hack clamps the wall radius after scaling it to 1/4, so the limit is 800.
PATCHES['src/game/hardcoded.c'].append(('.wallMaxRadius                    = 200.0f,', '.wallMaxRadius                    = 800.0f,'))

# The hack's surfaces are stored at 1/4 scale. Its collision code allows for that, but these camera
# reads were left alone, so they see a quarter of the offset and the camera behaves accordingly.
PATCHES['src/game/camera.c'] += [
    ('        oo = floor->originOffset;\n', '        oo = floor->originOffset / 4.f;\n'),
    ('            originOffset = wall->originOffset;\n', '            originOffset = wall->originOffset / 4.f;\n'),
    # At 1/4 scale these products can't overflow. At full scale, huge triangles would.
    ('f32 normX = (surf->vertex2[1] - surf->vertex1[1]) * (surf->vertex3[2] - surf->vertex2[2]) -', 'f32 normX = (f32) (surf->vertex2[1] - surf->vertex1[1]) * (surf->vertex3[2] - surf->vertex2[2]) - (f32)'),
    ('f32 normY = (surf->vertex2[2] - surf->vertex1[2]) * (surf->vertex3[0] - surf->vertex2[0]) -', 'f32 normY = (f32) (surf->vertex2[2] - surf->vertex1[2]) * (surf->vertex3[0] - surf->vertex2[0]) - (f32)'),
    ('f32 normZ = (surf->vertex2[0] - surf->vertex1[0]) * (surf->vertex3[1] - surf->vertex2[1]) -', 'f32 normZ = (f32) (surf->vertex2[0] - surf->vertex1[0]) * (surf->vertex3[1] - surf->vertex2[1]) - (f32)'),
]
PATCHES['src/engine/surface_load.c'] += [
    ('nx = (y2 - y1) * (z3 - z2) - (z2 - z1) * (y3 - y2);', 'nx = (s64) (y2 - y1) * (z3 - z2) - (s64) (z2 - z1) * (y3 - y2);'),
    ('ny = (z2 - z1) * (x3 - x2) - (x2 - x1) * (z3 - z2);', 'ny = (s64) (z2 - z1) * (x3 - x2) - (s64) (x2 - x1) * (z3 - z2);'),
    ('nz = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2);', 'nz = (s64) (x2 - x1) * (y3 - y2) - (s64) (y2 - y1) * (x3 - x2);'),
]

# sm64coopdx floats numbers over stars and blue coin switches. The hack has none.
PATCHES['src/game/behaviors/spawn_star.inc.c'] = [('void spawn_star_number(void) {\n', 'void spawn_star_number(void) {\n    return;\n')]
PATCHES['src/game/behaviors/blue_coin.inc.c'] = [('struct Object *blueCoinNumber = spawn_object(o, MODEL_NUMBER, bhvBlueCoinNumber);', 'struct Object *blueCoinNumber = NULL;')]

# The hack swaps segment 0x0A for its own sky in two levels, keeping background 5 in their geo.
# The engine picks skyboxes by background alone, so tell those levels apart here.
SKYBOXES = (0x1369990, 0x1428eb0)
out = 'ALIGNED8 static const u8 sUjmSkyTiles[2][64][2048] = {'
for base in SKYBOXES:
    out += '{' + ','.join('{' + ','.join(map(str, rom[base + t * 2048:base + (t + 1) * 2048])) + '}' for t in range(64)) + '},\n'
out += '};\nstatic const u8 sUjmSkyList[2][80] = {'
for base in SKYBOXES:
    words = struct.unpack('>80I', rom[base + 0x20000:base + 0x20000 + 320])
    out += '{' + ','.join(str((w & 0xffffff) // 2048) for w in words) + '},\n'
open(os.path.join(engine, 'src/game/ujm_skybox.h'), 'w').write(out + '};\n')
PATCHES['src/game/skybox.c'] = [
    ('SkyboxTexture *sSkyboxTextures[10] = {', '#include "level_table.h"\n#include "ujm_skybox.h"\n\nSkyboxTexture *sSkyboxTextures[10] = {'),
    ('            f32 r = gSkyboxColor[0] / 255.0f;\n',
     '            if (background == 5 && (gCurrLevelNum == LEVEL_BOB || gCurrLevelNum == LEVEL_BITDW)) {\n'
     '                s32 sky = gCurrLevelNum == LEVEL_BITDW;\n'
     '                texture = (const Texture *) sUjmSkyTiles[sky][sUjmSkyList[sky][tileIndex]];\n'
     '            }\n\n'
     '            f32 r = gSkyboxColor[0] / 255.0f;\n'),
]

# 0x8ad20, 0xdfcd8: the skybox matrix has w = 0.75, which zooms the sky by 4/3 about the screen centre.
PATCHES['src/game/skybox.c'].append(
    ('        guOrtho(mtx, left, right, bottom, top, 0.0f, 3.0f, 1.0f);\n',
     '        extern void guOrthoF(float mf[4][4], float l, float r, float b, float t, float n, float f, float scale);\n'
     '        Mat4 ortho;\n        guOrthoF(ortho, left, right, bottom, top, 0.0f, 3.0f, 1.0f);\n'
     '        ortho[3][3] = 0.75f;\n        mtxf_to_mtx(mtx, ortho);\n'))
# 0xf2dd0
PATCHES['src/game/hardcoded.c'].append(('.KingWhompStarPos             = {   180.0f,  3880.0f,', '.KingWhompStarPos             = {   180.0f,  3872.0f,'))

# sm64coopdx turns the whole game down by default.
PATCHES['src/pc/configfile.c'] = [('unsigned int configMasterVolume                   = 80;', 'unsigned int configMasterVolume                   = MAX_VOLUME;')]

# sm64coopdx forces its own paused volume and mute behaviour on music. The hack's sequences set their own.
PATCHES['src/audio/external.c'].append(('    if (player == SEQ_PLAYER_LEVEL && sCurrentBackgroundMusicSeqId != 0xff) {\n        struct SequencePlayer *seqPlayer = &gSequencePlayers[player];\n        f32 maxVolume', '    if (FALSE) {\n        struct SequencePlayer *seqPlayer = &gSequencePlayers[player];\n        f32 maxVolume'))

# sm64coopdx adds EXIT TO CASTLE to the pause menu. The hack has vanilla's three options.
PATCHES['src/game/ingame_menu.c'] += [
    ('handle_menu_scrolling(MENU_SCROLL_VERTICAL, index, 1, 4);\n\n    gSPDisplayList(gDisplayListHead++, dl_ia_text_begin);\n    gDPSetEnvColor(gDisplayListHead++, 255, 255, 255, gDialogTextAlpha);\n\n    print_generic_string(x + 10, y - 2, textContinue);',
     'handle_menu_scrolling(MENU_SCROLL_VERTICAL, index, 1, 3);\n\n    gSPDisplayList(gDisplayListHead++, dl_ia_text_begin);\n    gDPSetEnvColor(gDisplayListHead++, 255, 255, 255, gDialogTextAlpha);\n\n    print_generic_string(x + 10, y - 2, textContinue);'),
    ('    print_generic_string(x + 10, y - 32, TEXT_EXIT_TO_CASTLE);\n\n    if (index[0] != 4) {\n        print_generic_string(x + 10, y - 47, textCameraAngleR);',
     '\n    if (index[0] != 3) {\n        print_generic_string(x + 10, y - 33, textCameraAngleR);'),
    ('render_pause_camera_options(x - 42, y - 57, &gDialogCameraAngleIndex, 110);', 'render_pause_camera_options(x - 42, y - 42, &gDialogCameraAngleIndex, 110);'),
    ('if (gDialogLineNum == 2 || gDialogLineNum == 3) {\n                        smlua_call_event_hooks', 'if (gDialogLineNum == 2) {\n                        smlua_call_event_hooks'),
    ('if (gDialogLineNum == 2 || gDialogLineNum == 3) {\n                            num = gDialogLineNum;', 'if (gDialogLineNum == 2) {\n                            num = gDialogLineNum;'),
]

# sm64coopdx removes SAVE & QUIT from the save prompt. The hack has vanilla's three options.
PATCHES['src/game/ingame_menu.c'] += [
    ('//#define TXT_SAVEQUIT_Y 20\n', '#define TXT_SAVEQUIT_Y 20\n'),
    ('#define TXT_CONTNOSAVE_Y 20\n', '#define TXT_CONTNOSAVE_Y 40\n'),
    ('    //u8 textSaveAndQuit[] = { TEXT_SAVE_AND_QUIT };\n', '    INGAME_TEXT_COPY(textSaveAndQuit, TEXT_SAVE_AND_QUIT);\n'),
    ('handle_menu_scrolling(MENU_SCROLL_VERTICAL, index, 1, 2); // decreased', 'handle_menu_scrolling(MENU_SCROLL_VERTICAL, index, 1, 3); // decreased'),
    ('    //print_generic_string(TXT_SAVEOPTIONS_X, y - TXT_SAVEQUIT_Y, textSaveAndQuit);\n', '    print_generic_string(TXT_SAVEOPTIONS_X, y - TXT_SAVEQUIT_Y, textSaveAndQuit);\n'),
]
PATCHES.setdefault('src/game/mario_actions_cutscene.c', []).extend([
    ('if (gSaveOptSelectIndex == SAVE_OPT_SAVE_AND_CONTINUE /*|| ', 'if (gSaveOptSelectIndex == SAVE_OPT_SAVE_AND_CONTINUE || gSaveOptSelectIndex == 2 /*|| '),
    ('            /*if (gSaveOptSelectIndex == SAVE_OPT_SAVE_AND_QUIT) {\n', '            if (gSaveOptSelectIndex == 2) {\n                fade_into_special_warp(-2, 0);\n                return;\n            }\n            /*if (gSaveOptSelectIndex == SAVE_OPT_SAVE_AND_QUIT) {\n'),
])

# sm64coopdx leaves the end screen after ten seconds. The hack stays on it, as vanilla does.
PATCHES['levels/ending/script.c'] = [
    ('const LevelScript level_ending_entry[] = {', 'static const LevelScript script_ending_stay[] = {\n    SLEEP(/*frames*/ 1),\n    JUMP(script_ending_stay),\n};\n\nconst LevelScript level_ending_entry[] = {'),
    ('    SLEEP_BEFORE_EXIT(/*frames*/ 30 * 10),\n', '    JUMP(script_ending_stay),\n    SLEEP_BEFORE_EXIT(/*frames*/ 30 * 10),\n'),
]

# sm64coopdx only shows CONGRATULATIONS and the key exit for a Bowser key. The hack's level 17 star gets them too, as in vanilla.
PATCHES.setdefault('src/game/ingame_menu.c', []).append(
    ('gLastCompletedCourseNum == COURSE_BITFS) && gLastCollectedStarOrKey == 1) {', 'gLastCompletedCourseNum == COURSE_BITFS)) {'))
PATCHES.setdefault('src/game/mario_actions_cutscene.c', []).append(
    ('(gLastCompletedCourseNum == COURSE_BITDW || gLastCompletedCourseNum == COURSE_BITFS)\n                    && gLastCollectedStarOrKey == 1) {', '(gLastCompletedCourseNum == COURSE_BITDW || gLastCompletedCourseNum == COURSE_BITFS)) {'))
# The mod writes the double quotes as these, which the engine doesn't know and drops.
PATCHES['src/game/level_info.c'] = [
    ('    SM64_CHAR("<<",  0xF5, false), // double quote open\n', '    SM64_CHAR("<<",  0xF5, false), // double quote open\n    SM64_CHAR("『",  0xF5, false),\n    SM64_CHAR("』",  0xF6, false),\n'),
]

# Free fly is faster than the camera's smoothing can follow, so the camera moves along with the player. Not in the hack.
PATCHES['src/game/camera.c'].append(
    ('    gCamera = c;\n    update_camera_hud_status(c);\n',
     '    gCamera = c;\n'
     '    static Vec3f sFlyLast;\n'
     '    static u8 sFlying = FALSE;\n'
     '    if (gMarioStates[0].action == ACT_DEBUG_FREE_MOVE) {\n'
     '        if (sFlying) {\n'
     '            f32 *moved[] = { c->pos, c->focus, gLakituState.curPos, gLakituState.curFocus, gLakituState.goalPos, gLakituState.goalFocus, gLakituState.pos, gLakituState.focus };\n'
     '            for (u32 i = 0; i < ARRAY_COUNT(moved); i++) {\n'
     '                for (u32 k = 0; k < 3; k++) { moved[i][k] += gMarioStates[0].pos[k] - sFlyLast[k]; }\n'
     '            }\n'
     '        }\n'
     '        vec3f_copy(sFlyLast, gMarioStates[0].pos);\n'
     '        sFlying = TRUE;\n'
     '    } else {\n'
     '        sFlying = FALSE;\n'
     '    }\n'
     '    update_camera_hud_status(c);\n'))

# 0xfdc30 and others: the hack's collision grid has 1024-unit cells and a 50-unit margin at 1/4 scale,
# so 4096 and 200 at full scale. The camera's wide wall checks see which walls those include.
PATCHES['src/engine/extended_bounds.h'] = [
    ('#define LEVEL_BOUNDARY_MAX 0x8000L\n    #define CELL_SIZE          0x400', '#define LEVEL_BOUNDARY_MAX 0x8000L\n    #define CELL_SIZE          0x1000'),
]
PATCHES['src/engine/surface_load.c'] += [
    ('if (coord % CELL_SIZE < 50) {', 'if (coord % CELL_SIZE < 200) {'),
    ('if (coord % CELL_SIZE > CELL_SIZE - 50) {', 'if (coord % CELL_SIZE > CELL_SIZE - 200) {'),
]

# sm64coopdx sets knockback speed when the action starts, for player attacks. In the hack each step does, as in vanilla.
PATCHES.setdefault('src/game/mario_actions_airborne.c', []).append(
    ('    stepResult = perform_air_step(m, 0);\n    switch (stepResult) {\n        case AIR_STEP_NONE:\n            set_character_animation(m, animation);\n            break;\n\n        case AIR_STEP_LANDED:\n            if (m->action == ACT_SOFT_BONK) {', '    mario_set_forward_vel(m, speed);\n\n    stepResult = perform_air_step(m, 0);\n    switch (stepResult) {\n        case AIR_STEP_NONE:\n            set_character_animation(m, animation);\n            break;\n\n        case AIR_STEP_LANDED:\n            if (m->action == ACT_SOFT_BONK) {'))
PATCHES.setdefault('src/game/mario.c', []).extend([
    ('            if (!(actionArg & PVP_ATTACK_KNOCKBACK_ACTION_ARG)) {\n                mario_set_forward_vel(m, -16.0f);\n            }\n', ''),
    ('            if (!(actionArg & PVP_ATTACK_KNOCKBACK_ACTION_ARG)) {\n                mario_set_forward_vel(m, 16.0f);\n            }\n', ''),
    ('            if (!(actionArg & PVP_ATTACK_KNOCKBACK_ACTION_ARG)) {\n                mario_set_forward_vel(m, m->forwardVel); // needed to update velocities\n            }\n', ''),
])

# 0x45614: the hack does this test at 1/4 scale in integers. Near huge triangles, full-scale rounding can pick the other side.
PATCHES['src/game/camera.c'] += [
    ('    f32 dirX = surf->vertex1[0] - pos[0];\n    f32 dirY = surf->vertex1[1] - pos[1];\n    f32 dirZ = surf->vertex1[2] - pos[2];\n',
     '    s32 ax = surf->vertex1[0] / 4, ay = surf->vertex1[1] / 4, az = surf->vertex1[2] / 4;\n'
     '    s32 bx = surf->vertex2[0] / 4, by = surf->vertex2[1] / 4, bz = surf->vertex2[2] / 4;\n'
     '    s32 cx = surf->vertex3[0] / 4, cy = surf->vertex3[1] / 4, cz = surf->vertex3[2] / 4;\n'
     '    normX = (f32) ((by - ay) * (cz - bz) - (bz - az) * (cy - by));\n'
     '    normY = (f32) ((bz - az) * (cx - bx) - (bx - ax) * (cz - bz));\n'
     '    normZ = (f32) ((bx - ax) * (cy - by) - (by - ay) * (cx - bx));\n'
     '    f32 dirX = ax - pos[0] / 4.f;\n    f32 dirY = ay - pos[1] / 4.f;\n    f32 dirZ = az - pos[2] / 4.f;\n'),
]

# The original removes the limit of four walls. Walls past the fourth run over the caller's stack: in
# rotate_camera_around_walls the seventh replaces its camera position pointer with a surface, read as floats, and the
# eighth its avoid yaw pointer. The list is longer here, so only those two effects need reproducing.
PATCHES['src/engine/surface_collision.h'] = [
    ('struct Surface *walls[4];', 'struct Surface *walls[32];'),
]
PATCHES['src/engine/surface_collision.c'].append(
    ('        if (data->numWalls < 4) {\n', '        if (data->numWalls < 32) {\n'),
)
PATCHES['src/game/camera.c'] += [
    ('s32 rotate_camera_around_walls(struct Camera *c, Vec3f cPos, INOUT s16 *avoidYaw, s16 yawRange) {\n',
     'static f32 sOverrunPos[3];\n'
     'static f32 overrun_float(u32 bits) { f32 f; memcpy(&f, &bits, 4); return f; }\n'
     '#define WALL_OVERRUN() do { \\\n'
     '    if (colData.numWalls >= 7) { \\\n'
     '        struct Surface *s = colData.walls[6]; \\\n'
     '        sOverrunPos[0] = overrun_float(((u32) (u16) s->type << 16) | (u16) s->force); \\\n'
     '        sOverrunPos[1] = overrun_float(((u32) (u8) s->flags << 24) | ((u32) (u8) s->room << 16) | (u16) (s->lowerY / 4)); \\\n'
     '        sOverrunPos[2] = overrun_float(((u32) (u16) (s->upperY / 4) << 16) | (u16) (s->vertex1[0] / 4)); \\\n'
     '        cPos = sOverrunPos; \\\n'
     '    } \\\n'
     '    if (colData.numWalls >= 8) { avoidYaw = (s16 *) &colData.walls[7]->type; } \\\n'
     '} while (0)\n'
     's32 rotate_camera_around_walls(struct Camera *c, Vec3f cPos, INOUT s16 *avoidYaw, s16 yawRange) {\n'),
    ('        if (find_wall_collisions(&colData) != 0) {\n            wall = colData.walls[colData.numWalls - 1];\n\n            // If we\'re over halfway',
     '        if (find_wall_collisions(&colData) != 0) {\n            WALL_OVERRUN();\n            wall = colData.walls[colData.numWalls - 1];\n\n            // If we\'re over halfway'),
    ('            if (find_wall_collisions(&colData) != 0) {\n                wall = colData.walls[colData.numWalls - 1];\n                horWallNorm',
     '            if (find_wall_collisions(&colData) != 0) {\n                WALL_OVERRUN();\n                wall = colData.walls[colData.numWalls - 1];\n                horWallNorm'),
]

# A fifth wall overruns the saved position pointers of the player's wall functions in the original, so the push never
# reaches the position and the coordinates land on the wall surfaces instead, which stay changed until the level reloads.
PATCHES['src/engine/surface_collision.c'].extend([
    ('s32 f32_find_wall_collision(f32 *xPtr, f32 *yPtr, f32 *zPtr, f32 offsetY, f32 radius) {',
     'static u32 overrun_bits(f32 f) { u32 u; memcpy(&u, &f, 4); return u; }\n'
     'void wall_overrun_write_x(struct Surface *s, f32 v) {\n'
     '    s->type = (s16) (overrun_bits(v) >> 16);\n'
     '    s->force = (s16) overrun_bits(v);\n'
     '}\n'
     'void wall_overrun_write_y(struct Surface *s, f32 v) {\n'
     '    s->flags = (s8) (overrun_bits(v) >> 24);\n'
     '    s->room = (s8) (overrun_bits(v) >> 16);\n'
     '    s->lowerY = (s16) ((s16) overrun_bits(v) * 4);\n'
     '}\n'
     'void wall_overrun_write_z(struct Surface *s, f32 v) {\n'
     '    s->upperY = (s16) ((s16) (overrun_bits(v) >> 16) * 4);\n'
     '    s->vertex1[0] = (s16) ((s16) overrun_bits(v) * 4);\n'
     '}\n\n'
     's32 f32_find_wall_collision(f32 *xPtr, f32 *yPtr, f32 *zPtr, f32 offsetY, f32 radius) {'),
    ('    *xPtr = collision.x;\n    *yPtr = collision.y;\n    *zPtr = collision.z;\n',
     '    if (collision.numWalls >= 5) { wall_overrun_write_x(collision.walls[4], collision.x); } else { *xPtr = collision.x; }\n'
     '    if (collision.numWalls >= 6) { wall_overrun_write_x(collision.walls[5], collision.y); } else { *yPtr = collision.y; }\n'
     '    if (collision.numWalls >= 7) { wall_overrun_write_x(collision.walls[6], collision.z); } else { *zPtr = collision.z; }\n'),
])
PATCHES['src/engine/surface_collision.h'].append(
    ('s32 f32_find_wall_collision(',
     'void wall_overrun_write_x(struct Surface *s, f32 v);\nvoid wall_overrun_write_y(struct Surface *s, f32 v);\nvoid wall_overrun_write_z(struct Surface *s, f32 v);\ns32 f32_find_wall_collision('),
)
PATCHES['src/game/mario.c'] += [
    ('    // I\'m not sure if this code is actually ever used or not.\n    pos[0] = collisionData.x;\n',
     '    if (collisionData.numWalls >= 5) {\n'
     '        wall_overrun_write_x(collisionData.walls[4], collisionData.x);\n'
     '        wall_overrun_write_y(collisionData.walls[4], collisionData.y);\n'
     '        wall_overrun_write_z(collisionData.walls[4], collisionData.z);\n'
     '        return wall;\n'
     '    }\n\n'
     '    // I\'m not sure if this code is actually ever used or not.\n    pos[0] = collisionData.x;\n'),
    ('    find_wall_collisions(collisionData);\n\n    pos[0] = collisionData->x;\n',
     '    find_wall_collisions(collisionData);\n\n'
     '    if (collisionData->numWalls >= 5) {\n'
     '        wall_overrun_write_x(collisionData->walls[4], collisionData->x);\n'
     '        wall_overrun_write_y(collisionData->walls[4], collisionData->y);\n'
     '        wall_overrun_write_z(collisionData->walls[4], collisionData->z);\n'
     '        return;\n'
     '    }\n\n'
     '    pos[0] = collisionData->x;\n'),
]

# While flying, the camera's floor-based height pulls it back down, so it would be left far below a high player.
# Keep it at a fixed distance instead, in whichever direction the camera buttons have turned it.
PATCHES['src/game/camera.c'].append(
    ('    update_lakitu(c);\n\n    gLakituState.lastFrameAction = sMarioCamState->action;\n',
     '    if (gMarioStates[0].action == ACT_DEBUG_FREE_MOVE) {\n'
     '        f32 *fly = gMarioStates[0].pos;\n'
     '        s16 flyYaw = atan2s(c->pos[2] - fly[2], c->pos[0] - fly[0]);\n'
     '        vec3f_set(c->pos, fly[0] + 1000.0f * sins(flyYaw), fly[1] + 300.0f, fly[2] + 1000.0f * coss(flyYaw));\n'
     '        vec3f_set(c->focus, fly[0], fly[1] + 100.0f, fly[2]);\n'
     '    }\n\n'
     '    update_lakitu(c);\n\n    gLakituState.lastFrameAction = sMarioCamState->action;\n'),
)

for name, edits in PATCHES.items():
    path = os.path.join(engine, name)
    src = open(path).read()
    for old, new in edits:
        if old not in src:
            raise SystemExit(f'patch target not found in {name}: {old}')
        src = src.replace(old, new, 1)
    open(path, 'w').write(src)
