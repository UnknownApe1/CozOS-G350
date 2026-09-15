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

## Must be verified on hardware

1. Volume buttons repeat correctly when held.
2. FN + Volume adjusts brightness and does not also change volume.
3. FN continues to work as the emulator/frontend hotkey.
4. Both analog sticks move in the correct directions and reach full range.
5. Headphone insertion/removal routes audio correctly.
6. Suspend/resume restores both audio and controls.
7. Rumble does not remain active during startup.
8. Battery readings are plausible across a full charge/discharge cycle.

## Deliberately unchanged

- Battery parameters: KNULLI and PAN4ELEC already match.
- Audio codec defaults: KNULLI and PAN4ELEC already match.
- KNULLI's G350 device tree: its controller identity and axis configuration are
  newer and must be tested before replacing any values.
- Emulator defaults: tune only after the hardware baseline passes.

