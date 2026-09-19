# G350 battery-accuracy work

Status: data collection; no percentage override is enabled yet.

## What the current stack does

The BATLEXP G350 DTB in KNULLI uses the RK817 fuel-gauge driver. Its current
battery node contains:

- 21-point OCV table: 3400 mV through 4172 mV.
- Design capacity: 3151 mAh.
- Design qmax: 3465 mAh.
- Battery resistance: 146.
- Power-off threshold: 3400 mV.
- Charger maximum: 4250 mV and 2000 mA.

KNULLI Scarab also includes BatteryPlus. Its default voltage mode learns
device-specific full states and writes the visible value to
`/tmp/battery.percent`, which EmulationStation, the HUD, system information,
and patched RetroArch may consume instead of the RK817 driver's raw `capacity`.

That means there can be several different values at once:

1. RK817 driver capacity.
2. BatteryPlus visible percentage.
3. Voltage and charge-counter readings.
4. Frontend values sampled or cached at different times.

A correction must identify which layer is wrong before changing the DTB or
overriding the number.

## Battery Survey 0.1

The read-only survey package samples once per minute:

- UTC time and uptime.
- RK817 driver capacity and status.
- KNULLI/BatteryPlus visible percentage.
- voltage_now, voltage_avg, and voltage_ocv when exposed.
- current, charge, energy, temperature, health, and cycle fields when exposed.
- BatteryPlus configuration, learned map, restore state, and calibrated flag.
- G350 DT battery and charger properties.

It does not modify battery, charger, shutdown, or DTB settings.

## Test procedure

1. Charge fully and remain connected for 20 minutes.
2. Start the survey from Ports.
3. Unplug and use the G350 normally until its normal low-battery shutdown.
4. Recharge enough to boot.
5. Run Stop and Package.
6. Review `/userdata/system/cozos/battery-survey-latest.zip`.

## Release gate for an accuracy fix

- A complete discharge log establishes the real full and empty loaded voltage.
- Visible percentage is monotonic during steady discharge, apart from small
  load/recovery tolerance.
- Charging state never causes an unsafe downward correction.
- Low-battery shutdown remains above the hardware cutoff.
- The change can be completely removed without touching saves or user data.
- At least two full discharge cycles agree before a DTB change is considered.

## Why the DTB is not being changed yet

P4ELEC's open G350 battery report describes large jumps, cable-induced jumps,
and shutdown while a high percentage remains. Its maintainer also observed
inconsistent behavior despite matching DTB settings. Changing design capacity
or the OCV table without measurements could make shutdown less safe. The first
step is therefore paired voltage, current, driver-capacity, and BatteryPlus
logging from the same physical unit.
