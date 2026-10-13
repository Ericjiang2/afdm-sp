"""Synthetic files only, no receiver calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('verify', Path(__file__).with_name('verify-i01-actual-bindings-v1.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))

class ActualBindingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        source = self.root / 'source-i01-development-v1/source/afdm_sp_joint_unrolled'
        source.mkdir(parents=True)
        for i in range(228):
            (source / f's{i}.py').write_text('# fixture\n')
        files = {}
        command = []
        for key, flag in [('protocol', '--protocol'), ('development_protocol', '--development-protocol'), ('quote', '--quote'), ('checkpoint', '--checkpoint')]:
            path = self.root / key
            path.write_text('fixture')
            files[key] = v.sha(path)
            command.extend([flag, str(path)])
        bindings = dict(files=files, source_sha256={p.name: v.sha(p) for p in source.iterdir()})
        self.ledger = self.root / 'i01-development-inputs-v1/i01-development-ledger'
        audit = dict(status='passed', F_audited=3456, bindings=bindings, code_sha256={}, batches=[])
        for start, stop in v.RANGES:
            root = self.root / f'i01-development-b{start:03d}-{stop:03d}-v1'
            ids = [[b, s, a] for b in range(start, stop) for s in (7, 8, 9) for a in v.ARMS]
            contract = dict(bindings=bindings, code_sha256={}, start=start, stop=stop,
                            identities=ids, calls_reserved=dict(E=0, F=len(ids), T=0),
                            max_full_calls=len(ids), ledger=str(self.ledger), config_sha256=str(start), command=command)
            write(root / 'contract.json', contract)
            write(root / 'summary.json', {})
            write(self.ledger / f'reservation-{start}.json', {k:x for k,x in contract.items() if k!='ledger'})
            (self.root / (root.name + '.exit')).write_text('0')
            audit['batches'].append(dict(root=str(root), F_audited=len(ids), proofs=[dict(identity=i) for i in ids], contract_sha256=v.sha(root/'contract.json'), summary_sha256=v.sha(root/'summary.json')))
        self.audit = self.root / 'audit.json'
        write(self.audit, audit)

    def test_complete_actual_files(self):
        self.assertEqual(v.verify(self.root, self.audit)['unique_F'], 3456)

    def test_changed_input(self):
        (self.root / 'checkpoint').write_text('changed')
        with self.assertRaises(ValueError): v.verify(self.root, self.audit)

    def test_changed_source(self):
        (self.root / 'source-i01-development-v1/source/afdm_sp_joint_unrolled/s0.py').write_text('changed')
        with self.assertRaises(ValueError): v.verify(self.root, self.audit)

    def test_extra_reservation(self):
        write(self.ledger / 'reservation-extra.json', {})
        with self.assertRaises(ValueError): v.verify(self.root, self.audit)

    def test_changed_reservation(self):
        write(self.ledger / 'reservation-0.json', {})
        with self.assertRaises(ValueError): v.verify(self.root, self.audit)

    def test_bad_raw_proof_identities(self):
        original = v.read(self.audit)
        for mode in ('empty', 'duplicate', 'wrong_batch'):
            changed = json.loads(json.dumps(original))
            proofs = changed['batches'][0]['proofs']
            if mode == 'empty':
                proofs.clear()
            elif mode == 'duplicate':
                proofs[-1] = proofs[0]
            else:
                proofs[0]['identity'][0] = 191
            write(self.audit, changed)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                v.verify(self.root, self.audit)

    def test_late_batch_failure(self):
        write(self.root / 'i01-development-b000-001-v1/batch-failure.json', {})
        with self.assertRaises(ValueError): v.verify(self.root, self.audit)

if __name__ == '__main__': unittest.main()
