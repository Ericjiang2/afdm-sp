import unittest
from unittest.mock import patch

import numpy as np

import codelay
from run import compare_geometry, e1


class CodelayKernelTest(unittest.TestCase):
    def test_closed_form_all_routes_without_variance_fft(self):
        full = e1.load_variant()
        route = codelay.load(full)
        rng = np.random.default_rng(83)
        n = 64
        y = rng.normal(size=n) + 1j*rng.normal(size=n)
        x = rng.normal(size=n) + 1j*rng.normal(size=n)
        v = rng.uniform(.02, .5, n)
        u = np.full_like(v, v.mean())
        opts = dict(c1=9/(2*n), c2=.0003, ridge=.11, max_delay=7, max_edits=2, local_passes=2)
        paths = [full.Path(1,-.2), full.Path(1,1.3), full.Path(4,1.17)]
        xt = full.daft(x, opts['c1'], opts['c2'], True)
        _, ref_q, _, _, _, match = full._system(y, xt, u, paths, opts['c1'], opts['c2'], .11)
        fft = np.fft.fft

        def no_variance_fft(a, *args, **kwargs):
            if np.shape(a) == v.shape and np.isrealobj(a):
                raise AssertionError('variance FFT on the closed route')
            return fft(a, *args, **kwargs)

        for strategy in ('compact','direct','fallback'):
            kw = dict(opts, strategy='compact' if strategy == 'fallback' else strategy)
            failure = FloatingPointError('forced compact numerical fallback')
            if strategy == 'fallback':
                with patch.object(full, 'exchange_scores', side_effect=failure):
                    ref = full.reopen_geometry(y,x,u,paths,**kw)
            else:
                ref = full.reopen_geometry(y,x,u,paths,**kw)
            with patch.object(np.fft, 'fft', side_effect=no_variance_fft):
                _, q, _, _, _, gamma = route._system(y, xt, v, paths, opts['c1'], opts['c2'], .11)
                np.testing.assert_allclose(gamma, match, atol=1e-13)
                np.testing.assert_allclose(q, ref_q, atol=1e-13)
                if strategy == 'fallback':
                    with patch.object(route, 'exchange_scores', side_effect=failure):
                        got = route.reopen_geometry(y,x,v,paths,**kw)
                else:
                    got = route.reopen_geometry(y,x,v,paths,**kw)
            self.assertEqual(bool(got.diagnostics['numerical_fallback']), strategy=='fallback')
            compare_geometry(ref,got,np.vdot(y,y).real)

    def test_zero_uncertainty(self):
        full = e1.load_variant()
        route = codelay.load(full)
        x = np.ones(32,complex)
        paths = [full.Path(1,0.), full.Path(1,.4), full.Path(3,1.)]
        _, _, _, h, _, g = route._system(x, x, np.zeros(32), paths, 9/64, .001, .15)
        _, _, _, want, _, _ = full._system(x, x, np.zeros(32), paths, 9/64, .001, .15)
        np.testing.assert_array_equal(g, 0)
        np.testing.assert_array_equal(h, want)


class AnalysisTests(unittest.TestCase):
    def test_censored_resamples_are_retained(self):
        from analyze import crossing_summary, curve

        a = curve([[.01, 0.], [.03, .001], [.1, .05]], [500, 600], 400)
        b = curve([[.18, .003], [.001, 0.], [.1, .05]], [500, 600], 400)
        result = crossing_summary(a, b)
        self.assertEqual(result['point'][0], '-inf')
        self.assertTrue(np.isfinite(result['point'][1]))
        self.assertEqual(result['interval95'], ['-inf','+inf'])
        self.assertEqual(result['left']['right_censored'], 1)

    def test_main_grid_and_two_sided_discordance(self):
        import math
        from analyze import log_p_two_sided, main_keys

        keys = main_keys()
        self.assertEqual(len(keys), 13600)
        self.assertEqual(sum(k[2] == 650 for k in keys), 800)
        self.assertAlmostEqual(log_p_two_sided(14, 0), math.log10(2**-13))
        self.assertEqual(log_p_two_sided(0, 0), 0.)
