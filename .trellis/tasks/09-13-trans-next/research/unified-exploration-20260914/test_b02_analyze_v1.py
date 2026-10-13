import numpy as np

from b02_analyze_v1 import fit_predict


def test_ridge_matches_augmented_least_squares_and_no_test_standardization():
    x = np.array([-3., 0., 1., 5.])
    y = np.array([[.1, .2], [.3, .1], [.2, .4], [.6, .2]])
    test = np.array([100., -50.])
    result, model = fit_predict(x, y, test)
    design = np.column_stack((np.ones(len(x)), (x - x.mean()) / x.std()))
    expected = np.linalg.lstsq(np.vstack((design, [0., 1.])), np.vstack((y, [0., 0.])), rcond=None)[0]
    np.testing.assert_allclose(result, np.column_stack((np.ones(2), (test-x.mean())/x.std())) @ expected)
    assert model['center'] == x.mean() and model['scale'] == x.std()
    assert result.max() > 1.  # No post-hoc probability clipping.


def test_constant_feature_is_explicit_fit_mean_even_for_shifted_test():
    y = np.array([[.1, .4], [.3, .2], [.2, .3]])
    result, model = fit_predict(np.ones(3), y, [0., 1000.])
    np.testing.assert_allclose(result, np.broadcast_to(y.mean(0), (2, 2)))
    assert model['constant_predictor'] and model['slope'] == [0., 0.]
