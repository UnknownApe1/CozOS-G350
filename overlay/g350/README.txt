CozOS G350 SD-card overlay 0.1.0
===============================
This is a testable configuration update for official KNULLI, not a firmware
image. Do NOT flash this ZIP. No kernel, DTB, ROMs or saves are replaced.

INSTALL
1. Keep a backup of your working card.
2. Extract this ZIP on your computer.
3. Copy the contents of its roms/ports folder into your KNULLI card's
   existing roms/ports folder. Copy the cozos subfolder too.
   Do not overwrite system/custom.sh or format any partition.
4. Put the card back in the G350 and boot. Refresh/update the game list
   if needed. Open Ports, then "CozOS 0.1 - Install".
5. Reboot through KNULLI's normal menu.
6. Hold FN first, then tap Volume + and Volume -. Test from the main menu.
   Check ordinary volume controls and your usual game hotkeys too.

WHERE TO COPY
The required location on the device is /userdata/roms/ports.
If KNULLI is on your home network, open its SHARE network folder and then
roms/ports. If using a card reader, open the partition that already contains
roms and system. Windows may show only the small boot partition when the
data partition is ext4. Do not copy these files to boot instead, and decline
any Windows prompt to format the card. Use KNULLI network sharing or a Linux
computer/live USB to access the existing data partition.

If Ports does not list these scripts, do not reflash. With SSH access run:
  bash "/userdata/roms/ports/CozOS 0.1 - Install.sh"
This is an alternative; SSH is not required for the Ports method.

WHAT CHANGES
The installer checks the detected hardware and the installed startup hook
and volume handler before modifying anything. It copies the current hotkey
configuration to a backup, then installs a user override at:
  /userdata/system/configs/multimedia_keys.conf
It changes the FN brightness chords to BTN_TRIGGER_HAPPY5 (input code 708),
using the existing KNULLI brightness handler. Other hotkeys and power bindings
are retained. This does not add a new on-screen brightness bar.
The visible version label is in the Ports entries and the status report;
it does not rename official KNULLI's main menu or claim a custom firmware.

POWER CHECK
1. Launch "CozOS 0.1 - Status and Power Check" before pressing power.
2. Return to the main menu. Tap power briefly, then try waking it normally.
3. Launch that same entry again.
4. Read/copy system/cozos/report.txt from SHARE/the data partition.
   Same boot ID: there was no full reboot between checks.
   Changed boot ID: a new kernel boot occurred. That does not by itself prove
   whether this was shutdown, a crash, or a failed resume.
The report also contains the installed power scripts, power settings and
available sleep states. No suspend or shutdown behavior is changed by this
package. Safe sleep cannot be promised without the actual device report.

STATUS / RESULTS
Launch the Status entry. A terminal dialog is used when available.
Some Ports frontends do not show shell text. In that case the authoritative
result is saved at system/cozos/last-action.txt, and the detailed report is at
system/cozos/report.txt. There is no background daemon or permanent overlay.

REMOVE
Launch "CozOS 0.1 - Remove", then reboot. It restores the original user config
if there was one, or removes only the override it created. It refuses to
overwrite a config edited by someone else after installation.
Reports and the original backup remain under system/cozos.
After removal you may delete the three CozOS .sh launchers and roms/ports/cozos.

MANUAL RECOVERY
If an installation prevents normal key handling, power down normally when
possible and access the data partition. Read system/cozos/installed.json:
- had_override=false: remove only system/configs/multimedia_keys.conf.
- had_override=true: copy system/cozos/original-multimedia.conf back to
  system/configs/multimedia_keys.conf.
Keep a copy of any subsequently edited config before manual recovery.

VALIDATION AND LIMITS
Tested locally: config transformation, preservation of stock power bindings,
install/remove with and without existing user overrides, refusal on unknown
hardware/unsupported hooks, repeat installation and protection of later edits.
Not tested on a physical G350. This is the first hardware-test package.
Boot rumble, sleep fixes, and a graphical status bar are not included.

SOURCE REFERENCES
Reviewed source: UnknownApe1/CozOS-G350 branch cozzios-g350, September 16, 2026.
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/etc/init.d/S50triggerhappy
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/package/system/knulli-triggerhappy/conf/rk3326/multimedia_keys_G350.conf
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/usr/bin/power-button
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/usr/bin/knulli-suspend

The overlay implementation is original and licensed under MIT (LICENSE.txt).
