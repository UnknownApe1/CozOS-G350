CozOS G350 SD-card overlay 0.2.0
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
   if needed. Open Ports, then "CozOS 0.2 - Install".
5. Reboot through KNULLI's normal menu.
6. Hold FN first, then tap Volume + and Volume -. Test from the main menu.
7. Briefly tap Power. The screen should turn off without rebooting. Briefly
   tap Power again to wake. Hold Power for 2 seconds when you want shutdown.
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
  bash "/userdata/roms/ports/CozOS 0.2 - Install.sh"
This is an alternative; SSH is not required for the Ports method.

WHAT CHANGES
The installer checks the detected hardware and the installed startup hook
and volume handler before modifying anything. It copies the current hotkey
configuration to a backup, then installs a user override at:
  /userdata/system/configs/multimedia_keys.conf
It changes the FN brightness chords to BTN_TRIGGER_HAPPY5 (input code 708),
using the existing KNULLI brightness handler. It also replaces the plain power
press/release commands with persistent CozOS handlers. FN+Power and all other
hotkeys are retained. This does not add a new on-screen brightness bar.
The visible version label is in the Ports entries and the status report;
it does not rename official KNULLI's main menu or claim a custom firmware.

POWER FIX AND CHECK
The supplied report showed that the official 2026-05-10 G350 build called
pm-suspend on a short press, then booted again instead of resuming. CozOS 0.2
uses a screen-off sleep instead: it mutes audio, pauses EmulationStation and
active emulator processes, lowers the CPU governor, and turns off the display.
It does not enter the broken kernel suspend state. A second short press restores
the CPU, processes, display and prior mute state. This uses more power than a
working hardware suspend, but avoids the observed reboot. Hold Power for two
seconds for normal shutdown.

1. Launch "CozOS 0.2 - Status and Power Check" before pressing power.
2. Tap Power briefly, wait 10 seconds, then tap it briefly again.
3. Launch the status entry again and read system/cozos/report.txt.
   "Same kernel boot" confirms that the screen-off cycle did not reboot.

STATUS / RESULTS
Launch the Status entry. A terminal dialog is used when available.
Some Ports frontends do not show shell text. In that case the authoritative
result is saved at system/cozos/last-action.txt, and the detailed report is at
system/cozos/report.txt. There is no background daemon or permanent overlay.

REMOVE
Launch "CozOS 0.2 - Remove", then reboot. It restores the original user config
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
Tested locally: config transformation; preservation of unrelated and FN+Power
bindings; install/remove with and without existing overrides; upgrade from 0.1;
refusal on unknown hardware/unsupported hooks; repeat installation; protection
of later edits; power-button short/long control flow; shell syntax.
The original 0.1 brightness mapping and diagnostics were tested on a physical
G350. The 0.2 screen-off sleep still needs its first physical-device test.
Boot rumble and a graphical status bar are not included.

SOURCE REFERENCES
Reviewed source: UnknownApe1/CozOS-G350 branch cozzios-g350, September 16, 2026.
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/etc/init.d/S50triggerhappy
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/package/system/knulli-triggerhappy/conf/rk3326/multimedia_keys_G350.conf
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/usr/bin/power-button
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/usr/bin/knulli-suspend

The overlay implementation is original and licensed under MIT (LICENSE.txt).
