"""Recorder/config/statistics fixtures; no RNG, physical channel or pilot run."""
from pathlib import Path
import tempfile
import unittest

import numpy as np

from . import protocol
from .config import load_config
from .study import array_hash, paired_interval, wrapped_error


class Contracts(unittest.TestCase):
    def test_config_and_count_contract(self):
        config = load_config()
        groups = len(config['Ns'])*len(config['Ts'])*len(config['snr_db'])*config['groups_per_cell']
        vectors = len(config['Ns'])*sum(config['Ts'])*len(config['snr_db'])*config['groups_per_cell']*3
        scalars = sum(config['Ns'])*sum(config['Ts'])*len(config['snr_db'])*config['groups_per_cell']*3
        self.assertEqual(groups, config['paired_groups'])
        self.assertEqual(vectors, config['new_observations'])
        self.assertEqual(scalars, config['new_complex_scalars'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'modified.json'
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'frozen SHA-256'):
                load_config(path)

    def test_paired_cell_variance_and_modular_errors(self):
        report = paired_interval(np.array([[1., 0.], [1., 0.]]))
        self.assertEqual(report['mean'], .5)
        self.assertAlmostEqual(report['standard_error']**2, .125)
        self.assertAlmostEqual(wrapped_error(.1, 3.9, 4.), .2)
        self.assertNotEqual(array_hash(np.array([1., 2.])), array_hash(np.array([[1., 2.]])))

    def test_source_guard_and_private_adapter(self):
        self.assertEqual(protocol.adapter().PACKAGE, protocol.PACKAGE)
        self.assertNotEqual(protocol.frozen.PACKAGE, protocol.PACKAGE)
        with tempfile.TemporaryDirectory(dir=protocol.PACKAGE) as directory:
            source = Path(directory)/'fixture.py'
            source.write_text('fixture = True\n')
            with self.assertRaisesRegex(ValueError, 'uncommitted project source'):
                protocol.committed_project_sources([source])


if __name__ == '__main__':
    unittest.main()
