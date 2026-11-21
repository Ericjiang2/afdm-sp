"""Check the mixed-width covariance against explicit AF-domain operators."""
import json
from pathlib import Path
import sys

import numpy as np

from screen import Widening, bank_for, context, m2

out = Path(sys.argv[1])
ctx = context(out)
full = bank_for(ctx)
bank = type(full)(64, round(2 * full.n * full.c1) / 128, .013, 6, m2.dpss_rx.tap_columns, m2.tapchannel)
widen = Widening(bank)
rng = np.random.default_rng(812)
def cn():
    return rng.normal(size=bank.n) + 1j * rng.normal(size=bank.n)

obs = dict(y=cn(), pilot=cn(), sigma2=.22)
mu, v = cn(), rng.uniform(.001, .8, bank.n)
groups = (1, 12, 33)
taps = [dict(delay=int(bank.delay[g]), c=int(bank.center[g]), W=.5, D=3) for g in groups]
_, ch, gamma = widen.fit(obs, mu, v, taps)
ref = bank.channel(groups, bank.prepare(obs, mu, v))
np.testing.assert_allclose(ch.gains, ref.gains, atol=1e-12, rtol=1e-12)
taps[1].update(c=0, W=2.5, D=8)
_, ch, gamma = widen.fit(obs, mu, v, taps)
operators = [m2.tapchannel.tap_matrix(m2.tapchannel.make_tap_channel(
    bank.n, bank.c1, bank.c2, [delay], ch.tap_mods[:, i:i+1]))
    for i, delay in enumerate(ch.delays)]
expected = np.einsum('ian,jan,n->ij', np.asarray(operators).conj(), operators, v)
np.testing.assert_allclose(gamma, expected, atol=1e-11, rtol=1e-11)
rows = [json.loads(line) for line in (out / 'smoke' / 'rows-00.jsonl').read_text().splitlines()]
assert {r['family'] for r in rows} == {'U', 'G', 'J4'}
assert any(r['trace']['expanded'] for r in rows)
print(json.dumps(dict(mixed_width_gamma_max_error=float(np.abs(gamma - expected).max()),
                      smoke_rows=len(rows), expanded_smoke_rows=sum(bool(r['trace']['expanded']) for r in rows))))
