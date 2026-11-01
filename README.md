# Ultra Jump Mania: native PC port

Runs the Super Mario 64 hack *Ultra Jump Mania - Simpleflip Island* (Superstupidy) natively on Linux, with no emulator. A Windows build is possible but takes manual steps. You play as Tari.

| Part | Where | Source |
|---|---|---|
| Engine | `third_party/sm64coopdx` | [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx) v1.5.1 |
| Levels, textures, HUD, music, text | `third_party/ultra-jump-mania-mod` | [GameBanana mod 486003](https://gamebanana.com/mods/486003), imported by sonicytp |
| Tari model, goomba, act select eye and 3D coin | exported into `build/` by `tools/rom2tari.py` | your hack ROM |
| Textures the mod lacks or has as vanilla | written over the mod by `tools/rom2tex.py` | your hack ROM |
| Scrolling textures | registered by `tools/scrolls.py` | the mod |
| Voices, sound effects, instruments | written into the engine by `tools/rom2sound.py` during the build | your hack ROM |
| Boot logo, Select File flow | written into the engine by `tools/rom2intro.py` during the build | your hack ROM |
| Always-on health meter, no lives, menu text, collision, camera, skies, no co-op chat | written into the engine by `tools/patch_engine.py` during the build | your hack ROM |
| Controls overlay (optional) | `mods/ujm-controls` | this repo |

## Requirements
- Linux. The commands below use Debian/Ubuntu package names, so adjust them for other distros.
- Two ROMs you supply yourself, placed in the folder **above** this repo:
  - `Super Mario 64 (U) [!].z64` (SHA-1 `9bef1128717f958171a4afac3ed78ee2bb4e86ce`)
  - `Ultra Jump Mania - Simpleflip Island.z64` (SHA-1 `2ea4b33a4206aa8df1de6cd721d79ee2b5740ca5`)

## Getting started
Run these from this repo.

```bash
sudo apt-get install build-essential git python3 pkg-config libsdl2-dev libglew-dev libgl1-mesa-dev binutils-mips-linux-gnu unzip curl bsdmainutils libcapstone-dev libz-dev libcurl4-openssl-dev
tools/fetch.sh     # download the engine and mod into third_party/
tools/build.sh     # build the engine and install the mod (about 4 minutes)
tools/run.sh       # play
```

## Optional: running in an Incus container
This keeps the toolchain and the game off the host. It relies on the `ws` helper from the author's own machine setup, and expects the folder above this repo to be named `MR64` and mounted at `/home/dev/code/MR64`.

```bash
ws new mr64 "$(dirname "$PWD")"
incus exec mr64 -- bash -c 'apt-get update && apt-get install -y build-essential git python3 pkg-config libsdl2-dev libglew-dev libgl1-mesa-dev binutils-mips-linux-gnu unzip curl bsdmainutils libcapstone-dev libz-dev libcurl4-openssl-dev libgl1-mesa-dri'
ws run -- bash tools/fetch.sh
ws run -- bash tools/build.sh
tools/setup-display.sh     # once: share the GPU, Wayland display and audio
tools/play.sh              # play
```

Anything running in `mr64` can then open windows on your desktop and use your audio. To undo it: `incus config device remove mr64 gpu wayland pulse`.

## Windows
The scripts here only build on Linux. There is no Windows build script yet, but a build made by cross-compiling on Linux has been run under Wine, though not on real Windows. After `tools/build.sh`, it took these steps:

1. Install `mingw-w64`, and get the SDL2, GLEW and zlib `mingw64` packages from [MSYS2](https://repo.msys2.org/mingw/mingw64/) to compile against.
2. In a copy of `third_party/sm64coopdx`, run `make WINDOWS_BUILD=1 CROSS=x86_64-w64-mingw32- TARGET_BITS=64 TARGET_ARCH=x86-64 DISCORD_SDK=0 COOPNET=0`. This needs the POSIX-threads compilers, a `x86_64-w64-mingw32-sdl2-config` script for the MSYS2 SDL2, and small stand-ins for `ftello64`, `fseeko64` and `isblank`, which that SDL2 expects.
3. Next to `sm64coopdx.exe`, put `lang`, `palettes`, `dynos` and `mods` from the build folder. Pass `--savepath` a `user` folder holding `baserom.us.z64`, a `mods` folder with `ultra jump mania` and `ujm-controls`, and an `sm64config.txt` with the lines `enable-mod: ujm-controls` and `enable-mod: ultra jump mania`. Without those lines, the first launch shows the vanilla game.

## Controls
Keyboard defaults, which you can change in the game's options:

| Action | Key |
|---|---|
| Move | W, A, S, D |
| Jump (A) | L |
| Punch (B) | `,` |
| Crouch (Z) | K |
| Pause (Start) | Space |
| Camera (C buttons) | Arrow keys |
| Free fly on/off (L) | Left Shift |

While flying, W, A, S, D move, L rises, K falls and `,` slows you down. You pass through walls and over death floors and can't touch objects, so turn it off to land on a goal or warp. It won't turn off where there is no floor below you.

In the Incus setup, controllers are not passed through to the container yet.

The controls also appear on screen while paused. To turn the overlay off, remove `--enable-mod ujm-controls` from the launcher.

## Comparing with the original
`tools/play-emulator.sh` runs the hack in `mupen64plus` with the same keys as the game, apart from free fly. Run `tools/setup-x11.sh` once first. It uses the Incus setup, and needs `mupen64plus-ui-console` in the container.

## Testing
`tests/smoke.sh` starts the game off-screen, walks forward and saves screenshots to `build/shots`. It needs `xvfb xdotool imagemagick`.

`tests/sidebyside.sh` plays the same scripted inputs in `mupen64plus` and in the port, and records them next to each other to `build/sidebyside.mp4`, with screenshots in `build/sidebyside/`. It also needs `mupen64plus-ui-console ffmpeg`. Set `DURATION` to change its length in seconds. Set `LEVEL=9` and `SPAWN_WAIT=25` to start both in Simpleflip Island, the port through the hub's own warp and the test-only mod `tests/ujm-warp`. The two can't stay in step for long: the inputs are timed, and the emulator runs slower and enters the level at a different spot.

To compare with the original's memory and camera, these run the hack from save states in `build/oracle`. `tests/emu-state.sh` boots it and saves a state, and `tests/emu-enter.sh` goes through a warp from one. `tests/emu-at.sh` and `tests/port-at.sh` take screenshots at the same spots. `tests/ramdump.py`, `tests/port-dump.sh` and `tests/compare-objects.py` compare object lists. `tests/flow.sh` captures the boot, Select File and pause screens. `tests/traj.sh` plays frame-exact inputs on both and compares position, action and camera (set `FREECAM=1` to leave the camera unpinned). `tests/compare-level.py` compares a level's vertices, lights and textures with the hack's RAM, and `tests/romdiff.py` lists every code difference between the hack and vanilla. Set `EMUPLUGINS` to run `tests/emu-at.sh` with other emulator plugins. `tests/star.sh` teleports both next to an object or warp, taps A and captures what follows (set `NOACT=1` for levels without act select). `tests/audio.sh` compares recorded music levels. `tests/compare-text.py` compares all dialogs and names byte by byte with the hack, `tests/fly.sh` logs the camera distance in free fly, and `tests/wallscan.sh` counts the walls the player's checks can hit in a level. Set `TRAJ_START` and `TRAJ_NEST` to run `tests/traj.sh` from a chosen spot, with inputs that walk into the hub's corner of walls.

## Troubleshooting
| Message | Cause | Fix |
|---|---|---|
| `OpenGL 2.1+ is required. Reported version: 0.0` or `Could not setup connection to PulseAudio` | Incus setup only: the display is not shared with the container | Run `tools/setup-display.sh` |
| `requires INTEL_FORCE_PROBE` and no window | Mesa is too old for your GPU | Install a newer Mesa (`tools/setup-display.sh` uses Debian backports) |
| `could not find valid vanilla us sm64 rom` | The ROM is not in the game's user folder | Check the ROM name and location, then rerun `tools/build.sh` |
| Mario appears instead of Tari | The mod's Tari model is not installed | Rerun `tools/build.sh` |

If keys stop responding, run `UJM_KEYLOG=1 tools/play.sh` and reproduce it: the terminal then lists every key the game receives.

## Known gaps
- Tested off-screen in the container only so far. Running without a container has not been confirmed.
- No complete playthrough has been played. A scripted 1548-frame run (`tests/traj.sh`) matches the hack in position and action in the hub, level 17 and all five areas of Simpleflip Island, with the camera within 1 unit once it has settled from its entry. Each star, the red coins, the level 17 NPC, the ending and a death warp were compared separately with the hack by teleporting next to them (`tests/stars.sh`, `tests/redcoins.sh`, `tests/star.sh`).
- The hack removes the original limit of four walls per collision check, so extra walls overwrite the stack. The port uses a longer list and reproduces the effects in the camera (`rotate_camera_around_walls`) and in the player's wall functions. Overruns in object wall checks are not reproduced. `tests/wallscan.sh` lists where wall checks can reach five walls. For the player's steps, that is only the hub. Ledge and punch checks never do. The swim radius and object radii of 100 or more also reach five walls in the hub and level 9 areas 1 and 4; level 9 areas 2, 3 and 5 and level 17 stay at four or fewer. Started inside that corner, the port matches the hack from frame 2, the first frame the two logs line up. Walking in from the side in a scripted test never reached five walls.
- SAVE & QUIT differs on purpose. The hack's scripts send it to Select File, but under `mupen64plus` the hack freezes on a black screen there, with both the dynarec and the interpreter. The port goes to Select File.
- The hub's warp 240 to level 6 has no trigger found in normal play. Forcing it stops `mupen64plus` with a core error (`error in ERET`), while the port loads the room and shows a save prompt.
- Free fly isn't in the hack. Its camera stays a fixed distance from the player instead of behaving like the hack's.
- Audio was measured, not heard. Sequences, tempo, volumes and spectrum match the hack, apart from the emulator's own 0.8 output factor. The port allows 128 notes at once where the N64 allows 16, so dense music may drop fewer notes than on the original.
- `mupen64plus` is the only reference, and its plugins disagree on blending and filtering, so small colour and text softness differences can't be settled without a hardware-accurate renderer. The pause text uses the same filter settings as the hack's display lists.
- `mr_blizzard`, the wing cap, `white_particle` and `red_flame_shadow` fail to compile from the mod and use vanilla models. Their ROM data is byte-identical to vanilla, so this doesn't change how they look.
- The menu's single-glyph strings, such as the coin and star symbols, come from the vanilla ROM.
- The game starts as a one-player sm64coopdx session, so it is not a standalone executable.

## Sharing
Do not publish `build/`, `third_party/` or the ROMs: they contain Nintendo and hack-author material. `.gitignore` keeps them out of this repo.
