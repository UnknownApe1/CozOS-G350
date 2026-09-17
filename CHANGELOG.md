# Changelog

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
