"""Development admission requires the exact producer and recovered audit chain."""
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


SPEC=importlib.util.spec_from_file_location('pilot_initial_runner_v6',
    Path(__file__).with_name('pilot_initial_runner_v6.py'))
pilot=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(pilot)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PilotDevelopmentGate(unittest.TestCase):
    def test_sorted_loaded_terms_keep_six_producer_cross_keys(self):
        original=dict(map=np.array([.1+0j,.2j]),tail=np.array([.2+0j,.1j]),
            data=np.array([.3+0j,.3j]),noise=np.array([.4+0j,.4j]))
        loaded={key:original[key] for key in sorted(original)}
        cross={f'{a}:{b}':2*float(np.vdot(original[a],original[b]).real)
            for i,a in enumerate(pilot.ERROR_TERM_ORDER)
            for b in pilot.ERROR_TERM_ORDER[i+1:]}
        g=np.array([1.+0j,-1.+0j])
        error=dict(terms=loaded,squares={k:pilot.energy(v) for k,v in original.items()},
            cross={key:cross[key] for key in sorted(cross)},
            physical_affine=g+sum(original.values()))
        pilot.verify_four_vector_terms(error,g)
        error['cross']['data:map']=error['cross'].pop('map:data')
        with self.assertRaises(ValueError):
            pilot.verify_four_vector_terms(error,g)

    def test_engineering_producer_and_recovery_identities_bind_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            contracts=root/'contracts';contracts.mkdir()
            engineering_contract=contracts/'pilot-initial-engineering-v1.json'
            engineering_contract.write_text('{}')
            out=root/'runs'/'pilot-initial-engineering-v1'/'engineering';out.mkdir(parents=True)
            failure=out/'failure.json';failure.write_text('{"status":"FAILED"}')
            summary_path=out/'summary-v5.json'
            source_sha='a'*64
            summary=dict(status='COMPLETE',stage='engineering',producer_status='FAILED_after_all_calls',
                calls={'A':20,'E':16},records=[{} for _ in range(36)],
                recovery_new_initialization_CE=0,
                script_sha256=pilot.ENGINEERING_PRODUCER_V1_SHA256,
                recovery_script_sha256='b'*64,
                original_failure_sha256=digest(failure),source_sha256=source_sha,
                contract_sha256=digest(engineering_contract))
            summary_path.write_text(json.dumps(summary))
            evidence=root/'evidence';evidence.mkdir()
            receipt_path=evidence/'pilot-initial-engineering-v1-engineering-raw-audit-v5.json'
            receipt=dict(status='PASS',saved_records=36,actual_new_initialization_CE=16,
                audit_new_initialization_CE=0,
                producer_script_sha256=pilot.ENGINEERING_PRODUCER_V1_SHA256,
                recovery_script_sha256='b'*64,
                summary_sha256=digest(summary_path),original_failure_sha256=digest(failure),
                source_sha256=source_sha,contract_sha256=digest(engineering_contract))
            receipt_path.write_text(json.dumps(receipt))
            contract=dict(engineering_summary=str(summary_path.relative_to(root)),
                engineering_receipt=str(receipt_path.relative_to(root)),
                engineering_contract_sha256=digest(engineering_contract),source_sha256=source_sha,
                engineering_recovery_v5_sha256='b'*64)
            contract['old_inputs']={str(path.relative_to(root)):digest(path)
                for path in (engineering_contract,summary_path,receipt_path,failure)}
            binding=pilot.verify_recovered_engineering(root,contract,digest)
            self.assertEqual(binding['summary_sha256'],digest(summary_path))
            self.assertEqual(binding['producer_script_sha256'],pilot.ENGINEERING_PRODUCER_V1_SHA256)
            receipt['recovery_script_sha256']='0'*64
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):
                pilot.verify_recovered_engineering(root,contract,digest)

    def test_native_spectrum_follows_stored_complex64_diagnostics(self):
        A=np.array([[1,2+1j],[2,1-1j],[3,2-2j],[4,4+1j]],dtype=np.complex64)
        norms=np.linalg.norm(A,axis=0)
        eig=np.linalg.eigvalsh((A/norms).conj().T@(A/norms))
        D=A.astype(np.complex128)
        _,G=pilot.verify_native_gram(A,D.conj().T@D,norms,eig)
        np.testing.assert_array_equal(G,D.conj().T@D)


if __name__=='__main__':unittest.main()
