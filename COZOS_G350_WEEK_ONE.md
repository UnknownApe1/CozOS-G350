# CozOS G350 — Week One

## Goal

Produce a conservative, testable G350 image based on KNULLI Scarab. The first
week is about stability, not visual customization or adding features.

The PAN4ELEC card remains untouched and is the recovery/reference system.

## Release gate

The first image is considered workable only when all critical checks pass on
the physical BATLEXP G350:

- Boots successfully three times in a row.
- Display orientation, brightness, controls, both analog sticks, and FN/Menu
  work correctly.
- Speaker audio, volume controls, and headphone insertion/removal work.
- Clean shutdown works without filesystem repair on the next boot.
- Suspend/resume works five times without losing controls or audio.
- Battery percentage is plausible during a 60-minute discharge test.
- NES, SNES, Genesis, GBA, and PS1 each launch, play, save, exit, and reload.
- At least one N64, Dreamcast, PSP, and Nintendo DS test game is recorded as
  pass, acceptable with tuning, or unsupported for the first release.
- No ROMs, BIOS files, saves, or scraped media are shipped in the image.

## Schedule

### Day 1 — Known-good baseline

1. Preserve the working PAN4ELEC card.
2. Flash current KNULLI Scarab for G350 to a second reliable microSD card.
3. Run the hardware smoke-test section below.
4. Record every failure before changing settings.

### Day 2 — Reproducible fork

1. Build the unmodified G350-only image from this repository.
2. Verify its SHA-256 checksum.
3. Flash and repeat the smoke test.

### Days 3–4 — G350 fixes

Fix only failures that reproduce on the physical unit. Keep each fix isolated
and reversible. Compare behavior with PAN4ELEC when controls, display, audio,
battery, or suspend differ.

### Day 5 — Emulator defaults

Lock conservative defaults for PS1 and below. Record higher-end systems as
best-effort; do not sacrifice stability to chase a single difficult game.

### Weekend — Release candidate

Perform the complete release gate twice from a clean flash. A failing critical
check blocks the stable label and produces another test build instead.

## Hardware smoke-test record

| Check | Result | Notes |
|---|---|---|
| Cold boot | Pass (1/3) | Official KNULLI image reaches the frontend. |
| Reboot | Not tested | |
| Screen/orientation | Pass | Display works correctly. |
| Brightness keys | Partial | Normal brightness works; FN + Volume fails in the frontend on upstream KNULLI. CozOS fix staged. |
| D-pad and face buttons | Pass | |
| Left analog stick | Pass | |
| Right analog stick | Pass | |
| FN/Menu and hotkeys | Pass | FN/Menu itself works. |
| Speaker/volume | Pass | Speaker and volume buttons work. |
| Headphone hot-plug | Pass | Audio switches to headphones and returns to the speaker. |
| Suspend/resume | Pass (5/5) | Five consecutive cycles completed; controls and audio still work after waking. |
| Clean shutdown | Not tested | |
| Battery reading | Not tested | |
| Rumble at boot/gameplay | Fail at boot | Device rumbles during startup; gameplay rumble not tested. |
| USB card reader/OTG | Not tested | |
| Wi-Fi dongle, if used | Not tested | |

The missing frontend status bar is tracked as a presentation/default-setting
issue rather than a hardware failure.

## Build

The build host needs Linux or WSL2, a running Docker engine, at least 8 GiB of
RAM, and at least 80 GiB free disk space. More disk and RAM are preferable.

```sh
sh ./scripts/cozos/build-g350.sh
```

The script deliberately overrides KNULLI's normal RK3326 packaging list so it
emits only the BATLEXP G350 image. It also generates a SHA-256 checksum beside
the compressed image.

## Safety rules

- Never flash the only working PAN4ELEC card.
- Confirm the target drive by capacity and device name before writing an image.
- Keep personal ROMs, BIOS files, saves, and Wi-Fi credentials outside Git.
- Do not enable upstream OTA updates on a modified image until update
  compatibility has been reviewed.
- Keep a boot log and exact build commit for every flashed test image.
