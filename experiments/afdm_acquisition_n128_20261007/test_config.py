"""Immutable workload and recorder contracts, without scientific generation."""
import hashlib
import json
import unittest

from . import protocol, study


class ConfigContract(unittest.TestCase):
    def test_counts_and_config_hash(self):
        data = study.CONFIG_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), study.CONFIG_SHA256)
        c = json.loads(data)
        self.assertEqual((c['Ns'], c['T'], c['snr_db'], c['groups_per_cell']), ([128], 2, [5], 256))
        self.assertEqual(c['phases']['D']['new_geometry_probes'], 2*130*127*32)
        self.assertEqual(c['phases']['P']['new_observations'], 256*2*2)
        self.assertEqual(256*2*(4096+512), 2359296)
        self.assertEqual(96*2359296, 226492416)
        self.assertEqual(protocol.adapter().PACKAGE, protocol.PACKAGE)


if __name__ == '__main__':
    unittest.main()
