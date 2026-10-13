# The old negative screen did not test the new repeated-delay working regime

This is an inspection of supplied source, not a new replay of its historical results.

## Frozen map

`native/src/twofft.py`, SHA256
`c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0`:

```python
self.R=(c.delays[:,None]==c.delays[None,:])*dkernel(c.dopplers[None,:]-c.dopplers[:,None],n)
# channel power uses h^H R h
rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)
```

Thus forward scalar energy retains R, while gain self-reaction retains only its diagonal.
This is the declared approximation, not a newly discovered violation of its implementation specification.

## Already present stronger algorithms

`native/src/fast_bilinear.py` has a `coherent` variant with
`ch=o.weighted_gamma(v,sv)@hb`. Its header explicitly says it retains cross terms
from the P-BiG-AMP derivation before their large-system simplification.

`native/src/block_bilinear.py`, SHA256
`f57545a65e936add0ca23547e3eab78d5b2a099ec1d304c6e2f1d3e0155fce83`, already implements
full P-dimensional Gaussian gain covariance, the reaction `sv*n*vx*(R@hb)`,
and corresponding covariance contractions. Its Basis class explicitly supports
invertible gain-coordinate changes. These are not inventions of this investigation.

## What the earlier screens supplied to those algorithms

`native/tests/screen_block.py` calls `physical.refine(... max_paths=8, rounds=2)`
before each of its two coded rounds, for both `soft` and `mean` CE.
`screen_fastamp.py` and `screen_six_db.py` likewise use `physical.refine`.

`baseline/src/physical.py` calls `fit`, whose initializer is:

```python
unique=np.unique(lq)
energy=np.array([np.sum(abs(gq[lq==d])**2) for d in unique])
ls=unique[np.argsort(-energy)[:max_paths]]
centers=np.array([kq[np.flatnonzero(lq==d)[np.argmax(abs(gq[lq==d]))]] for d in ls])
```

Its subsequent optimization changes Doppler, not delay. Therefore its working paths
have distinct delays. For this geometry the physical operator Gram is exactly I.
The specific isotropic gain-reaction completion proposed now vanishes there.
The vector variant can still have other cross terms from nonuniform working moments;
this audit does NOT say the entire earlier coherent algorithm was identical to TF.

CSTATE, unlike that refit, permits repeated delays. The fresh packet independently
reports repeated working slots in 26/61, 6/6, and 4/5 remaining failures at 6/6.5/7 dB.
This is why testing the term in the new regime does not contradict the earlier null
screens. It does not prove causality or make full-covariance AMP novel.

All ten inspected source/cache files and their hashes are in `frozen_reference_manifest.json`.
They are copied from user-supplied archives solely for reproducibility.
