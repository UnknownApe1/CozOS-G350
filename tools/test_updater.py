import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

SOURCE=Path(__file__).parents[1]/'overlay/g350/roms/ports/cozos/updater.py'


def load(root):
    os.environ['COZOS_ROOT']=str(root)
    spec=importlib.util.spec_from_file_location('cozos_updater_test',SOURCE)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_update(path,version='0.6.3',extra=None,corrupt_manifest=False,unsafe=False):
    files={
        'app/main.py':b'print("CozOS")\n',
        'app/updater.py':b'# updater\n',
        'app/control_center_060.py':b'# control center\n',
    }
    manifest_files={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
    if corrupt_manifest:
        manifest_files['app/main.py']='0'*64
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('cozos-update/VERSION',version+'\n')
        archive.writestr('cozos-update/MANIFEST.json',json.dumps({
            'version':version,'files':manifest_files},sort_keys=True))
        for name,data in files.items(): archive.writestr('cozos-update/'+name,data)
        if extra: archive.writestr('cozos-update/app/'+extra,b'not declared')
        if unsafe: archive.writestr('cozos-update/app/../../escape.txt',b'bad')
    return path


class Updater063Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.updater=load(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def seed_active(self,version='0.6.2'):
        target=self.updater.APPS/version
        target.mkdir(parents=True)
        (target/'main.py').write_text('old main\n')
        (target/'updater.py').write_text('old updater\n')
        self.updater.ACTIVE.parent.mkdir(parents=True,exist_ok=True)
        self.updater.ACTIVE.write_text(version+'\n')

    def test_upgrade_and_rollback_preserve_previous_version(self):
        self.seed_active()
        package=make_update(self.updater.UPDATES/'CozOS-G350-Update-0.6.3.zip')
        version,previous=self.updater.install_package(package)
        self.assertEqual((version,previous),('0.6.3','0.6.2'))
        self.assertEqual(self.updater.current_version(),'0.6.3')
        self.assertTrue((self.updater.APPS/'0.6.2/main.py').is_file())
        self.assertEqual(self.updater.rollback(),'0.6.2')

    def test_same_version_install_is_a_repair(self):
        self.seed_active('0.6.3')
        package=make_update(self.updater.UPDATES/'CozOS-G350-Update-0.6.3.zip')
        version,previous=self.updater.install_package(package)
        self.assertEqual((version,previous),('0.6.3',''))
        self.assertEqual((self.updater.APPS/'0.6.3/main.py').read_text(),'print("CozOS")\n')
        self.assertFalse((self.updater.APPS/'0.6.3.replaced').exists())

    def test_scans_ports_and_share_root(self):
        ports=make_update(self.root/'userdata/roms/ports/CozOS-G350-Update-0.6.3.ZIP')
        self.assertEqual(self.updater.newest_local(),ports)
        ports.unlink()
        share=make_update(self.root/'userdata/CozOS-G350-Update-0.6.3.zip')
        self.assertEqual(self.updater.newest_local(),share)

    def test_diagnostics_explain_rejected_zip(self):
        path=self.updater.UPDATES/'CozOS-G350-Update-broken.zip'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'not a zip')
        report=self.updater.local_scan_report()
        self.assertIn(str(path),report)
        self.assertIn('Rejected packages:',report)
        self.assertIn('File is not a zip file',report)

    def test_rejects_undeclared_payload(self):
        path=make_update(self.updater.UPDATES/'CozOS-G350-Update-0.6.3.zip',extra='surprise.py')
        with self.assertRaisesRegex(RuntimeError,'undeclared package files'):
            self.updater.inspect_package(path)

    def test_failed_repair_keeps_active_copy(self):
        self.seed_active('0.6.3')
        package=make_update(self.updater.UPDATES/'CozOS-G350-Update-0.6.3.zip',corrupt_manifest=True)
        with self.assertRaisesRegex(RuntimeError,'Checksum failed'):
            self.updater.install_package(package)
        self.assertEqual(self.updater.current_version(),'0.6.3')
        self.assertEqual((self.updater.APPS/'0.6.3/main.py').read_text(),'old main\n')

    def test_path_traversal_is_rejected(self):
        path=make_update(self.root/'unsafe.zip',unsafe=True)
        with self.assertRaisesRegex(RuntimeError,'Unsafe ZIP path'):
            self.updater.inspect_package(path)

    def test_external_sha_mismatch_is_rejected(self):
        path=make_update(self.root/'good.zip')
        with self.assertRaisesRegex(RuntimeError,'SHA-256'):
            self.updater.install_package(path,expected_sha256='0'*64)

    def test_semantic_version_ordering(self):
        self.assertGreater(self.updater.version_key('0.10.0'),self.updater.version_key('0.9.9'))
        for version in ('0.9.9','0.10.0'):
            make_update(self.updater.UPDATES/f'CozOS-G350-Update-{version}.zip',version=version)
        self.assertEqual(self.updater.inspect_package(self.updater.newest_local()),'0.10.0')


if __name__=='__main__': unittest.main()
