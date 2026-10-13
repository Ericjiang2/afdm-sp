"""Selection admission unit fixtures; not mechanism E2E evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from afdm_sp_joint_unrolled.direction_mechanism_run import select_recipe


class AdmissionTests(unittest.TestCase):
    def test_selection_file_is_hashed_and_bound_to_protocol(self):
        protocol={'design':{'recipes':[{'id':f'fixture-{i}','family':'fixture'} for i in range(8)]}}
        value={'status':'complete','protocol_sha256':'protocol-fixture',
               'selection':{'B_star_operational':'fixture-3'},'evidence_kind':'unit-fixture'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'selector.json';path.write_text(json.dumps(value))
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(select_recipe(path,digest,protocol,'protocol-fixture')['id'],'fixture-3')
            with self.assertRaises(ValueError):select_recipe(path,'a'*64,protocol,'protocol-fixture')
            with self.assertRaises(ValueError):select_recipe(path,digest,protocol,'different-protocol')
            for change in ({'status':'pending'},{'selection':{'B_star_operational':'unregistered'}}):
                wrong=dict(value,**change);path.write_text(json.dumps(wrong))
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):select_recipe(path,digest,protocol,'protocol-fixture')


if __name__=='__main__':unittest.main()
