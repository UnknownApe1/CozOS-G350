CozOS G350 SD-card overlay 0.4.4
===============================

This is a targeted update for the BATLEXP G350 running KNULLI Scarab
2026-05-10. It is NOT a firmware image. Do not flash this ZIP.

WHY 0.4.3 DID NOT SHOW THE IMAGE
The 0.4.3 status report proved that /boot/logo_640x480.bmp was created and
checksum-verified, but this installed G350 build did not display it. KNULLI's
own boot-logo guide warns that its boot-partition bootlogo.bmp process is not
supported on every device. This G350 also had no original bootlogo.bmp.

WHAT 0.4.4 CHANGES
0.4.4 detects the image selected by the G350's installed
/etc/init.d/S03system-splash script. On this KNULLI family that is an existing
PNG under /usr/share/knulli/splash. It replaces only that exact file, then runs
KNULLI's official knulli-save-overlay command so the change survives reboot.

The installer also removes the checksum-verified but unused 0.4.3
/boot/logo_640x480.bmp file. All working CozOS features remain:
- FN + Volume Up/Down brightness control.
- Short Power press toggles screen-off sleep/wake.
- Hold Power about two seconds for normal shutdown.
- Safe automatic idle shutdown instead of broken hardware suspend.
- G350-oriented emulator, performance, scaling, latency and audio defaults.
- Existing explicit user settings, saves, save states, ROMs and BIOS are kept.

INSTALL / UPGRADE
1. Keep a backup of the working SD card.
2. Extract this ZIP on your computer.
3. Copy the CONTENTS of this ZIP's roms/ports folder into the existing
   roms/ports folder on the KNULLI SHARE/data partition. Allow folders and
   files to merge/replace the older CozOS files.
4. Put the card in the G350 and boot. Refresh the game list if required.
5. Open Ports and run "CozOS 0.4.4 - Install" once.
6. Wait for it to finish, then reboot normally through KNULLI.

The overlay-saving step can take several minutes. Do not power off while the
installer is running. You do not need to uninstall 0.4.3 first.

ROLLBACK
Run "CozOS 0.4.4 - Remove". It verifies the current CozOS image, restores the
exact original PNG from a SHA-256 checked backup, and saves the KNULLI overlay
again. It refuses to overwrite a later manual edit.

Emergency recovery: if a rootfs overlay ever prevents KNULLI from starting,
turn the device off, put SD1 in a computer, open the readable KNULLI/BATOCERA
partition, enter its boot folder, and delete the file named "overlay". This
discards every rootfs overlay modification, not ROMs, saves, or userdata.

STATUS / DIAGNOSTICS
Run "CozOS 0.4.4 - Status". Reports are written under:
  /userdata/system/cozos/report.txt
  /userdata/system/cozos/rootfs-splash-status.txt
  /userdata/system/cozos/rootfs-splash-last-action.txt  (only after an error)

KNOWN LIMIT
Boot rumble happens earlier than this user-space splash and is not changed.

Official KNULLI references:
  https://knulli.org/configure/customization/bootlogo/
  https://knulli.org/configure/patches-and-overlays/
