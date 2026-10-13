"""Synthetic contract tests; these do not generate scientific observations."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import supplement_scope as scope


def fixture(root):
    domains = {}
    spans = {'engineering': (32, 34), 'confirm': (0, 2048),
             'development': (192, 320), 'cost-warmup': (1537, 1547),
             'cost-measurement': (1547, 2059)}
    for purpose, (split, family) in scope.DOMAINS.items():
        start, stop = spans[purpose]
        domains[purpose] = dict(split=split, family=family, block_start=start,
            block_stop=stop, snrs=[7, 8] if purpose == 'development' else [7, 8, 9],
            arm_ids=list(scope.ARMS), max_F=scope.CAPS[purpose])
    ledger = root / 'ledger'
    ledger.mkdir()
    legacy = ledger / 'reservation-legacy.json'
    legacy.write_text(json.dumps({'campaign_id': scope.CAMPAIGN,
        'calls_reserved': {'F': 46530, 'T': 0, 'E': 0}, 'status': 'failed'}))
    return dict(schema=scope.SCHEMA, scope_id=scope.SCOPE_ID, campaign_id=scope.CAMPAIGN,
        status='frozen', physical_N=1024, deadline_unix=scope.DEADLINE,
        data_scopes=domains, admitted_purposes=list(domains), auxiliary_bytes_reserved=1000,
        resource_limits=dict(new_peak_bytes=200_000_000_000, cost_wall_seconds=36000,
            cpu_workers_max=32, cpu_headroom=16, threads_per_worker=1, gpu_workers_max=2),
        scope_lock=str(root / '.scope.lock'),
        ledger_paths={key: str(ledger) for key in scope.CAPS},
        history={'ledger_files': {str(legacy): scope.sha(legacy)},
                 'ledger_inventory': {str(ledger): [str(legacy)]}})


class ScopeContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.manifest = fixture(self.root)
        self.clock = patch.object(scope.time, 'time', return_value=scope.DEADLINE - 100)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def request(self, purpose='engineering', **kwargs):
        domain = self.manifest['data_scopes'][purpose]
        args = dict(split=domain['split'], purpose=purpose, family=domain['family'],
            arm='I1', block=domain['block_start'], snr=7, scenario='G0')
        args.update(kwargs)
        return scope.validate_request(self.manifest, **args)

    def reserve(self, out='run', **kwargs):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.manifest))
        identity = dict(split='engineering', family=None, block=32, snr_db=7, arm='I1', repeat=0)
        return scope.reserve(self.manifest, path, scope.sha(path), self.root / out,
            'engineering', [identity], bytes_reserved=kwargs.get('bytes_reserved', 1000))

    def test_all_purpose_boundaries_and_sealed_data(self):
        for purpose in scope.CAPS:
            with self.subTest(purpose=purpose):
                self.request(purpose)
                with self.assertRaises(ValueError):
                    self.request(purpose, block=self.manifest['data_scopes'][purpose]['block_stop'])
                with self.assertRaises(ValueError):
                    self.request(purpose, split='D_test')
                with self.assertRaises(ValueError):
                    self.request(purpose, scenario='G1')

    def test_no_legacy_development_reuse_or_cost_1024_silent_change(self):
        with self.assertRaises(ValueError):
            self.request('development', block=191)
        with self.assertRaises(ValueError):
            self.request('cost-warmup', block=1536)
        self.manifest['data_scopes']['cost-measurement']['block_stop'] += 512
        with self.assertRaises(ValueError):
            self.request('cost-measurement')

    def test_wrong_family_arm_snr_and_overlap(self):
        for kwargs in ({'family': 'F_C'}, {'arm': 'I2'}, {'snr': 10}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.request('confirm', **kwargs)
        self.manifest['data_scopes']['cost-measurement'].update(block_start=1546, block_stop=2058)
        with self.assertRaises(ValueError):
            self.request('cost-measurement')

    def test_expired_and_extended_deadline(self):
        for deadline in (scope.DEADLINE - 200, scope.DEADLINE + 1, float('nan')):
            self.manifest['deadline_unix'] = deadline
            with self.assertRaises(ValueError):
                self.request()

    def test_pending_purpose_cannot_generate_data(self):
        self.manifest['admitted_purposes'] = ['engineering']
        with self.assertRaises(ValueError):
            self.request('confirm')

    def test_duplicate_reservation_and_old_failure_unchanged(self):
        before = (self.root / 'ledger/reservation-legacy.json').read_bytes()
        row = self.reserve()
        self.assertEqual(row['calls_reserved']['F'], 1)
        with self.assertRaises(ValueError):
            self.reserve('retry')
        self.assertEqual(before, (self.root / 'ledger/reservation-legacy.json').read_bytes())

    def test_history_change_or_new_old_reservation_refuses(self):
        path = self.root / 'ledger/reservation-other-old.json'
        path.write_text('{}')
        with self.assertRaises(ValueError):
            self.reserve()
        path.unlink()
        (self.root / 'ledger/reservation-legacy.json').write_text('{}')
        with self.assertRaises(ValueError):
            self.reserve()

    def test_global_storage_reservation_refuses_overflow(self):
        with self.assertRaises(ValueError):
            self.reserve(bytes_reserved=200_000_000_000)


if __name__ == '__main__':
    unittest.main()
