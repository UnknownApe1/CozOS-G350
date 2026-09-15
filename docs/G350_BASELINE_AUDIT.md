# G350 Baseline Audit

## Sources compared

- KNULLI `knulli-main` at `064cd0900e7da07e6a5f15608f18b782270789f7`.
- PAN4ELEC G350 release image dated 2025-03-12, verified against its published
  SHA-256 checksum (`8c87d327...ac9122`).
- PAN4ELEC public source snapshot at
  `9c19bfb2717a8790d96ee6104090e575966d5d00`.

PAN4ELEC's repository states that its complete modified device-tree source is
not published. Its release image was therefore inspected only as a behavioral
and binary configuration reference. No PAN4ELEC binary or unpublished code is
included in CozOS.

## Confirmed common hardware configuration

Both device trees describe the same core G350 hardware characteristics:

- RK3326 platform and RK817 PMIC/battery driver.
- Identical battery OCV table, design capacity, qmax, battery resistance,
  charger current/voltage, power-off threshold, and sample resistance.
- Identical speaker and headphone codec volume values.
- Volume buttons use Linux key codes 114 and 115.
- The physical FN/Menu key is Linux input code 708 (`BTN_TRIGGER_HAPPY5`).
- Face, shoulder, D-pad, stick-click, Start, and Select GPIO assignments match.

KNULLI uses a dedicated `G350` model and `g350_joypad` identity. Its controller
mapping explicitly compensates for the G350 analog-axis arrangement. This is
preferable to importing PAN4ELEC's older generic `GO-Super Gamepad` identity.

## Fixed in CozOS

### FN + Volume brightness shortcut

KNULLI's G350 device tree and EmulationStation profile both identify FN/Menu as
`BTN_TRIGGER_HAPPY5`. The generic RK3326 multimedia shortcut file instead uses
`BTN_TRIGGER_HAPPY1`, which is Select on this device.

`multimedia_keys_G350.conf` now provides an isolated G350 mapping:

- Volume Up/Down changes volume.
- FN + Volume Up/Down changes brightness.
- Power-button press/release retains KNULLI's normal power handling.

The triggerhappy service automatically chooses this file because the KNULLI
G350 device tree reports the model as `G350`.

## Physical baseline — 2026-09-15

The official KNULLI G350 image was tested on the target BATLEXP G350 before
building CozOS:

- Display, normal brightness, D-pad, face buttons, both analog sticks,
  FN/Menu, volume buttons, and speaker audio pass.
- FN + Volume does not change brightness in the frontend. This reproduces the
  shortcut mismatch fixed above.
- The frontend does not show a status bar. This is tracked separately as a
  presentation/default-setting issue.
- A brief power-button press appears to power the unit off. A cold-boot-logo
  check is still required to distinguish a failed suspend from a suspend state
  that blanks the display and LED.
- The rumble motor runs during startup, reproducing KNULLI's known G350 boot
  rumble issue. Gameplay rumble has not yet been tested.
- Headphone hot-plug has not yet been tested.

## Must be verified on hardware

1. Volume buttons repeat correctly when held.
2. The CozOS FN + Volume fix adjusts brightness without also changing volume.
3. Headphone insertion/removal routes audio correctly.
4. A brief power press suspends and resumes without displaying the full KNULLI
   boot sequence.
5. Suspend/resume restores both audio and controls five times in a row.
6. Gameplay rumble works without leaving the motor active during startup.
7. Battery readings are plausible across a full charge/discharge cycle.

## Deliberately unchanged

- Battery parameters: KNULLI and PAN4ELEC already match.
- Audio codec defaults: KNULLI and PAN4ELEC already match.
- KNULLI's G350 device tree: its controller identity and axis configuration are
  newer and must be tested before replacing any values.
- Emulator defaults: tune only after the hardware baseline passes.
