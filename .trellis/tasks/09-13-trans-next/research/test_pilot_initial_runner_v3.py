"""PILOT-02 audit-only recovery contracts; no initialization or channel calls."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np


SPEC=importlib.util.spec_from_file_location('pilot_initial_runner_v3',
    Path(__file__).with_name('pilot_initial_runner_v3.py'))
pilot=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(pilot)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PilotRecovery(unittest.TestCase):
    def test_saved_native_spectrum_matches_producer_dtype(self):
        A=np.array([[1,2+1j],[2,1-1j],[3,2-2j],[4,4+1j]],dtype=np.complex64)
        native_norms=np.linalg.norm(A,axis=0)
        native_eigenvalues=np.linalg.eigvalsh((A/native_norms).conj().T@(A/native_norms))
        D=A.astype(np.complex128)
        double_gram=D.conj().T@D
        checked,G=pilot.verify_native_gram(A,double_gram,native_norms,native_eigenvalues)
        np.testing.assert_array_equal(checked,D)
        np.testing.assert_array_equal(G,double_gram)
        double_norms=np.linalg.norm(D,axis=0)
        self.assertGreater(np.linalg.norm(double_norms-native_norms),1e-9*np.linalg.norm(double_norms))
        with self.assertRaises(FloatingPointError):
            pilot.verify_native_gram(A,double_gram,double_norms,native_eigenvalues)

    def test_recover_closed_reservation_ledger_without_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'runs'/'pilot'/'engineering';out.mkdir(parents=True)
            clock=1.
            for number in range(1,21):
                kinds=('A',) if number>16 else ('E','A')
                for kind in kinds:
                    token=f'{kind}-{number:05d}'
                    identity=dict(token=token,kind=kind,block=0,snr=7,split='engineering',arm='P02')
                    (out/(token+'-reserve.json')).write_text(json.dumps(dict(identity,reserved_at=clock)))
                    clock+=1
                    record=dict(identity,seconds=.1,CPU_seconds=.1,scores={})
                    (out/(token+'-result.json')).write_text(json.dumps(record))
            failure=dict(status='FAILED',stage='engineering',calls={'A':20,'E':16},active=None)
            (out/'failure.json').write_text(json.dumps(failure))
            entries,saved_failure=pilot.recovery_records(out,root,digest)
            self.assertEqual(len(entries),36)
            self.assertEqual(entries[0]['kind'],'E')
            self.assertEqual(entries[-1]['kind'],'A')
            self.assertEqual(saved_failure,failure)
            self.assertEqual(entries[0]['sha256'],digest(entries[0]['record']))
            failure['active']={'token':'E-00017'}
            (out/'failure.json').write_text(json.dumps(failure))
            with self.assertRaises(ValueError):
                pilot.recovery_records(out,root,digest)


if __name__=='__main__':unittest.main()
