#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

MODULE = (Path(__file__).resolve().parents[1] /
          'overlay/g350/roms/ports/cozos/control_center.py')
SPEC = importlib.util.spec_from_file_location('cozos_control_center', MODULE)
cc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cc)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        cc.ROOT = self.root
        cc.STATE = self.root / 'userdata/system/cozos'
        cc.BACKUPS = cc.STATE / 'backups'
        for relative in cc.BACKUP_PATHS[:2]:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(relative + '=original\n')

    def tearDown(self):
        self.temp.cleanup()

    def test_round_trip_with_pre_restore_backup(self):
        rc, _ = cc.create_backup()
        self.assertEqual(rc, 0)
        target = self.root / cc.BACKUP_PATHS[0]
        target.write_text('changed=yes\n')
        rc, _ = cc.restore_latest()
        self.assertEqual(rc, 0)
        self.assertIn('original', target.read_text())
        self.assertTrue(list(cc.BACKUPS.glob('CozOS-G350-pre-restore-*.zip')))

    def test_rejects_unapproved_path(self):
        cc.BACKUPS.mkdir(parents=True, exist_ok=True)
        path = cc.BACKUPS / 'CozOS-G350-settings-99999999-999999Z.zip'
        payload = b'unsafe'
        manifest = {'format': 1, 'files': [{'path': '../../etc/shadow',
                    'sha256': cc.digest(payload), 'mode': 0o644}]}
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('files/../../etc/shadow', payload)
        with self.assertRaises(RuntimeError):
            cc.validate_backup(path)


class OverlayIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_root = os.environ.get('COZOS_ROOT')
        os.environ['COZOS_ROOT'] = str(self.root)
        cc.ROOT = self.root
        cc.STATE = self.root / 'userdata/system/cozos'
        cc.BACKUPS = cc.STATE / 'backups'

        fixtures = {
            'sys/firmware/devicetree/base/model': 'BATLEXP G350\0',
            'sys/class/graphics/fb0/virtual_size': '640,480\n',
            'etc/init.d/S50triggerhappy':
                '/userdata/system/configs/multimedia_keys.conf\n',
            'etc/init.d/S03system-splash':
                '/usr/share/knulli/splash/boot-logo-${resolution}.png\n',
            'usr/bin/volume-button': 'case "$1" in\nbriup) ;;\nbridown) ;;\nesac\n',
            'usr/bin/knulli-brightness': '#!/bin/sh\n',
            'etc/triggerhappy/triggers.d/multimedia_keys.conf':
                'KEY_VOLUMEUP 1 /usr/bin/volume-button volup\n'
                'KEY_VOLUMEUP 0 /usr/bin/volume-button-release\n'
                'KEY_VOLUMEDOWN 1 /usr/bin/volume-button voldown\n'
                'KEY_VOLUMEDOWN 0 /usr/bin/volume-button-release\n',
            'boot/knulli-boot.conf': 'splash.screen.enabled=0\n',
            'userdata/system/knulli.conf': 'global.audio_latency=80\n',
            'userdata/splash/original.png': self.fake_png(b'userdata-original'),
            'usr/share/knulli/splash/boot-logo-640x480.png':
                self.fake_png(b'rootfs-original'),
        }
        for relative, payload in fixtures.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(payload, bytes):
                path.write_bytes(payload)
            else:
                path.write_text(payload)

    @staticmethod
    def fake_png(tail):
        return (b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x0dIHDR' +
                (640).to_bytes(4, 'big') + (480).to_bytes(4, 'big') + tail)

    def tearDown(self):
        if self.old_root is None:
            os.environ.pop('COZOS_ROOT', None)
        else:
            os.environ['COZOS_ROOT'] = self.old_root
        self.temp.cleanup()

    def test_control_center_install_status_and_complete_rollback(self):
        original_rootfs = (self.root /
            'usr/share/knulli/splash/boot-logo-640x480.png').read_bytes()
        rc, message = cc.install_or_repair()
        self.assertEqual(rc, 0, message)
        installed = json.loads((cc.STATE / 'installed.json').read_text())
        self.assertEqual(installed['version'], cc.VERSION)
        self.assertTrue((self.root /
            'userdata/system/configs/multimedia_keys.conf').exists())
        rc, report = cc.status()
        self.assertEqual(rc, 0, report)
        self.assertIn('Installed version: ' + cc.VERSION, report)
        rc, message = cc.remove_cozos()
        self.assertEqual(rc, 0, message)
        self.assertFalse((cc.STATE / 'installed.json').exists())
        self.assertEqual((self.root /
            'usr/share/knulli/splash/boot-logo-640x480.png').read_bytes(),
            original_rootfs)


if __name__ == '__main__':
    unittest.main()
