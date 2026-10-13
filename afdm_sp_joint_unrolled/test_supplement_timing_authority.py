"""Timing range provenance tests using signed local fixtures, no simulation."""
import copy
import unittest

from . import supplement_timing_authority as authority
from . import test_supplement_timing_collection as fixtures

write = fixtures.write


class TimingAuthorityContracts(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TimingCollectionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.old = {'path': str(f.manifest), 'sha256': f.manifest_sha}
        self.value = copy.deepcopy(f.manifest_value)
        self.value.update(schema='COST02-timing-collection-manifest-v2',
            block_start=2, excluded_manifests=[self.old],
            catalogue={'fixture': 'fifteen methods'}, selection={'fixture': 'bound inputs'})
        self.path = f.root/'new-pilot.json'

    def sign(self, value, path):
        self.fixture.sign_manifest(value)
        return write(path, value)

    def test_new_pilot_excludes_whole_old_range_and_binds_authority(self):
        self.sign(self.value, self.path)
        result = authority.validate_boundary(self.value, self.path)
        self.assertEqual((result['block_start'], result['block_stop']), (2, 4))
        self.assertEqual(result['excluded_manifests'], {self.old['path']: self.old['sha256']})
        self.assertIn(self.old['path'], result['files'])
        self.assertTrue(any('authorization-' in p for p in result['files']))

    def test_generator_uses_same_v2_range_before_any_random_draw(self):
        from .supplement_data import _confirm_manifest
        digest = self.sign(self.value, self.path)
        token = {'frozen_manifest_path': str(self.path), 'frozen_manifest_sha256': digest}
        args = (token, self.value['protocol_sha256'], 'F_C', 'A2')
        checked = _confirm_manifest(*args, 2, 8, 'G0', timing_purpose='timing-pilot')
        self.assertEqual(checked['block_start'], 2)
        for block in (0, 1, 4):
            with self.subTest(block=block), self.assertRaises(ValueError):
                _confirm_manifest(*args, block, 8, 'G0', timing_purpose='timing-pilot')

    def test_missing_duplicate_overlap_and_tampered_history_rejected(self):
        for change in ('missing', 'duplicate', 'overlap', 'hash', 'foreign'):
            value = copy.deepcopy(self.value)
            if change == 'missing':
                value.pop('excluded_manifests')
            elif change == 'duplicate':
                value['excluded_manifests'].append(copy.deepcopy(self.old))
            elif change == 'overlap':
                value['block_start'] = 1
            elif change == 'hash':
                value['excluded_manifests'][0]['sha256'] = '0'*64
            else:
                foreign = copy.deepcopy(self.fixture.manifest_value)
                foreign['protocol_sha256'] = '0'*64
                path = self.fixture.root/'foreign.json'
                value['excluded_manifests'] = [{'path': str(path), 'sha256': self.sign(foreign, path)}]
            self.sign(value, self.path)
            with self.subTest(change=change), self.assertRaises(ValueError):
                authority.validate_boundary(value, self.path)

    def test_formal_uses_new_pilot_end_and_identical_catalogue_prior_source(self):
        digest = self.sign(self.value, self.path)
        formal = copy.deepcopy(self.value)
        formal.pop('excluded_manifests')
        formal.update(timing_purpose='timing-confirmation', block_start=4,
            n_by_snr={'7': 1024, '8': 1024, '9': 1024},
            pilot_manifest_path=str(self.path), pilot_manifest_sha256=digest)
        path = self.fixture.root/'formal.json'
        self.sign(formal, path)
        result = authority.validate_boundary(formal, path)
        self.assertEqual(result['block_start'], 4)
        self.assertEqual(set(result['excluded_manifests']), {self.old['path'], str(self.path)})
        for key in ('catalogue', 'selection', 'prior_by_snr', 'source_manifest'):
            changed = copy.deepcopy(formal)
            changed[key] = {'different': True}
            self.sign(changed, path)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'pilot'):
                authority.validate_boundary(changed, path)

    def test_expired_history_is_preserved_but_unsigned_changes_are_rejected(self):
        old = copy.deepcopy(self.fixture.manifest_value)
        old['runtime_deadline_unix'] = 1
        old['runtime_admitted_unix'] = 0
        old_path = self.fixture.root/'expired.json'
        self.value['excluded_manifests'] = [{'path': str(old_path), 'sha256': self.sign(old, old_path)}]
        self.sign(self.value, self.path)
        authority.validate_boundary(self.value, self.path)
        old['n_by_snr']['8'] = 3
        self.value['excluded_manifests'][0]['sha256'] = write(old_path, old)
        self.sign(self.value, self.path)
        with self.assertRaisesRegex(ValueError, 'authorization'):
            authority.validate_boundary(self.value, self.path)


if __name__ == '__main__':
    unittest.main()
