"""Deterministic audit fixtures, with no research observations or phase grids."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_collision_resolution import audit

TOLERANCES = {name:dict(atol=1e-9, rtol=1e-7) for name in
              ('algebra', 'score', 'finite_difference', 'linear_algebra', 'distance')}


class AuditTests(unittest.TestCase):
    def test_import_graph_has_no_teacher_or_reader(self):
        for name in ('collision_teacher', 'information_study', 'distance_reader'):
            self.assertNotIn('experiments.afdm_collision_resolution.'+name, sys.modules)

    def test_zero_mean_gaussian_Bessel_limit(self):
        m = np.zeros((1, 4), complex)
        b = np.array([[1, 2j, 0, 0]], complex)
        state = dict(m0=m, m1=b, m_mu=m, kappa=.3)
        y = np.array([[0, 0, 0, 0], [1+2j, -.5j, .7, -1]], complex)
        noise = .8
        result = audit.likelihood(y, state, noise)
        norm = np.sum(abs(y)**2, axis=1)
        expected = -4*np.log(np.pi*noise)-norm/noise
        np.testing.assert_allclose(result['logpdf'], expected, atol=1e-13)
        target = .3*(abs(y.conj()@b[0])**2/noise**2-np.sum(abs(b)**2)/noise)
        np.testing.assert_allclose(result['score'][:, 0], target)
        np.testing.assert_allclose(result['score'][:, 1:3], 0, atol=1e-14)
        np.testing.assert_allclose(result['score'][:, 3], -4+norm/noise)

    def test_Bessel_origin_has_closed_r_and_scale_scores(self):
        state = dict(m0=np.array([[1, 0, 0, 0]], complex),
                     m1=np.array([[0, 2, 0, 0]], complex),
                     m_mu=np.array([[.5, 0, 0, 0]], complex), kappa=.2)
        result = audit.likelihood(np.zeros((1, 4)), state, 2.)
        np.testing.assert_allclose(result['score'], [[-.3, -.5, -.5, -3.5]], atol=1e-14)

    def test_independent_geometry_invariants_and_exact_derivative(self):
        state = audit.geometry(.27, tau=1.3)
        np.testing.assert_allclose(state['daft']@state['daft'].conj().T, np.eye(4), atol=1e-14)
        self.assertEqual(state['m0'].shape, (64, 4))
        self.assertEqual(state['pdp'].shape, (138, 2))
        np.testing.assert_allclose(state['pdp'][:69, ::-1], state['pdp'][69:])
        np.testing.assert_allclose(state['pdp_weights'][:69], state['pdp_weights'][69:])
        np.testing.assert_allclose(np.vdot(state['w'], state['b']), 0, atol=1e-14)
        self.assertTrue(np.all(abs(state['w']) > 0))
        step = 1e-6
        difference = (audit.geometry(.27+step)['w']-audit.geometry(.27-step)['w'])/(2*step)
        np.testing.assert_allclose(state['w_dot'], difference, atol=3e-9, rtol=3e-9)
        np.testing.assert_allclose(np.mean(np.sum(abs(state['m1'])**2, axis=1)), 1.3*4)

    def test_truncated_polynomial_first_and_second_powers(self):
        m = np.array([[2+1j, 0, 0, 0], [0, 0, 0, 0]], complex)
        b = np.array([[1-1j, 0, 0, 0], [2j, 0, 0, 0]], complex)
        dm = np.array([[.3j, 0, 0, 0], [1, 0, 0, 0]], complex)
        base, mu, tangent = audit.signal_polynomial(m, b, dm, [1, 0, 0, 0])
        np.testing.assert_allclose(base, abs(m[:, 0])**2)
        np.testing.assert_allclose(mu, 2*np.real(m[:, 0].conj()*dm[:, 0]))
        np.testing.assert_allclose(tangent, abs(b[:, 0])**2-abs(m[:, 0])**2)
        base, mu, tangent = audit.signal_polynomial(m, b, dm, [2, 0, 0, 0])
        np.testing.assert_allclose(base, abs(m[:, 0])**4)
        np.testing.assert_allclose(mu, 4*abs(m[:, 0])**2*np.real(m[:, 0].conj()*dm[:, 0]))
        np.testing.assert_allclose(tangent, 4*abs(b[:, 0])**2*abs(m[:, 0])**2-2*abs(m[:, 0])**4)

    def test_exact_noise_moment_and_zero_tangent(self):
        zeros = np.zeros((1, 4), complex)
        state = dict(m0=zeros, m1=zeros, m_mu=zeros, kappa=1.)
        mean, derivative = audit.exact_moment(state, [2, 0, 0, 0], 3.)
        self.assertEqual(mean, 18.)
        np.testing.assert_array_equal(derivative, [0, 0, 0, 36])
        self.assertEqual(audit.exact_moment(state, [0, 0, 0, 0], 3.)[0], 1.)

    def test_projection_exact_known_residual_and_frozen_coefficient(self):
        x = np.arange(32, dtype=float)
        scores = np.column_stack([2*np.cos(x)+np.sin(x), np.cos(x), x, (-1.)**x])
        fit, _ = audit.information(scores[:16], 1e-10)
        test, residual = audit.information(scores[16:], 1e-10, fit['coefficient'])
        np.testing.assert_array_equal(test['coefficient'], fit['coefficient'])
        np.testing.assert_allclose(residual, scores[16:, 0]-scores[16:, 1:]@fit['coefficient'])
        system = dict(covariance=np.eye(4), derivatives=np.column_stack([np.ones(4), np.eye(4)[:, :3]]))
        moment = audit.analytic_projection(system, 4, 1e-10)
        np.testing.assert_allclose(moment['witness'], [0, 0, 0, 1], atol=1e-14)
        self.assertAlmostEqual(moment['effective'], 1.)

    def test_batch_SE_uses_eight_means(self):
        values = np.arange(16.)
        result = audit.batches(values)
        means = np.arange(.5, 16, 2)
        np.testing.assert_array_equal(result['batch_means'], means)
        self.assertAlmostEqual(result['batch_se'], np.std(means, ddof=1)/np.sqrt(8))
        with self.assertRaises(ValueError):
            audit.batches(np.arange(17.))

    def test_binary_bridge_and_tensor_identity(self):
        p, q = np.array([.75, .25]), np.array([.25, .75])
        values = audit.bridge(np.log(q/p))
        mixture = (p+q)/2
        self.assertAlmostEqual(mixture@values['tv'], .5)
        h2 = np.sum((np.sqrt(p)-np.sqrt(q))**2)
        self.assertAlmostEqual(mixture@values['hellinger_squared'], h2)
        for repeats in (1, 2, 8):
            self.assertAlmostEqual(audit.repeat_h2(h2, repeats), 2-2*np.sum(np.sqrt(p*q))**repeats)
        extreme = audit.bridge(np.array([-1e6, -1e-9, 0, 1e-9, 1e6]))
        np.testing.assert_allclose(extreme['hellinger_squared'][[1, 3]], 2.5e-19, rtol=1e-9)
        np.testing.assert_array_equal(extreme['tv'][[0, 2, 4]], [1, 0, 1])
        np.testing.assert_array_equal(audit.repeat_h2([0., 2.], 256), [0., 2.])

    def test_unequal_denominators_and_familywise_radius(self):
        result = audit.bridge_summary([0., 1.], [0., 0., 0., 1.], 1., .05, 224)
        self.assertEqual(result['estimate'], .375)
        self.assertEqual(result['null']['groups'], 2)
        self.assertEqual(result['alternative']['groups'], 4)
        expected = np.sqrt((1/2+1/4)*np.log(2*224/.05)/8)
        self.assertAlmostEqual(result['simultaneous']['radius'], expected)
        self.assertGreater(result['simultaneous']['radius'], result['pointwise']['radius'])

    def test_checks_keep_failures_and_detect_nested_tamper(self):
        checks = audit.Checks(TOLERANCES)
        checks.tree(dict(a=[1., 2.], flag=True), dict(a=[1., 3.], flag=False), 'fixture')
        self.assertEqual(len(checks.records), 2)
        self.assertTrue(all(not item['passed'] for item in checks.records))
        checks.close([1, np.nan], [1, 2], 'nonfinite')
        self.assertFalse(checks.records[-1]['passed'])
        checks.equal([[True]*24, [False, False], [70, 70], [0, 0]],
                     [[True]*24, [False, False], [70, 70], [0, 0]], 'ragged_physical_signature')
        self.assertTrue(checks.records[-1]['passed'])

    def test_bound_records_and_artifacts_reject_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root/'stage'
            folder.mkdir()
            manifest = root/'protected.json'
            manifest.write_text('{}')
            (folder/'raw.bin').write_bytes(b'fixture')
            (folder/'registration.json').write_text(json.dumps(dict(git_head='tiny-fixture')))
            artifacts = {'stage/raw.bin':audit.sha(folder/'raw.bin')}
            (folder/'attempt.json').write_text(json.dumps(dict(status='complete', artifact_sha256=artifacts)))
            config = dict(protected_manifest_sha256=audit.sha(manifest), protected_file_count=0,
                          inputs=dict(tiny=dict(path='stage', git_head='tiny-fixture', artifacts=artifacts,
                                                records={name:audit.sha(folder/name) for name in ('registration.json', 'attempt.json')})))
            with patch.object(audit, 'ROOT', root), patch.object(audit, 'PROTECTED', manifest):
                self.assertEqual(audit.verify_bindings(config)['tiny'], folder)
                (folder/'raw.bin').write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'bound artifact changed'):
                    audit.verify_bindings(config)
                broken = copy.deepcopy(config)
                broken['inputs']['tiny']['records']['attempt.json'] = 'wrong'
                with self.assertRaisesRegex(ValueError, 'bound source record changed'):
                    audit.verify_bindings(broken)


if __name__ == '__main__':
    unittest.main()
