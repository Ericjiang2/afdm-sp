"""Render saved-state diagnostics only; never imports a receiver."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
COLORS={'TF_J20_R2':'#0072B2','TF_POINT20_R2':'#D55E00'}
LABELS={'TF_J20_R2':'TF joint','TF_POINT20_R2':'POINT gain-mean control'}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'pdf.fonttype':42,'savefig.bbox':'tight'})

def load():
    with (ROOT/'extracted'/'audit_iteration_metrics.csv').open() as f: raw=list(csv.DictReader(f))
    rows=[]
    for r in raw:
        z={}
        for k,v in r.items():
            if k=='arm':z[k]=v;continue
            try:z[k]=float(v)
            except (ValueError,TypeError):z[k]=v
        aliases={'vh_pre':'pre_vh','vh_post':'post_vh','vx_pre':'pre_vx',
                 'xpower_pre':'xpower','hRh_pre':'channelpower',
                 'output_variance_correction':'correction','reaction_ratio':'actual_reaction_ratio',
                 'gain_mean_relative_movement':'gain_movement_ratio','P':'p_count'}
        for dst,src in aliases.items():z[dst]=z[src]
        z['N']=1024  # Frozen campaign dimension, not a swept parameter.
        rows.append(z)
    return rows

def series(rows,snr,arm):
    return sorted([r for r in rows if r['snr_centi_db']==snr and r['arm']==arm],
                  key=lambda r:(r['round'],r['iteration']))

def draw():
    rows=load();files=[]
    panels=[('vq',r'$v_q$ (current pseudo-variance)','log'),
            ('vh_pre',r'$v_h$ entering iteration','symlog'),
            ('vx_pre',r'$v_x$ entering iteration','log'),
            ('xpower_pre',r'$\|x\|^2/N$ entering iteration','linear'),
            ('hRh_pre',r'$h^H R h$ entering iteration','linear'),
            ('output_variance_correction','Relative output-variance correction','symlog'),
            ('reaction_ratio','Actual reaction / data backprojection','symlog'),
            ('gain_mean_relative_movement',r'$\|h_{t+1}-h_t\|/\|h_t\|$','log')]
    snrs=sorted({r['snr_centi_db'] for r in rows})
    for snr in snrs:
        fig,axes=plt.subplots(2,4,figsize=(16,7.4),layout='constrained')
        for ax,(field,title,scale) in zip(axes.flat,panels):
            for arm,color in COLORS.items():
                s=series(rows,snr,arm);x=[r['round']*20+r['iteration']+1 for r in s]
                y=[r[field] for r in s]
                ax.plot(x,y,color=color,lw=1.8,ls='-' if arm=='TF_J20_R2' else '--',label=LABELS[arm])
                if field=='vh_pre' and arm=='TF_J20_R2':
                    ax.plot(x,[r['vh_post'] for r in s],color=color,lw=1,ls=':',label='TF posterior $v_h$')
            if scale=='symlog':ax.set_yscale('symlog',linthresh=1e-6)
            else:ax.set_yscale(scale)
            ax.axvline(20.5,color='0.55',lw=.8,ls=':')
            ax.set(title=title,xlabel='Saved inner iteration: round 1 | round 2')
            ax.set_xticks([1,10,20,30,40]);ax.grid(alpha=.18)
        axes[0,0].legend(fontsize=9);axes[0,1].legend(fontsize=8)
        fig.suptitle(f'{snr/100:g} dB — existing audit frame 0; N=1024; no receiver rerun\n'
                     'Variance/state quantities use pre-update values; vq and movement refer to current update',fontsize=13)
        for ext in ['png','pdf']:
            p=ROOT/f'mechanism_{int(snr)}.{ext}';fig.savefig(p,dpi=170);files.append(p.name)
        plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,7.5),layout='constrained')
    fields=[('vh_post',r'$N v_h$ (posterior)','N'),
            ('output_variance_correction',r'Output correction divided by $P/N$','PN'),
            ('reaction_ratio',r'Actual reaction ratio divided by $P/N$','PN'),
            ('gain_mean_relative_movement',r'Gain-mean movement divided by $P/N$','PN')]
    for ax,(field,title,kind) in zip(axes.flat,fields):
        for arm,color in COLORS.items():
            arrays=[]
            for snr in snrs:
                s=series(rows,snr,arm)
                arrays.append([r[field]*r['N'] if kind=='N' else r[field]/(r['P']/r['N']) for r in s])
            a=np.array(arrays);x=np.arange(1,a.shape[1]+1)
            ax.plot(x,np.median(a,axis=0),color=color,lw=1.7,ls='-' if arm=='TF_J20_R2' else '--',label=LABELS[arm])
            ax.fill_between(x,np.min(a,axis=0),np.max(a,axis=0),color=color,alpha=.12)
        ax.set_yscale('symlog',linthresh=1e-4);ax.axhline(1,color='0.4',ls=':',lw=.9)
        ax.axvline(20.5,color='0.5',ls=':',lw=.8);ax.set(title=title,xlabel='Saved inner iteration: round 1 | round 2')
        ax.grid(alpha=.18)
    axes[0,0].legend()
    fig.suptitle('Fixed-N consistency diagnostics — not an N-scaling experiment\n'
                 'Lines: median of 3 existing audit frames (one per SNR); shading: range, not confidence interval',fontsize=12)
    for ext in ['png','pdf']:
        p=ROOT/f'scaling_consistency.{ext}';fig.savefig(p,dpi=170);files.append(p.name)
    plt.close(fig)
    (ROOT/'plot_files.json').write_text(json.dumps(files,indent=2)+'\n')

if __name__=='__main__':draw()
