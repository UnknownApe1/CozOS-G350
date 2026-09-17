#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
LAUNCHER = REPO / 'overlay/g350/roms/ports/CozOS Control Center.sh'


class LauncherTests(unittest.TestCase):
    def test_non_tty_ports_launch_uses_vaixterm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ports = root / 'ports'
            bin_dir = root / 'bin'
            (ports / 'cozos').mkdir(parents=True)
            bin_dir.mkdir()
            shutil.copy2(LAUNCHER, ports / LAUNCHER.name)
            (ports / 'cozos/control_center.py').write_text('raise SystemExit(0)\n')
            fake = bin_dir / 'vaixterm'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$VAIXTERM_LOG"\n')
            fake.chmod(0o755)
            log = root / 'vaixterm-args.txt'
            environment = os.environ.copy()
            environment['PATH'] = str(bin_dir) + os.pathsep + environment['PATH']
            environment['VAIXTERM_LOG'] = str(log)
            result = subprocess.run([str(ports / LAUNCHER.name)], stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, env=environment, timeout=5, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            arguments = log.read_text().splitlines()
            self.assertEqual(arguments[:8], ['-w', '640', '-h', '480', '--no-credit',
                                              '--force-full-render', '-e', 'python3 "' +
                                              str(ports / 'cozos/control_center.py') + '"'])


if __name__ == '__main__':
    unittest.main()
