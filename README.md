# CozOS G350

**CozOS is a tested BATLEXP G350 enhancement pack for official KNULLI.**

It is not currently a complete replacement firmware image. Install the official
KNULLI G350 image first, then copy the CozOS update to the `SHARE` partition and
run it from Ports. This approach is faster to test, easier to roll back, and
keeps KNULLI as the maintained Linux/emulator base.

## Download

### [Download CozOS G350 0.4.4](releases/CozOS-G350-Overlay-0.4.4.zip)

SHA-256:

```text
ccd2a7f741a7bae9addc7c7ecdaaac0757a78de48cf1df48de63a478d84fd630
```

Tested on a BATLEXP G350 with **KNULLI Scarab 2026-05-10**.

## What CozOS adds

- Working `FN + Volume Up/Down` brightness controls.
- Safe short-power-button screen-off/wake behavior for the G350 build where
  normal suspend shut the device down instead of resuming.
- Hold Power for about two seconds for a normal shutdown.
- Automatic extended idle mode uses shutdown instead of broken suspend.
- G350-oriented emulator/core defaults and performance profiles.
- Conservative scaling, latency, audio, and frame-pacing defaults.
- A working CozOS boot splash using KNULLI's rootfs overlay mechanism.
- Preservation of ROMs, BIOS files, saves, save states, scraped media, and
  existing explicit emulator settings.
- Checksum-verified backups and a complete Remove/rollback command.

## Install

1. Install and boot the official KNULLI G350 image at least once.
2. Download and extract the ZIP above.
3. Copy the **contents** of its `roms/ports` folder into the existing
   `roms/ports` folder on KNULLI's `SHARE` partition.
4. Allow the `cozos` folder and files to merge/replace older versions.
5. Boot the G350, open **Ports**, and run **CozOS 0.4.4 - Install**.
6. Wait for the overlay save to finish; do not power off during installation.
7. Reboot normally through KNULLI.

You do not need to uninstall an older CozOS version before upgrading.

See [the full installation and recovery guide](docs/INSTALL.md).

## Project direction

The supported path is now:

```text
Official KNULLI G350 image + CozOS G350 update pack
```

We are not spending normal development time rebuilding the entire KNULLI image
for every CozOS change. A full image may return later if CozOS needs kernel,
device-tree, bootloader, or driver changes that cannot be delivered safely as
an overlay. The inherited KNULLI/Buildroot source remains in this fork for that
future work and for upstreamable patches.

## Known limitation

The G350 rumble motor activates briefly during early boot. That occurs before
the current CozOS user-space overlay loads, so 0.4.4 does not change it.

## Source layout

- `overlay/g350/` — installable update source.
- `releases/` — tested downloadable packages and checksums.
- `docs/` — installation, recovery, compatibility, and feature notes.
- inherited KNULLI folders — upstream Buildroot/firmware source retained for
  low-level development.

## Upstream and license

CozOS is based on and intended to complement
[KNULLI](https://github.com/knulli-cfw/knulli-linux). Individual components
retain their upstream licenses. See `COPYING` and `overlay/g350/LICENSE.txt`.

This is a community project and is not an official KNULLI release.
