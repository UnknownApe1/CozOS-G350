# Install, update, rollback, and recovery

## Requirements

- BATLEXP G350.
- Official KNULLI G350 installation. CozOS 0.6.3 retains the hardware-tested
  0.4.4/0.5.x behavior on KNULLI Scarab 2026-05-10.
- A backup of the working SD card is strongly recommended.

## First install or upgrade to 0.6.3

1. Download `releases/CozOS-G350-Overlay-0.6.3.zip`.
2. Verify its SHA-256 against the adjacent `.sha256` file if possible.
3. Extract the ZIP on a computer. Do not flash the ZIP.
4. Copy the contents of its `roms/ports` directory to the existing `roms/ports`
   directory on KNULLI's writable `SHARE` partition.
5. Merge/replace the older CozOS files when prompted.
6. Boot KNULLI and refresh the game list if the Ports entry is absent.
7. Run `CozOS Control Center` from Ports. On its first 0.6.3 run, the stable
   launcher safely bootstraps the application to:

```text
/userdata/system/cozos/apps/0.6.3
```

8. Choose `Install or repair CozOS 0.6.3`.
9. Wait for completion. Creating the KNULLI rootfs overlay can take several
   minutes. Do not reset or remove power while it is running.
10. Refresh the game list or reboot normally. From then on, use
    `Tools → CozOS Control Center`; the verified Ports bootstrap is hidden.

The installer hardware-gates itself to G350/BATLEXP, verifies required KNULLI
interfaces, stores rollback metadata before writes, and checks installed files.

## Upgrading from 0.6.2

Copy the unopened `CozOS-G350-Update-0.6.3.zip` to `SHARE/cozos-updates`.
Open `Tools → CozOS Control Center` and choose `Find and install/repair a local
update`. Exit and reopen Control Center after activation.

## Local versioned updates

Future Control Center releases are installed from the permanent Tools entry. Copy a `CozOS-G350-Update-x.y.z.zip` into:

```text
SHARE/cozos-updates
```

Open `Tools → CozOS Control Center` and choose
`Find and install/repair a local update`. CozOS also checks the SHARE root and
`SHARE/roms/ports`. Status diagnostics list valid packages and exact rejection
reasons. Installing the active version again performs a safe repair.
The updater validates the update manifest and every packaged SHA-256, rejects
unsafe ZIP paths, stages the new application in a separate version directory,
and changes `/userdata/system/cozos/active-version` only after validation and
installation succeed. A failed or tampered package therefore cannot replace the
working active Control Center.

## Online updates

`Check and install online update` reads the published CozOS release index,
downloads the listed update ZIP, verifies the release SHA-256, then performs the
same staged installation used for local updates. Network failure or checksum
failure leaves the active version unchanged.

## Version rollback

Choose `Roll back to previous CozOS version` to switch the active Control Center
pointer to a retained previous version. Restart the Control Center after an
update or version rollback so the selected application version is loaded.

Update activity is recorded at:

```text
/userdata/system/cozos/logs/updates.log
```

## Battery accuracy survey

Open `Tools → CozOS Control Center → Battery accuracy survey`. Start fully
charged, begin the survey, unplug, and use the G350 normally until its normal
low-battery shutdown. Recharge only enough to boot, then choose `Stop and
package the survey`. The upload-ready result is written to:

```text
/userdata/system/cozos/battery-survey-latest.zip
```

The logger samples once per minute. It is read-only for battery hardware and
KNULLI configuration; it does not change charging, shutdown thresholds, the
device tree, BatteryPlus, or the displayed percentage. Do not force the battery
below the device's normal shutdown point.

## Status report

Open `CozOS Control Center` and choose `Status and diagnostics`. Diagnostic
output is stored under:

```text
/userdata/system/cozos/report.txt
/userdata/system/cozos/rootfs-splash-status.txt
/userdata/system/cozos/control-center-report.txt
```

## Splash upgrade safety

CozOS keeps the original KNULLI system splash as the rollback source. During an
upgrade, 0.6.3 may replace either that verified original image or the exact
checksum-verified splash installed by an older CozOS release. Any unrecognized
manual/outside edit still stops the splash update instead of being overwritten.

## Complete CozOS rollback

Open `CozOS Control Center`, choose `Remove CozOS / complete rollback`, confirm,
and reboot. It restores the backed-up hotkey configuration, managed settings,
prior user splash files, and original KNULLI system-splash image. A later manual
edit is never silently overwritten.

## Settings backup and restore

The Control Center can back up supported KNULLI configuration files under
`/userdata/system/cozos/backups`. Each archive has a manifest and SHA-256 hash
for every file. Restore accepts only documented settings paths, verifies all
hashes before writing, and creates a pre-restore safety backup first.

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
