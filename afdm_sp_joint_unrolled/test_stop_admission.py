"""Development must refuse failed engineering or changed receiver algorithms."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from .bottleneck_pilot import sha
from .trans_next_stop_run import execute


class StopAdmissionTests(unittest.TestCase):
    def check_rejected(self, status, source, pattern):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root/'manifest.json'
            manifest.write_text(json.dumps(source))
            admission = root/'admission.json'
            admission.write_text(json.dumps(dict(status=status, records=24, source_sha256=sha(manifest))))
            c = dict(schema='trans-stop-engineering-v1', stage='development', tag='run',
                device='cpu', threads=1, blocks=list(range(32)), snrs=[7, 8], F_limit=128,
                arms=[dict(name=n) for n in ('BP_STOP', 'SISO_STOP')],
                engineering_admission=str(admission), engineering_admission_sha256=sha(admission),
                engineering_source_manifest=str(manifest), engineering_source_sha256=sha(manifest))
            contract = root/'contract.json'
            contract.write_text(json.dumps(c))
            args = SimpleNamespace(root=root/'run', contract=contract, contract_sha256=sha(contract),
                                   source_manifest=manifest, source_sha256=sha(manifest))
            with self.assertRaisesRegex(ValueError, pattern):
                execute(args)
            self.assertFalse(args.root.exists())

    def test_failed_engineering_is_not_admission(self):
        self.check_rejected('FAILED', {}, 'incomplete stop engineering')

    def test_changed_feedback_algorithm_is_not_qualified(self):
        self.check_rejected('PASS', {'supplement_feedback.py': '0'*64}, 'changed qualified stop algorithm')


if __name__ == '__main__':
    unittest.main()
