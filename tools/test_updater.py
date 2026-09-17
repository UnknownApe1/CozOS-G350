import hashlib, importlib.util, json, os, tempfile, unittest, zipfile
from pathlib import Path

MODULE=Path(__file__).resolve().parents[1]/'overlay/g350/roms/ports/cozos/updater.py'


def load(root):
    os.environ['COZOS_ROOT']=str(root)
    spec=importlib.util.spec_from_file_location('cozos_updater_test',MODULE)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def make_update(path,version='0.6.1',tamper=False,unsafe=False):
    files={'app/main.py':b'print("ok")\n','app/updater.py':('VERSION="'+version+'"\n').encode()}
    manifest={'version':version,'files':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}
    if tamper: manifest['files']['app/updater.py']='0'*64
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('cozos-update/VERSION',version+'\n')
        z.writestr('cozos-update/MANIFEST.json',json.dumps(manifest))
        for k,v in files.items(): z.writestr('cozos-update/'+k,v)
        if unsafe: z.writestr('cozos-update/app/../../escape.txt','bad')


class UpdaterTests(unittest.TestCase):
    def test_install_and_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); mod=load(root)
            old=mod.APPS/'0.6.0'; old.mkdir(parents=True)
            (old/'main.py').write_text('old')
            (old/'updater.py').write_text('old')
            mod.ACTIVE.parent.mkdir(parents=True,exist_ok=True); mod.ACTIVE.write_text('0.6.0\n')
            pkg=root/'good.zip'; make_update(pkg)
            version,previous=mod.install_package(pkg)
            self.assertEqual((version,previous),('0.6.1','0.6.0'))
            self.assertEqual(mod.current_version(),'0.6.1')
            self.assertEqual(mod.rollback(),'0.6.0')

    def test_tampered_package_never_switches_active_version(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); mod=load(root)
            mod.ACTIVE.parent.mkdir(parents=True,exist_ok=True); mod.ACTIVE.write_text('0.6.0\n')
            pkg=root/'bad.zip'; make_update(pkg,tamper=True)
            with self.assertRaises(RuntimeError): mod.install_package(pkg)
            self.assertEqual(mod.current_version(),'0.6.0')

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); mod=load(root)
            pkg=root/'unsafe.zip'; make_update(pkg,unsafe=True)
            with self.assertRaises(RuntimeError): mod.inspect_package(pkg)

    def test_external_sha_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); mod=load(root)
            pkg=root/'good.zip'; make_update(pkg)
            with self.assertRaises(RuntimeError): mod.install_package(pkg,expected_sha256='0'*64)

    def test_semantic_version_ordering(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); mod=load(root)
            self.assertGreater(mod.version_key('0.10.0'),mod.version_key('0.9.9'))
            for version in ('0.9.9','0.10.0'):
                pkg=mod.UPDATES/('CozOS-G350-Update-'+version+'.zip')
                pkg.parent.mkdir(parents=True,exist_ok=True); make_update(pkg,version=version)
            self.assertEqual(mod.inspect_package(mod.newest_local()),'0.10.0')

if __name__=='__main__': unittest.main()
