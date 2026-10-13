"""Strict paired analysis for the fixed 48-frame initial-OMP exploration."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


COMPARISONS = [('A','B'),('A','C'),('C','D'),('D','E'),('B','F'),
               ('A','F'),('A','D'),('E','E_thermal')]


def load_records(root):
    rows=[]
    source=None
    expected={(r,i,s) for r in (90700,90701,90702) for i in range(16) for s in (8,12,16)}
    identities=set()
    sources={}
    for rep in (90700,90701,90702):
        directory=root/f'rep{rep}'
        status=json.loads((directory/'status.json').read_text())
        if not status['complete'] or status['completed']!=48:
            raise ValueError('incomplete experimental stream')
        if source is not None and status['source_hashes']!=source:
            raise ValueError('source changed across streams')
        source=status['source_hashes']
        path=directory/'frames.jsonl'
        sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        for line in path.read_text().splitlines():
            row=json.loads(line)
            identity=(row['replicate'],row['frame_index'],row['snr'])
            if identity in identities or identity[0]!=rep or not row['uncoded']:
                raise ValueError('duplicate identity, wrong stream or coding')
            identities.add(identity)
            for arms in row['stages'].values():
                for result in arms.values():
                    mask=np.unpackbits(np.frombuffer(bytes.fromhex(result['error_mask_hex']),dtype=np.uint8))
                    if result['bits']!=2048 or len(mask)!=2048 or mask.sum()!=result['errors']:
                        raise ValueError('invalid bit/error denominator or mask')
            rows.append(row)
    if identities!=expected:
        raise ValueError('predeclared frame matrix incomplete or changed')
    for rep in (90700,90701,90702):
        for i in range(16):
            block=[r for r in rows if r['replicate']==rep and r['frame_index']==i]
            for key in ('H','noise','info','coded','pilot'):
                if len({r['input_hashes'][key] for r in block})!=1:
                    raise ValueError('cross-SNR exogenous pairing failed')
    return sorted(rows,key=lambda r:(r['snr'],r['replicate'],r['frame_index'])),sources


def paired_statistics(rows,stage,left,right,indices):
    a=np.array([r['stages'][stage][left]['errors'] for r in rows])
    b=np.array([r['stages'][stage][right]['errors'] for r in rows])
    delta=(b-a)/2048
    sampled=np.concatenate([delta[lo+index] for lo,index in indices],axis=1).mean(axis=1)
    repaired=introduced=0
    for row in rows:
        arms=row['stages'][stage]
        masks=[np.unpackbits(np.frombuffer(bytes.fromhex(arms[k]['error_mask_hex']),dtype=np.uint8)).astype(bool) for k in (left,right)]
        repaired+=int((masks[0]&~masks[1]).sum())
        introduced+=int((~masks[0]&masks[1]).sum())
    return dict(left=left,right=right,left_errors=int(a.sum()),right_errors=int(b.sum()),
        delta_BER=float(delta.mean()),CI95_delta_BER=np.quantile(sampled,[.025,.975]).tolist(),
        relative_reduction=float(1-b.sum()/a.sum()) if a.sum() else None,
        frames_improved=int((b<a).sum()),frames_harmed=int((b>a).sum()),frames_tied=int((b==a).sum()),
        repaired_bits=repaired,introduced_bits=introduced,
        by_stream=[dict(replicate=rep,left_errors=int(a[j:j+16].sum()),right_errors=int(b[j:j+16].sum()))
                   for j,rep in zip((0,16,32),(90700,90701,90702))])


def summarize(rows):
    result={}
    for snr in (8,12,16):
        block=[r for r in rows if r['snr']==snr]
        rng=np.random.default_rng(202609070+snr)
        indices=[(j,rng.integers(0,16,size=(10000,16))) for j in (0,16,32)]
        quality=dict(frames=len(block),bits=len(block)*2048,
            frames_with_misses=sum(bool(r['quality']['missed_ids']) for r in block),
            mean_true_atoms=float(np.mean([r['quality']['true_atoms'] for r in block])),
            mean_missed_atoms=float(np.mean([len(r['quality']['missed_ids']) for r in block])),
            mean_false_atoms=float(np.mean([len(r['quality']['false_ids']) for r in block])),
            mean_recall=float(np.mean([r['quality']['recall'] for r in block])),
            mean_precision=float(np.mean([r['quality']['precision'] for r in block])),
            mean_lost_energy=float(np.mean([r['quality']['missed_coefficient_energy'] for r in block])),
            max_lost_energy=float(max(r['quality']['missed_coefficient_energy'] for r in block)),
            mean_oracle_repr=float(np.mean([r['projection']['A']['E_repr'] for r in block])),
            mean_final_nmse=float(np.mean([r['channel_errors']['A']['nmse'] for r in block])),
            mean_final_excess=float(np.mean([r['channel_errors']['A']['excess_within_support'] for r in block])))
        stages={}
        for stage in ('initial_ls','first_receiver','final_receiver'):
            arm_names=list(block[0]['stages'][stage])
            arms={}
            for arm in arm_names:
                values=[r['stages'][stage][arm] for r in block]
                errors=sum(v['errors'] for v in values)
                arms[arm]=dict(errors=errors,bits=quality['bits'],BER=errors/quality['bits'],
                    error_frames=sum(v['errors']>0 for v in values),
                    mean_nmse=float(np.mean([v['nmse'] for v in values])),
                    mean_sigma2=float(np.mean([v['sigma2'] for v in values])),
                    mean_graph_edges=float(np.mean([v['graph_edges'] for v in values])))
            comparisons=COMPARISONS+([('A','B_sigmaA'),('B','B_sigmaA'),('F','F_sigmaA')] if stage!='initial_ls' else [])
            stages[stage]=dict(arms=arms,comparisons={f'{a}_to_{b}':paired_statistics(block,stage,a,b,indices) for a,b in comparisons})
        result[str(snr)]=dict(quality=quality,stages=stages)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    args=p.parse_args()
    rows,hashes=load_records(args.root)
    summary=dict(scope='48 independent exogenous frames, 3 streams, 3 SNRs, uncoded development diagnostic',
        bootstrap='10000 paired resamples within each fixed 16-frame stream; pointwise 95% intervals',
        oracle_scope='terminal H substitution at common A sigma, not oracle closed-loop feedback or BER optimum',
        source_files=hashes,results=summarize(rows))
    with (args.root/'summary.json').open('x') as f:json.dump(summary,f,indent=2,allow_nan=False)
    lines=['# OMP initial-support probe: measured results','',summary['scope'],'',
        'A=OMP estimated; B=equal-cardinality truth-assisted estimated; C=OMP exact gains;',
        'D=reference exact gains; E=full true channel; F=compact truth-support estimated.','',
        'Oracle C/D/E use common A sigma. A/B/F retain their own normal feedback trajectory.',
        'No LDPC; no training; no formal claim. Zero observed errors is not zero population BER.','',
        '| SNR | Recall | Missed atoms | False atoms | Lost energy | Final A NMSE |',
        '|---|---|---|---|---|---|']
    for snr,r in summary['results'].items():
        q=r['quality'];lines.append(f"| {snr} | {q['mean_recall']:.4%} | {q['mean_missed_atoms']:.3f} | {q['mean_false_atoms']:.3f} | {q['mean_lost_energy']:.4%} | {q['mean_final_nmse']:.6g} |")
    for stage in ('initial_ls','first_receiver','final_receiver'):
        lines.extend(['',f'## {stage}','', '| SNR | A | B | C | D | E | F | Bits per arm |','|---|---|---|---|---|---|---|---|'])
        for snr,r in summary['results'].items():
            arms=r['stages'][stage]['arms'];cells=[f"{arms[a]['BER']:.6g} ({arms[a]['errors']})" for a in ('A','B','C','D','E','F')]
            lines.append('| '+snr+' | '+' | '.join(cells)+f" | {r['quality']['bits']} |")
        lines.extend(['','| SNR | Contrast | BER difference (right-left), 95% CI | Frame win/harm/tie | Repaired/new bits |','|---|---|---|---|---|'])
        for snr,r in summary['results'].items():
            for key,c in r['stages'][stage]['comparisons'].items():
                lo,hi=c['CI95_delta_BER']
                lines.append(f"| {snr} | {key} | {c['delta_BER']:.6g} [{lo:.6g}, {hi:.6g}] | {c['frames_improved']}/{c['frames_harmed']}/{c['frames_tied']} | {c['repaired_bits']}/{c['introduced_bits']} |")
    (args.root/'results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({s:dict(quality=r['quality'],final={a:v['BER'] for a,v in r['stages']['final_receiver']['arms'].items()}) for s,r in summary['results'].items()},indent=2))


if __name__=='__main__':main()
