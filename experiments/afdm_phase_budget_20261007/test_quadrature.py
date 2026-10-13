"""Small deterministic engineering contracts; not acquisition evidence."""
import unittest
import copy
import json
import hashlib
import tempfile
from pathlib import Path

import numpy as np
from scipy.special import roots_legendre

from .audit import scalar_reference, validate_structure, validate_primary, validate_convergence
from .quadrature import fano, phase_information


class QuadratureContracts(unittest.TestCase):
    def test_zero_snr_has_zero_information(self):
        for value in phase_information(0., 16).values():
            self.assertAlmostEqual(value, 0., places=13)
        self.assertAlmostEqual(scalar_reference(0.)['phase'], 0., places=12)

    def test_invalid_inputs_fail(self):
        for gamma in (-1., float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                phase_information(gamma, 16)
        with self.assertRaises(ValueError):
            phase_information(1., True)

    def test_two_independent_integrals_small_fixture(self):
        direct = phase_information(.4, 40)
        reference = scalar_reference(.4)
        for key in ('phase', 'gaussian'):
            self.assertAlmostEqual(direct[key], reference[key], places=9)
        self.assertGreater(direct['phase'], 0)
        self.assertGreater(direct['radial'], 0)

    def test_fano_conditions_before_averaging(self):
        values = np.array([0., 1.])
        expected = .5*(1-np.log(2)/np.log(1024))
        self.assertAlmostEqual(float(fano(values, 128, 1024).mean()), expected)
        self.assertEqual(float(fano(values.mean(), 128, 1024)), 0.)

    def test_recorder_metadata_and_package_exist(self):
        from experiments.afdm_higher_order_information.protocol import _observations
        config = json.loads(Path(__file__).with_name('STUDY_CONFIG.json').read_text())
        self.assertEqual(_observations(config), 0)
        self.assertTrue(Path(__file__).with_name('__init__.py').is_file())

    def test_source_inventory_includes_deferred_binding(self):
        from . import study  # noqa: F401 -- explicit preload required by the launcher.
        from .protocol import import_inventory
        self.assertIn('experiments/afdm_coherent_structure_20261006/thread_binding.py',
                      import_inventory()['all_paths'])

    def test_audit_rejects_missing_or_shifted_rule_states(self):
        config = dict(rho_orders=[8, 16], hermite_orders=[8, 16],
                      rho_points=[.75, 1.25], snr_db=5, cases=[[128, 1024]])
        records = []
        for r in config['rho_orders']:
            nodes, weights = roots_legendre(r)
            for h in config['hermite_orders']:
                records.append(dict(rho_order=r, hermite_order=h, rho=(1+nodes/4).tolist(),
                                    weights=(weights/2).tolist(), values=[dict(phase=0., gaussian=0., radial=0.)]*r,
                                    bounds=[dict(samples=128, labels=1024, phase_fano=0., gaussian_fano=0., phase_average_first=0.)]))
        saved = dict(records=records, points=[dict(rho=r, gamma=10**.5*r*r, phase=0., gaussian=0., radial=0.) for r in config['rho_points']])
        validate_structure(saved, config)
        missing = copy.deepcopy(saved)
        missing['records'][0]['values'].pop()
        with self.assertRaisesRegex(ValueError, 'missing quadrature'):
            validate_structure(missing, config)
        shifted = copy.deepcopy(saved)
        shifted['records'][0]['rho'][0] += .001
        with self.assertRaisesRegex(ValueError, 'GL nodes'):
            validate_structure(shifted, config)
        cases = copy.deepcopy(saved)
        cases['records'][0]['bounds'] = []
        with self.assertRaisesRegex(ValueError, 'frozen sample'):
            validate_structure(cases, config)
        nan = copy.deepcopy(saved)
        nan['points'][0]['gaussian'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite point'):
            validate_structure(nan, config)
        config['fano_tolerance'] = .0003
        self.assertEqual(validate_convergence(records, config), 0.)
        changed = copy.deepcopy(records)
        changed[0]['bounds'][0]['gaussian_fano'] = .01
        with self.assertRaisesRegex(ValueError, 'four-resolution'):
            validate_convergence(changed, config)

    def test_primary_bytes_and_config_are_bound_before_integration(self):
        config = dict(phase='A', seed=0)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'results.json'
            registration = root/'registration.json'
            source.write_text('{}')
            registration.write_text(json.dumps(dict(config=dict(config, phase='Q'))))
            attempt = dict(status='complete', exit_code=0, artifact_sha256={
                str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, registration)})
            source.with_name('attempt.json').write_text(json.dumps(attempt))
            validate_primary(source, config)
            with self.assertRaisesRegex(ValueError, 'frozen registration'):
                validate_primary(source, dict(config, seed=1))
            source.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'result SHA256'):
                validate_primary(source, config)


if __name__ == '__main__':
    unittest.main()
