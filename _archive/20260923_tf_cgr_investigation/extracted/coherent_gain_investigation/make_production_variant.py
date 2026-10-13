"""Make a separate, SHA-bound CGR or matched-spectrum sham module.
Never edits the frozen source. Run its original qualification suite afterwards.
"""
from pathlib import Path
import argparse,hashlib,json
EXPECTED='c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0'
OLD='rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)'
NEW='rh=h+vq*(Bb.conj().T@st-(gain_R@hb)*sv*n*vx)'

def make(source:Path,destination:Path,mode:str):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:
        raise ValueError('Source differs from inspected version. Reconcile source/equations; do not bypass this check.')
    if destination.exists() or source.resolve()==destination.resolve():
        raise FileExistsError('Choose a new separate output module.')
    text=raw.decode();anchor='    h=c.gains.copy();vh=1/P'
    if text.count(OLD)!=1 or text.count(anchor)!=1:raise ValueError('Ambiguous source anchors')
    init='    gain_R=o.R\n'
    if mode=='sham':
        init=('    signs=np.ones(P)\n'
              '    for delay in np.unique(c.delays):\n'
              '        group=np.flatnonzero(c.delays==delay)\n'
              '        signs[group]=(-1.)**np.arange(group.size)\n'
              '    gain_R=signs[:,None]*o.R*signs[None,:]\n')
    text=text.replace(anchor,init+anchor).replace(OLD,NEW)
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(text)
    receipt=dict(source_sha256=EXPECTED,output_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
      mode=mode,original_frozen_source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==EXPECTED,
      changed_update=NEW,unchanged='all priors, damping, scalar variances, data reaction, symbols, geometry, iterations, interface')
    destination.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2))
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--mode',choices=['reaction','sham'],default='reaction');a=p.parse_args()
    print(json.dumps(make(a.source,a.destination,a.mode),indent=2))
