#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]
LAUNCHER=REPO/'overlay/g350/roms/ports/CozOS Control Center.sh'


class LauncherTests(unittest.TestCase):
    def test_non_tty_ports_launch_bootstraps_versioned_app_and_uses_vaixterm(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); ports=root/'ports'; bin_dir=root/'bin'; state=root/'state'
            (ports/'cozos').mkdir(parents=True); bin_dir.mkdir()
            shutil.copy2(LAUNCHER,ports/LAUNCHER.name)
            (ports/'cozos/main.py').write_text('raise SystemExit(0)\n')
            (ports/'cozos/updater.py').write_text('VERSION="0.6.2"\n')
            fake=bin_dir/'vaixterm'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$VAIXTERM_LOG"\nprintf "%s\\n" "$SDL_GAMECONTROLLER_USE_BUTTON_LABELS" > "$VAIXTERM_ENV_LOG"\n')
            fake.chmod(0o755)
            log=root/'vaixterm-args.txt'; env_log=root/'vaixterm-env.txt'
            environment=os.environ.copy(); environment['PATH']=str(bin_dir)+os.pathsep+environment['PATH']
            environment['VAIXTERM_LOG']=str(log); environment['VAIXTERM_ENV_LOG']=str(env_log)
            environment['COZOS_STATE']=str(state)
            result=subprocess.run([str(ports/LAUNCHER.name)],stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                  env=environment,timeout=5,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((state/'active-version').read_text().strip(),'0.6.2')
            entry=state/'apps/0.6.2/main.py'
            self.assertTrue(entry.is_file())
            arguments=log.read_text().splitlines()
            expected='cd "'+str(state/'apps/0.6.2')+'" && python3 "'+str(entry)+'"'
            self.assertEqual(arguments[:8],['-w','640','-h','480','--no-credit','--force-full-render','-e',expected])
            self.assertEqual(env_log.read_text().strip(),'1')

if __name__=='__main__': unittest.main()
