"""Summarize verified exposed endpoints; no new experiment or significance gate."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def summarize(root):
    path = root/'raw/mechanism.json'
    rows = json.loads(path.read_text())['rows']
    ix = {(v['block'], v['snr'], v['arm']):v for v in rows}
    expected = {(b,s,a) for b in range(32) for s in (7,8) for a in ('ORIGINAL','TAIL','RIDGE_T')}
    if set(ix) != expected or len(rows) != len(ix):
        raise ValueError('duplicate or incomplete exposed endpoint matrix')
    out = {'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
           'scope':'post-hoc descriptions, no independent confirmation or causal claim'}
    for s in (7,8):
        out[str(s)] = section = {}
        for a in ('ORIGINAL','TAIL','RIDGE_T'):
            values = [ix[b,s,a] for b in range(32)]
            count = sum(v['clipped']['wrong_sign_bits'] for v in values)
            section[a] = dict(failed_blocks=[v['block'] for v in values if v['scores']['FER']],
                mean_H_NMSE=statistics.mean(v['scores']['H_NMSE'] for v in values),
                mean_clipped_NLL=statistics.mean(v['clipped']['bit_NLL'] for v in values),
                mean_raw_NLL=statistics.mean(v['raw']['bit_NLL'] for v in values),
                wrong_sign_bits=count,
                mean_wrong_abs_llr_weighted=(sum((v['clipped']['mean_wrong_abs_llr'] or 0)*v['clipped']['wrong_sign_bits']
                    for v in values)/count if count else None))
        for a in ('ORIGINAL','RIDGE_T'):
            section['TAIL_vs_'+a] = dict(
                rescued=[b for b in range(32) if ix[b,s,a]['scores']['FER'] and not ix[b,s,'TAIL']['scores']['FER']],
                new_failures=[b for b in range(32) if not ix[b,s,a]['scores']['FER'] and ix[b,s,'TAIL']['scores']['FER']],
                NLL_improved=sum(ix[b,s,'TAIL']['clipped']['bit_NLL'] < ix[b,s,a]['clipped']['bit_NLL'] for b in range(32)))
    out['block14_7'] = {a:dict(scores=ix[14,7,a]['scores'],
        clipped={k:v for k,v in ix[14,7,a]['clipped'].items() if k!='wrong_positions'})
        for a in ('ORIGINAL','TAIL','RIDGE_T')}
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    with args.output.open('x') as f:
        json.dump(summarize(args.root), f, indent=2, allow_nan=False)
        f.write('\n')
