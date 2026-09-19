# Changelog

## 0.6.3 — integrated G350 battery survey

- Adds a read-only battery accuracy survey to Control Center rather than
  installing separate Ports launchers.
- Records the RK817 driver percentage, KNULLI-visible percentage, voltage,
  current, charge state, temperature, and available BatteryPlus/device-tree
  metadata once per minute.
- Adds one-time snapshots, live survey status, sample counts, safe stop/package,
  and an upload-ready `battery-survey-latest.zip`.
- Does not change charging, shutdown thresholds, the device tree, BatteryPlus,
  or displayed battery percentage before a real G350 discharge curve is
  analyzed.
- Stops a running survey during complete CozOS removal and refuses unsafe
  session paths or unrelated reused process IDs.
- Expands the regression suite to 20 tests covering battery collection and
  packaging alongside updater, rollback, launcher, and splash safety.

## 0.6.2 — updater reliability and diagnostics

- Searches `SHARE/cozos-updates`, `SHARE/roms/ports`, and the SHARE root for
  local CozOS update ZIPs without recursively scanning ROM libraries.
- Reports every searched location, valid package, and exact rejection reason in
  Control Center diagnostics instead of returning only “no update found.”
- Supports same-version repair and makes active-directory replacement
  rollback-safe if the final filesystem move fails.
- Rejects packaged app files that are absent from the signed-by-hash manifest.
- Adds regression coverage for discovery, corrupt packages, repair, upgrade,
  version rollback, traversal rejection, launcher bootstrap, and splash safety.

## 0.6.1 — permanent Tools Control Center

- Adds a permanent `Tools → CozOS Control Center` launcher and uses Ports only
  for the one-time bootstrap/migration.
- Writes and checksum-verifies the Tools launcher before hiding the verified
  CozOS Ports launcher.
- Refuses to overwrite or remove unrelated and manually edited launcher files.
- Keeps local/online updates and version rollback working from Tools through
  the verified active-version pointer.
- Extends complete rollback to remove verified CozOS launchers and versioned
  application files while preserving user data.

## 0.6.0 — versioned updater and permanent Tools launcher

- Turned the stable Ports Control Center into a one-time bootstrap launcher.
- Installed Control Center application files under versioned directories in
  `/userdata/system/cozos/apps` and switched versions only after validation.
- Added local updates from `SHARE/cozos-updates`, optional online updates from a
  signed-by-hash release index, progress reporting, persistent update logs, and
  restart guidance after activation.
- Added rollback to a retained previous Control Center version without
  overwriting the working copy during an update.
- Added SHA-256 validation, manifest validation, ZIP traversal rejection, and
  regression tests proving a tampered update cannot switch the active version.
- Fixed splash upgrades so a checksum-verified older CozOS image can be
  replaced by the new release while preserving the original KNULLI splash for
  full rollback.
- Added deterministic packaging for both the full overlay ZIP and smaller
  versioned update ZIP, plus the online `index.json` release metadata.

## 0.5.3 — G350 face-button labels

- Enabled SDL label-based face-button reporting only for the Control Center.
- Physical A now selects and physical B goes back, matching the printed G350
  labels, while START remains an alternate select button.
- Added a launcher regression test that verifies the isolated SDL setting.

## 0.5.2 — controller-native Control Center

- Replaced the `dialog`/ncurses interface that rendered blank in VaixTerm with
  a dependency-free ANSI menu driven directly by the G350 controls.
- Added D-pad navigation, A/START selection, B back/cancel, scrollable result
  screens, safe confirmation defaults, cursor restoration, and crash logging.
- Enabled VaixTerm full-render mode for reliable 640×480 redraws.

## 0.5.1 — visible Control Center hotfix

- Fixed the Control Center immediately returning to EmulationStation when
  Ports launched it without an interactive terminal.
- The launcher now opens the menu in KNULLI's bundled 640×480 VaixTerm SDL
  terminal, giving `dialog` a real TTY and handheld navigation support.
- Added an automated non-TTY Ports-launch test to prevent this regression.

## 0.5.0 — Control Center and fast overlay releases

- Replaced three versioned Ports entries with one stable CozOS Control Center.
- Added install/repair, combined diagnostics, local version information, and
  checksum-verified complete rollback to the Control Center.
- Added settings backup and verified restore with strict path allowlisting and
  an automatic pre-restore safety snapshot.
- Added a deterministic overlay packager and a short GitHub Actions workflow
  that tests Python, shell syntax, version consistency, splash dimensions,
  ZIP integrity, and SHA-256 output without compiling a firmware image.
- Retained all hardware-tested 0.4.4 G350 behavior and preserved user data.

## 0.4.4 — tested G350 update baseline

- Replaced the unsupported G350 boot-partition logo attempt with the PNG used
  by the installed KNULLI `S03system-splash` service.
- Persisted the system splash with KNULLI's `knulli-save-overlay` mechanism.
- Added checksum-verified backup, install verification, normal removal, and
  emergency overlay recovery instructions.
- Retained brightness shortcuts, safe power-button behavior, idle shutdown,
  emulator/core choices, performance profiles, and conservative audiovisual
  defaults.
- Preserved explicit user configuration and all user game data.

## 0.4.3

- Added the G350 emulator/performance profile set and complete rollback state.
- Attempted `/boot/logo_640x480.bmp`; hardware testing showed the installed
  G350 Scarab build did not consume that file.

## 0.4.2

- Added boot-logo diagnostics and strict no-change behavior when the expected
  path was absent.

## 0.4.1 and earlier

- Established G350 hardware checks, brightness hotkeys, short-power screen-off
  behavior, safe long-power shutdown, and configuration-preserving updates.
