"""Data-boundary regression tests with synthetic manifests, no frame generation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import supplement_scope as scope
from .supplement_data import SupplementData, _confirm_manifest, campaign_rng
from .test_supplement_scope import fixture


class DataScopeContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.manifest = fixture(self.root)
        auth = self.root / 'authorization.json'
        auth.write_text(json.dumps({'status': 'accepted', 'source': 'synthetic fixture',
                                    'authorized': ['synthetic contract test only']}))
        self.manifest.update(protocol_sha256='a' * 64,
            authorization={'status': 'accepted', 'evidence_path': str(auth),
                           'evidence_sha256': scope.sha(auth)})
        self.path = self.root / 'scope.json'
        self.data = SupplementData.__new__(SupplementData)
        self.data.protocol_sha256 = 'a' * 64
        self.rebind()
        clock = patch.object(scope.time, 'time', return_value=scope.DEADLINE - 100)
        clock.start()
        self.addCleanup(clock.stop)

    def rebind(self):
        self.path.write_text(json.dumps(self.manifest))
        self.token = {'frozen_manifest_path': str(self.path),
                      'frozen_manifest_sha256': scope.sha(self.path)}
        self.data.freeze_manifests = {'scope': self.token}

    def test_new_engineering_and_confirm_use_shared_authorization(self):
        result = self.data._request('engineering', 32, 7, arm_id='I1', scope_purpose='engineering')
        self.assertEqual(result['authorization_sha256'], self.manifest['authorization']['evidence_sha256'])
        self.data._request('confirm', 2047, 9, 'F_I', 'I1', scope_purpose='confirm')
        with self.assertRaises(ValueError):
            self.data._request('confirm', 2048, 9, 'F_I', 'I1', scope_purpose='confirm')

    def test_scope_cannot_fall_back_to_legacy_or_omit_purpose(self):
        with self.assertRaises(ValueError):
            self.data._request('engineering', 0, 7)
        self.data.freeze_manifests = {}
        with self.assertRaises(ValueError):
            self.data._request('engineering', 32, 7)
        with self.assertRaises(ValueError):
            self.data._request('engineering', 32, 7, arm_id='I1', scope_purpose='engineering')

    def test_missing_authorization_and_changed_hash_refuse(self):
        self.manifest['authorization']['status'] = 'pending'
        self.rebind()
        with self.assertRaises(ValueError):
            self.data._request('engineering', 32, 7, arm_id='I1', scope_purpose='engineering')
        self.path.write_text('{}')
        with self.assertRaises(ValueError):
            self.data._request('engineering', 32, 7, arm_id='I1', scope_purpose='engineering')

    def test_legacy_formal_minimum_1024_is_unchanged(self):
        self.manifest.update(schema='COST02-timing-family-manifest-v1', family='F_C',
            scenario='G0', timing_purpose='timing-confirmation', proceed_timing=True,
            n_by_snr={'7': 512, '8': 512, '9': 512}, arm_ids=['I1'], block_start=1537)
        # The existing v1 accepts None as its historical schema alias.
        self.manifest.pop('schema')
        self.rebind()
        with self.assertRaisesRegex(ValueError, 'at least 1024'):
            _confirm_manifest(self.token, 'a' * 64, 'F_C', 'I1', 1537, 7, 'G0',
                              timing_purpose='timing-confirmation')

    def test_snr_cannot_change_exogenous_identity(self):
        import numpy as np
        a = campaign_rng('confirm', 1, 'noise', family='F_I').normal(size=8)
        b = campaign_rng('confirm', 1, 'noise', family='F_I').normal(size=8)
        np.testing.assert_array_equal(a, b)
        with self.assertRaises(ValueError):
            campaign_rng('confirm', 1, 'noise', family='F_I', snr=7)


if __name__ == '__main__':
    unittest.main()
