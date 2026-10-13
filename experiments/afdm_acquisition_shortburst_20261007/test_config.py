"""Exact frozen cohort accounting, not performance sampling."""
import hashlib
import json
import unittest

from . import protocol, study


class ConfigContract(unittest.TestCase):
    def test_one_cell_counts_and_private_recorder(self):
        payload = study.CONFIG_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), study.CONFIG_SHA256)
        c = json.loads(payload)
        self.assertEqual((c['Ns'], c['T'], c['snr_db'], c['groups_per_cell']), ([64], 2, [5], 256))
        groups = len(c['Ns'])*len(c['snr_db'])*c['groups_per_cell']
        self.assertEqual(groups*3*c['T'], c['phases']['P']['new_observations'])
        self.assertEqual(groups*3*c['T']*64, 98304)
        self.assertEqual(groups*9, 2304)
        self.assertEqual(groups*3*(1024+32), 811008)
        self.assertEqual(groups*3*(1024+32)*48, 38928384)
        self.assertEqual(sum(p['wall_seconds'] for p in c['phases'].values()), 900)
        self.assertEqual(c['contract']['max_geometry_probes'], 0)
        self.assertEqual(protocol.adapter().PACKAGE, protocol.PACKAGE)
        self.assertNotEqual(protocol.frozen.PACKAGE, protocol.PACKAGE)


if __name__ == '__main__':
    unittest.main()
