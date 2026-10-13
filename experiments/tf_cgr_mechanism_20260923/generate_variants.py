"""Generate observed-only detector variants from one SHA-bound native source.

The generated modules live beside this script. Frozen source bytes are never edited.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sp_afdm_native_joint_20260921/src/twofft.py'
EXPECTED = 'c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0'
OLD = 'rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)'
STATE = 'if record_states:states.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_text(mode: str, source: Path = SOURCE) -> str:
    if sha(source) != EXPECTED:
        raise ValueError('native twofft source differs from reviewed SHA; reconcile before generation')
    if mode not in ('base', 'cgr', 'sham'):
        raise ValueError('unknown detector variant')
    original = source.read_text()
    if original.count(OLD) != 1 or original.count(STATE) != 1 or original.count('    h=c.gains.copy();vh=1/P') != 1:
        raise ValueError('ambiguous native source anchors')
    if mode == 'cgr':
        expression = 'rh=h+vq*(Bb.conj().T@st-(gain_R@hb)*sv*n*vx)'
        setup = '    gain_R=o.R\n'
    elif mode == 'sham':
        expression = 'rh=h+vq*(Bb.conj().T@st-(gain_R@hb)*sv*n*vx)'
        setup = ('    signs=np.ones(P)\n'
                 '    for delay in np.unique(c.delays):\n'
                 '        group=np.flatnonzero(c.delays==delay)\n'
                 '        signs[group]=(-1.)**np.arange(group.size)\n'
                 '    gain_R=signs[:,None]*o.R*signs[None,:]\n')
    else:
        expression = OLD
        setup = '    gain_R=o.R\n'
    original = original.replace('    h=c.gains.copy();vh=1/P', setup+'    h=c.gains.copy();vh=1/P')
    original = original.replace(OLD, 'h_pre=h.copy(); '+expression)
    observed = ('if record_states:states.append(dict(h_pre=h_pre,h=h.copy(),hbar=hb.copy(),'
                'x=x.copy(),xbar=xb.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),'
                'rx=rx.copy(),app=app.copy(),extrinsic=ext.copy(),vx=vx,vr=vr,vq=vq,'
                'vh=vh,alpha=sv,sv=sv,bar=bar,vp=vp,xbar_energy=float(np.vdot(xb,xb).real),'
                'gain_R=gain_R.copy(),physical_R=o.R.copy()))')
    return original.replace(STATE, observed)


def generate() -> dict[str, str]:
    receipt = {}
    for mode in ('base', 'cgr', 'sham'):
        path = Path(__file__).with_name(f'tf_{mode}.py')
        data = expected_text(mode).encode()
        if path.exists() and path.read_bytes() != data:
            raise FileExistsError(f'generated detector differs: {path}')
        if not path.exists():
            path.write_bytes(data)
        receipt[mode] = sha(path)
    return receipt


def verify(source: Path = SOURCE) -> dict[str, str]:
    receipt = {}
    for mode in ('base', 'cgr', 'sham'):
        path = Path(__file__).with_name(f'tf_{mode}.py')
        if not path.exists() or path.read_bytes() != expected_text(mode, source).encode():
            raise ValueError(f'{mode} detector is absent or differs from source-bound generation')
        receipt[mode] = sha(path)
    return receipt


if __name__ == '__main__':
    import json
    print(json.dumps(generate(), indent=2))
