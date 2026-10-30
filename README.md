# Ultra Jump Mania: native PC port

Runs the Super Mario 64 hack *Ultra Jump Mania - Simpleflip Island* (Superstupidy) natively on Linux, with no emulator. You play as Tari.

| Part | Where | Source |
|---|---|---|
| Engine | `third_party/sm64coopdx` | [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx) v1.5.1 |
| Levels, textures, HUD, music, text | `third_party/ultra-jump-mania-mod` | [GameBanana mod 486003](https://gamebanana.com/mods/486003), imported by sonicytp |
| Tari player model | exported into `build/` by `tools/rom2tari.py` | your hack ROM |

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

In the Incus setup, controllers are not passed through to the container yet.

## Testing
`tests/smoke.sh` starts the game off-screen, walks forward and saves screenshots to `build/shots`. It needs `xvfb xdotool imagemagick`.

## Troubleshooting
| Message | Cause | Fix |
|---|---|---|
| `OpenGL 2.1+ is required. Reported version: 0.0` or `Could not setup connection to PulseAudio` | Incus setup only: the display is not shared with the container | Run `tools/setup-display.sh` |
| `requires INTEL_FORCE_PROBE` and no window | Mesa is too old for your GPU | Install a newer Mesa (`tools/setup-display.sh` uses Debian backports) |
| `could not find valid vanilla us sm64 rom` | The ROM is not in the game's user folder | Check the ROM name and location, then rerun `tools/build.sh` |
| Mario appears instead of Tari | The mod's Tari model is not installed | Rerun `tools/build.sh` |

## Known gaps
- Tested off-screen in the container only so far. Playing on a real display, running without a container, and audio have not been confirmed.
- No full playthrough has been tested.
- The mod's other custom actors are not loaded. Their files are named `custom.*`, and renaming them gave 1,643 errors, with 48 of 144 actors failing to compile. Objects the hack changed may look like the originals.
- The game starts as a one-player sm64coopdx session, so it is not a standalone executable.

## Sharing
Do not publish `build/`, `third_party/` or the ROMs: they contain Nintendo and hack-author material. `.gitignore` keeps them out of this repo.
