#!/usr/bin/env python3
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1] / 'overlay/g350/roms/ports/cozos'


class ToolsMigrationTests(unittest.TestCase):
    def load(self, root):
        os.environ['COZOS_ROOT'] = str(root)
        sys.path.insert(0, str(APP))
        for name in ('control_center_060', 'control_center', 'updater'):
            sys.modules.pop(name, None)
        return importlib.import_module('control_center_060')

    def tearDown(self):
        if str(APP) in sys.path:
            sys.path.remove(str(APP))
        os.environ.pop('COZOS_ROOT', None)

    def test_verified_tools_first_then_ports_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cc = self.load(root)
            cc.PORTS_LAUNCHER.parent.mkdir(parents=True)
            cc.PORTS_LAUNCHER.write_text(cc.PORTS_MARKER + '\n')
            message = cc.install_tools_launcher()
            self.assertIn('verified', message)
            self.assertTrue(cc.TOOLS_LAUNCHER.is_file())
            self.assertEqual(cc.TOOLS_LAUNCHER.stat().st_mode & 0o777, 0o755)
            self.assertFalse(cc.PORTS_LAUNCHER.exists())
            self.assertEqual(cc.TOOLS_LAUNCHER.read_bytes(), cc.tools_launcher_payload())
            cc.install_tools_launcher()  # idempotent repair

    def test_unknown_tools_file_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cc = self.load(root)
            cc.TOOLS_LAUNCHER.parent.mkdir(parents=True)
            cc.TOOLS_LAUNCHER.write_text('#!/bin/sh\necho user-file\n')
            cc.PORTS_LAUNCHER.parent.mkdir(parents=True)
            cc.PORTS_LAUNCHER.write_text(cc.PORTS_MARKER + '\n')
            with self.assertRaisesRegex(RuntimeError, 'refusing to overwrite'):
                cc.install_tools_launcher()
            self.assertIn('user-file', cc.TOOLS_LAUNCHER.read_text())
            self.assertTrue(cc.PORTS_LAUNCHER.exists())

    def test_complete_rollback_removes_only_verified_launchers_and_apps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cc = self.load(root)
            cc.PORTS_LAUNCHER.parent.mkdir(parents=True)
            cc.PORTS_LAUNCHER.write_text(cc.PORTS_MARKER + '\n')
            cc.install_tools_launcher()
            app = cc.updater.APPS / cc.VERSION
            app.mkdir(parents=True)
            (app / 'main.py').write_text('pass\n')
            cc.updater.ACTIVE.parent.mkdir(parents=True, exist_ok=True)
            cc.updater.ACTIVE.write_text(cc.VERSION + '\n')
            cc.remove_control_center_launchers()
            self.assertFalse(cc.TOOLS_LAUNCHER.exists())
            self.assertFalse(cc.updater.ACTIVE.exists())
            self.assertFalse(cc.updater.APPS.exists())


if __name__ == '__main__':
    unittest.main()
