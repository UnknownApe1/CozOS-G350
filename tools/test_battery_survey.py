import csv
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

SOURCE=Path(__file__).parents[1]/'overlay/g350/roms/ports/cozos/battery_survey.py'


def load(root):
    os.environ['COZOS_ROOT']=str(root)
    spec=importlib.util.spec_from_file_location('cozos_battery_test',SOURCE)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BatterySurveyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        supply=self.root/'sys/class/power_supply/rk817-battery'; supply.mkdir(parents=True)
        values={'type':'Battery','name':'rk817-battery','status':'Discharging','capacity':'83',
                'voltage_now':'3975000','current_now':'-420000','temp':'315',
                'present':'1','health':'Good','online':'0'}
        for name,value in values.items(): (supply/name).write_text(value+'\n')
        (supply/'uevent').write_text('POWER_SUPPLY_NAME=rk817-battery\nPOWER_SUPPLY_CAPACITY=83\n')
        model=self.root/'sys/firmware/devicetree/base/model'; model.parent.mkdir(parents=True)
        model.write_bytes(b'BATLEXP G350\0')
        proc=self.root/'proc'; proc.mkdir(); (proc/'uptime').write_text('123.45 67.89\n')
        etc=self.root/'etc'; etc.mkdir(); (etc/'os-release').write_text('NAME=KNULLI\n')
        (proc/'version').write_text('Linux test kernel\n')
        tmp=self.root/'tmp'; tmp.mkdir(); (tmp/'battery.percent').write_text('79\n')
        self.mod=load(self.root)

    def tearDown(self):
        os.environ.pop('COZOS_ROOT',None); self.temp.cleanup()

    def test_snapshot_records_driver_and_visible_percent_without_modifying_config(self):
        message=self.mod.snapshot()
        self.assertIn('battery-snapshot.json',message)
        report=json.loads((self.mod.STATE/'battery-snapshot.json').read_text())
        self.assertEqual(report['device_model'],'BATLEXP G350')
        self.assertEqual(report['sample']['driver_capacity_percent'],'83')
        self.assertEqual(report['sample']['knulli_visible_percent'],'79')
        self.assertEqual(report['sample']['voltage_now'],'3975000')
        self.assertFalse((self.root/'userdata/system/configs/batteryplus').exists())

    def test_status_reports_latest_session_and_sample_count(self):
        session=self.mod.SURVEYS/'20260918T120000Z'; session.mkdir(parents=True)
        with (session/'battery.csv').open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=self.mod.FIELDS); writer.writeheader()
            writer.writerow(self.mod.sample()); writer.writerow(self.mod.sample())
        self.mod.atomic(self.mod.ACTIVE_FILE,str(session).encode())
        report=self.mod.survey_status()
        self.assertIn('Battery survey logger: STOPPED',report)
        self.assertIn('Recorded samples: 2',report)

    def test_package_contains_metadata_samples_and_final_snapshot(self):
        session=self.mod.SURVEYS/'20260918T120000Z'; session.mkdir(parents=True)
        (session/'metadata.json').write_text('{}\n')
        (session/'battery.csv').write_text(','.join(self.mod.FIELDS)+'\n')
        self.mod.atomic(self.mod.ACTIVE_FILE,str(session).encode())
        target=Path(self.mod.package())
        self.assertTrue(target.is_file())
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(set(archive.namelist()),{
                'battery-survey/battery.csv','battery-survey/final-snapshot.json',
                'battery-survey/metadata.json'})

    def test_active_session_outside_cozos_state_is_rejected(self):
        outside=self.root/'outside'; outside.mkdir()
        self.mod.atomic(self.mod.ACTIVE_FILE,str(outside).encode())
        with self.assertRaisesRegex(RuntimeError,'outside CozOS state'):
            self.mod.package()

    def test_missing_battery_is_reported_without_writes_to_hardware(self):
        supply=self.root/'sys/class/power_supply/rk817-battery'
        for child in supply.iterdir(): child.unlink()
        supply.rmdir()
        with self.assertRaisesRegex(RuntimeError,'No battery power-supply'):
            self.mod.sample()


if __name__=='__main__': unittest.main()
