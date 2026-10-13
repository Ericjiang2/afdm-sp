"""Shared physical AFDM delay-to-displacement mapping."""
import math


def physical_stride(N, c1):
    """Return physical 2*N*c1; the search width only orders candidate columns."""
    value = 2 * N * c1
    if not math.isfinite(value) or value < 0 or not float(value).is_integer():
        raise ValueError('physical stride 2*N*c1 must be a nonnegative integer')
    return int(value)
