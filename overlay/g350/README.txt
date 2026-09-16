CozOS G350 SD-card overlay 0.3.0
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
   if needed. Open Ports, then "CozOS 0.3 - Install".
5. Reboot through KNULLI's normal menu.
6. Hold FN first, then tap Volume + and Volume -. Test from the main menu.
7. Briefly tap Power. The screen should turn off without rebooting. Briefly
   tap Power again to wake. Hold Power for 2 seconds when you want shutdown.
   Check ordinary volume controls and your usual game hotkeys too.
8. Automatic idle behavior remains dim after 5 minutes, but its second stage
   is changed from broken hardware suspend to KNULLI's graceful shutdown.

WHERE TO COPY
The required location on the device is /userdata/roms/ports.
If KNULLI is on your home network, open its SHARE network folder and then
roms/ports. If using a card reader, open the partition that already contains
roms and system. Windows may show only the small boot partition when the
data partition is ext4. Do not copy these files to boot instead, and decline
any Windows prompt to format the card. Use KNULLI network sharing or a Linux
computer/live USB to access the existing data partition.

If Ports does not list these scripts, do not reflash. With SSH access run:
  bash "/userdata/roms/ports/CozOS 0.3 - Install.sh"
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
The installer also changes only system.batterysaver.extendedmode from suspend
to shutdown when that unsafe value is present. It preserves the existing idle
timers and all unrelated settings. KNULLI performs a graceful shutdown so
supported emulators can auto-save normally.
The visible version label is in the Ports entries and the status report;
it does not rename official KNULLI's main menu or claim a custom firmware.

POWER FIX AND CHECK
The supplied report showed that the official 2026-05-10 G350 build called
pm-suspend on a short press, then booted again instead of resuming. CozOS 0.3
uses a screen-off sleep instead: it mutes audio, pauses EmulationStation and
active emulator processes, lowers the CPU governor, and turns off the display.
It does not enter the broken kernel suspend state. A second short press restores
the CPU, processes, display and prior mute state. This uses more power than a
working hardware suspend, but avoids the observed reboot. Hold Power for two
seconds for normal shutdown.

The screen-off sleep and wake behavior has now been physically tested on the
target G350. Launch "CozOS 0.3 - Status" whenever a diagnostic report is needed.

STATUS / RESULTS
Launch the Status entry. A terminal dialog is used when available.
Some Ports frontends do not show shell text. In that case the authoritative
result is saved at system/cozos/last-action.txt, and the detailed report is at
system/cozos/report.txt. There is no background daemon or permanent overlay.

REMOVE
Launch "CozOS 0.3 - Remove", then reboot. It restores the original user config
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
If 0.3 changed the idle setting, removal restores its previous value. For
manual recovery, Power Management can safely be set to Extended Mode: Shutdown
or None; do not select Suspend on this G350 build.
Keep a copy of any subsequently edited config before manual recovery.

VALIDATION AND LIMITS
Tested locally: config transformation; preservation of unrelated and FN+Power
bindings; install/remove with and without existing overrides; upgrade from 0.1;
refusal on unknown hardware/unsupported hooks; repeat installation; protection
of later edits; power-button short/long control flow; shell syntax.
Brightness and screen-off sleep/wake were physically tested successfully on
the target G350. The 0.3 idle-safety change uses KNULLI's documented graceful
shutdown mode and the exact installed configuration. Boot rumble begins before
the writable user overlay starts, so this package cannot safely fix it. A
graphical brightness status bar is not included because KNULLI's installed
brightness handler exposes no supported on-screen-display interface.

SOURCE REFERENCES
Reviewed source: UnknownApe1/CozOS-G350 branch cozzios-g350, September 16, 2026.
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/etc/init.d/S50triggerhappy
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/package/system/knulli-triggerhappy/conf/rk3326/multimedia_keys_G350.conf
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/usr/bin/power-button
https://github.com/UnknownApe1/CozOS-G350/blob/cozzios-g350/board/fsoverlay/usr/bin/knulli-suspend

The overlay implementation is original and licensed under MIT (LICENSE.txt).
