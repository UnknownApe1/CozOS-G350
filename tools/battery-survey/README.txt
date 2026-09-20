CozOS G350 Battery Survey 0.1
=============================

This diagnostic does not change battery percentage, charging, shutdown, DTB,
or KNULLI configuration. It records the values already exposed by the RK817
fuel gauge and KNULLI BatteryPlus so CozOS can build a G350-specific correction
from real hardware data.

INSTALL
1. Extract this ZIP.
2. Copy the contents of its roms/ports folder into KNULLI's existing
   roms/ports folder on the SHARE partition.
3. Boot the G350 and refresh the game list if needed.

RUN A USEFUL SURVEY
1. Charge until the charge LED indicates full. Leave it connected 20 minutes.
2. Run "CozOS Battery - Start Survey" from Ports.
3. Unplug the charger and use the G350 normally.
4. Continue until the system gives a low-battery warning or shuts down.
5. Recharge enough to boot.
6. Run "CozOS Battery - Stop and Package".
7. Copy and upload this file:
   /userdata/system/cozos/battery-survey-latest.zip

The logger samples once per minute. A complete 100%-to-empty discharge is most
valuable, but partial sessions are still useful. Do not repeatedly force the
battery below the device's normal shutdown point.

FILES
- /userdata/system/cozos/battery-survey/<session>/battery.csv
- /userdata/system/cozos/battery-survey/<session>/metadata.json
- /userdata/system/cozos/battery-survey-latest.zip

Run "CozOS Battery - Snapshot" for a one-time report without starting a survey.
