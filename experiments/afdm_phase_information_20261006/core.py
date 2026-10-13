"""Observation-only fractional CFO and fourth-power integer correlation."""
import numpy as np


def waveform(n, c2):
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 2 or not np.isfinite(c2):
        raise ValueError('integer N>=2 and finite known c2 required')
    indices = np.arange(n)
    return (np.exp(-2j*np.pi*(2.5/n)*indices**2),
            np.exp(-2j*np.pi*c2*indices**2))


def fractional_scores(z, frequencies):
    samples = np.asarray(z, complex)
    frequencies = np.asarray(frequencies, float)
    if (samples.ndim != 2 or not len(samples) or samples.shape[1] < 2
            or frequencies.ndim != 1 or not len(frequencies)
            or not np.isfinite(samples).all() or not np.isfinite(frequencies).all()):
        raise ValueError('finite nonempty T-by-N samples and frequency vector required')
    index = np.arange(samples.shape[1])/samples.shape[1]
    values = []
    for frequency in frequencies:
        transformed = np.fft.fft(samples*np.exp(-2j*np.pi*frequency*index), axis=1, norm='ortho')
        values.append(np.mean(np.sum(abs(transformed)**4, axis=1)))
    result = np.asarray(values)
    if not np.isfinite(result).all():
        raise FloatingPointError('nonfinite fractional objective')
    return result


def estimate(y, row_chirp, column_chirp, *, method='analytic', grid_size=64,
             flat_relative=1e-12, tie_relative=1e-10):
    """Only Y and known waveform/numerical settings enter this estimator.

    FFT counts are N-vector transforms, including the final output and both
    template/data FFTs plus correlation IFFT. No shared template cache is used.
    """
    samples = np.asarray(y, complex)
    row, column = np.asarray(row_chirp, complex), np.asarray(column_chirp, complex)
    if (samples.ndim != 2 or not len(samples) or samples.shape[1] < 2
            or row.shape != (samples.shape[1],) or column.shape != row.shape
            or not np.isfinite(samples).all() or not np.isfinite(row).all()
            or not np.isfinite(column).all()
            or not np.allclose(abs(row), 1., rtol=0, atol=1e-12)
            or not np.allclose(abs(column), 1., rtol=0, atol=1e-12)):
        raise ValueError('finite observations and known unit-modulus chirps required')
    if not 0 < flat_relative < 1 or not 0 < tie_relative < 1:
        raise ValueError('positive numerical flat/tie tolerances required')
    if method not in {'analytic', 'grid'}:
        raise ValueError('unknown fractional estimator')
    if isinstance(grid_size, bool) or not isinstance(grid_size, int) or grid_size < 3:
        raise ValueError('grid size must be an integer >=3')
    t, n = samples.shape
    z = samples*row.conj()
    frequencies = np.arange(3)/3 if method == 'analytic' else np.arange(grid_size)/grid_size
    searched = fractional_scores(z, frequencies)
    constant = float(np.mean(searched))
    harmonic = complex(np.mean(searched*np.exp(-2j*np.pi*frequencies)))
    flat = abs(harmonic) <= flat_relative*max(1., float(np.mean(abs(searched))))
    if flat:
        fractional = 0.
    elif method == 'analytic':
        fractional = float(((np.pi-np.angle(harmonic))/(2*np.pi)) % 1.)
    else:
        fractional = float(frequencies[int(np.argmin(searched))])
    x = np.fft.fft(z*np.exp(-2j*np.pi*fractional*np.arange(n)/n), axis=1, norm='ortho')
    objective = float(np.mean(np.sum(abs(x)**4, axis=1)))
    moment = np.mean(x**4, axis=0)
    code = column**4
    correlation = np.fft.ifft(np.fft.fft(moment)*np.fft.fft(code).conj())
    scores = abs(correlation)
    if not np.isfinite(scores).all() or not np.isfinite(objective):
        raise FloatingPointError('nonfinite integer score or final objective')
    maximum = float(scores.max())
    exact_maxima = np.flatnonzero(scores == maximum)
    integer = int(exact_maxima[0])
    near_count = int(np.count_nonzero(maximum-scores <= tie_relative*maximum))
    near_tie = maximum == 0 or near_count > 1
    return dict(frequency=float((fractional+integer) % n), fractional=fractional, integer=integer,
                flat=bool(flat), near_tie=bool(near_tie), near_tie_count=near_count,
                identified=not (flat or near_tie), objective=objective,
                harmonic=[harmonic.real, harmonic.imag], harmonic_magnitude=float(abs(harmonic)),
                harmonic_constant=constant, fitted_minimum=constant-2*abs(harmonic),
                search_frequencies=frequencies, search_objectives=searched,
                fourth_power_mean=moment, integer_scores=scores,
                counts=dict(search_objective_evaluations=len(frequencies), final_objective_evaluations=1,
                            total_objective_evaluations=len(frequencies)+1,
                            search_fft_vectors=len(frequencies)*t, final_fft_vectors=t,
                            integer_fft_vectors=3, fft_vectors=(len(frequencies)+1)*t+3,
                            fft_vector_length=n))
