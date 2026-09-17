# Tested hardware and behavior

## Confirmed test configuration

- Device: BATLEXP G350
- SoC family: Rockchip RK3326
- Display: 640x480
- Base firmware: official KNULLI Scarab 2026-05-10
- CozOS version: 0.4.4

## Confirmed working

- Display and normal brightness control.
- D-pad, face/shoulder buttons, and both analog sticks.
- FN/Menu button.
- Volume buttons.
- FN + Volume brightness shortcuts after CozOS installation.
- Speaker output.
- CozOS boot splash through KNULLI's rootfs overlay.
- Short-power screen-off/wake replacement.
- Long-power normal shutdown.
- Installation over an earlier CozOS release.
- Checksum-backed removal/rollback path in simulation; the installed splash
  path and upgrade were also hardware-tested.

## Known issue outside 0.4.4 scope

- The vibration motor runs briefly during early boot. The event occurs before
  the CozOS user-space overlay starts.

## Not yet claimed as broadly compatible

- Other G350 hardware/panel revisions.
- KNULLI releases newer or older than the tested Scarab build.
- Other RK3326 handheld models.

The installer intentionally refuses unsupported device identities and missing
firmware interfaces instead of applying a speculative patch.
