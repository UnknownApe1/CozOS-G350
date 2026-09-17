# Install, upgrade, and recovery

## Requirements

- BATLEXP G350.
- Official KNULLI G350 installation. The 0.5.3 overlay retains the 0.4.4
  hardware-tested base for
  KNULLI Scarab 2026-05-10.
- A backup of the working SD card is strongly recommended.

## Install or upgrade

1. Download `releases/CozOS-G350-Overlay-0.5.3.zip`.
2. Optionally verify its SHA-256 against the adjacent `.sha256` file.
3. Extract the ZIP on a computer. Do not flash the ZIP.
4. Copy the contents of the extracted `roms/ports` directory to the existing
   `roms/ports` directory on KNULLI's writable `SHARE` partition.
5. Merge/replace the older CozOS files when prompted.
6. Boot KNULLI and refresh the game list if the new Ports entries are absent.
7. Run `CozOS Control Center` from Ports, then choose
   `Install or repair CozOS 0.5.3`.
8. Wait for completion. Creating the KNULLI rootfs overlay can take several
   minutes. Do not reset or remove power while it is running.
9. Reboot from the KNULLI menu.

The installer hardware-gates itself to G350/BATLEXP, verifies required KNULLI
interfaces, stores rollback metadata before writes, and checks installed file
hashes.

## Status report

Open `CozOS Control Center` and choose `Status and diagnostics`. Diagnostic
output is stored under:

```text
/userdata/system/cozos/report.txt
/userdata/system/cozos/rootfs-splash-status.txt
/userdata/system/cozos/control-center-report.txt
```

## Normal rollback

Open `CozOS Control Center`, choose `Remove CozOS / complete rollback`, confirm,
and reboot. It restores the backed-up hotkey configuration, managed settings,
prior splash files, and original KNULLI system-splash image. A later manual
edit is never silently overwritten.

## Settings backup and restore

The Control Center can back up the supported KNULLI configuration files under
`/userdata/system/cozos/backups`. Each archive has a manifest and SHA-256 hash
for every file. Restore accepts only the documented settings paths, verifies
all hashes before writing, and creates a pre-restore safety backup first.

This utility is for settings. CozOS never moves or deletes ROMs, BIOS files,
saves, save states, or scraped media. Keep a normal SD-card backup for those.

## Emergency overlay recovery

If a rootfs overlay prevents KNULLI from booting:

1. Power the G350 off.
2. Insert SD1 into a computer.
3. Open the readable KNULLI/BATOCERA boot partition.
4. Open its `boot` folder.
5. Delete the file named `overlay`.
6. Safely eject the card and boot again.

This removes all rootfs overlay modifications. It does not delete files stored
under `/userdata`, including ROMs, BIOS files, saves, and save states.

## Updating KNULLI itself

Remove or back up the rootfs `overlay` file before a major KNULLI update. After
confirming the new firmware boots, install a CozOS version documented as
compatible with that KNULLI release.
