#!/usr/bin/env python3
import hashlib, importlib.util, sys, tempfile, unittest
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
APP=REPO/'overlay/g350/roms/ports/cozos'
MODULE=APP/'rootsplash_060.py'


def png(tag):
    data=bytearray(b'\x89PNG\r\n\x1a\n'+b'\x00'*16)
    data[16:20]=(640).to_bytes(4,'big'); data[20:24]=(480).to_bytes(4,'big')
    return bytes(data)+tag


class RootSplashUpgradeTests(unittest.TestCase):
    def test_verified_older_cozos_splash_is_valid_upgrade_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); target=root/'boot-logo-640x480.png'; source=root/'new.png'; backup=root/'original.png'
            old=png(b'old-cozos'); new=png(b'new-cozos'); original=png(b'original-knulli')
            target.write_bytes(old); source.write_bytes(new); backup.write_bytes(original)
            old_sha=hashlib.sha256(old).hexdigest(); original_sha=hashlib.sha256(original).hexdigest()
            saved=[]
            sys.path.insert(0,str(APP))
            try:
                spec=importlib.util.spec_from_file_location('rootsplash_060_test',MODULE)
                mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            finally: sys.path.remove(str(APP))
            prior={'target':str(target),'backup':str(backup),'original_sha256':original_sha,
                   'installed_sha256':old_sha,'original_mode':0o644,'phase':'installed','version':'0.4.3'}
            mod.legacy.SOURCE=source; mod.legacy.select_target=lambda:(target,'640,480')
            mod.legacy.load_state=lambda:dict(prior); mod.legacy.save_state=lambda info:saved.append(dict(info))
            mod.legacy.save_overlay=lambda:'test-overlay-saved'
            message=mod.install()
            self.assertIn('0.6.2',message)
            self.assertEqual(target.read_bytes(),new)
            self.assertEqual(saved[-1]['original_sha256'],original_sha)
            self.assertEqual(saved[-1]['installed_sha256'],hashlib.sha256(new).hexdigest())

    def test_unknown_manual_splash_edit_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); target=root/'boot-logo-640x480.png'; source=root/'new.png'; backup=root/'original.png'
            target.write_bytes(png(b'manual')); source.write_bytes(png(b'new')); backup.write_bytes(png(b'original'))
            sys.path.insert(0,str(APP))
            try:
                spec=importlib.util.spec_from_file_location('rootsplash_060_manual_test',MODULE)
                mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            finally: sys.path.remove(str(APP))
            mod.legacy.SOURCE=source; mod.legacy.select_target=lambda:(target,'640,480')
            mod.legacy.load_state=lambda:{'target':str(target),'backup':str(backup),
                'original_sha256':'1'*64,'installed_sha256':'2'*64,'original_mode':0o644}
            with self.assertRaisesRegex(RuntimeError,'outside CozOS'): mod.install()

if __name__=='__main__': unittest.main()
