"""Descriptive tables from saved scalar/vector traces; no receiver execution."""
import csv,json,statistics
from pathlib import Path
R=Path(__file__).resolve().parent
rows=list(csv.DictReader((R/'extracted/audit_iteration_metrics.csv').open()))
def select(snr,arm,phase):
    return [r for r in rows if int(r['snr_centi_db'])==snr and r['arm']==arm and
            ((int(r['iteration'])==0) if phase=='initial' else
             (1<=int(r['iteration'])<=4) if phase=='early' else int(r['iteration'])>=5)]
def med(s,k):return statistics.median(float(r[k]) for r in s)
out=[]
for snr in (600,650,700):
 for arm in ('TF_J20_R2','TF_POINT20_R2'):
  for phase in ('initial','early','late'):
   s=select(snr,arm,phase)
   z={'snr_db':snr/100,'arm':arm,'phase':phase,'iteration_rows':len(s),'audit_frames':1,'coded_rounds':2}
   for k in ('vq','pre_vh','post_vh','pre_vx','xpower','channelpower','correction','actual_reaction_ratio','user_literal_reaction_ratio','gain_movement_ratio','n_post_vh','correction_over_p_over_n','reaction_over_p_over_n','gain_movement_over_p_over_n'):
    vals=[float(r[k]) for r in s]
    for tag,v in [('median',statistics.median(vals)),('min',min(vals)),('max',max(vals))]:z[k+'_'+tag]=v
   out.append(z)
with (R/'phase_summary.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
s='''| Scope | Value |
|---|---|
| Source | Frozen direction validation, receiver2d130b4d; N=1024,P=8,P/N=0.0078125 |
| Full vector diagnostics | Existing frame0 at6/6.5/7dB; TF/POINT;2 rounds×20 iterations=240 rows |
| Paired scalar diagnostics | Existing first8 per SNR;2 arms×2 rounds×20=1920 rows |
| New Monte Carlo / receiver calls | 0 / 0 |
| Time convention | CSV iterations0–19 per round; figures1–40 concatenate two rounds. Pre-update variance/state quantities; current vq; post-update gain movement. |
| Aggregation | Medians below pool the2 coded rounds for one audit frame per SNR. Descriptive iteration summaries, not independent-sample statistics. |
| Phases | Initial: inner t=0 in each round; early:t=1–4; late:t=5–19. Late is a descriptive window, not a claim of convergence. |
| Scalar convention | Original scalar CSV gain_variance/data_variance are post-update; they are not mislabeled as pre-update. |

| SNR dB | Method | Late N vh_post | Late output correction % | Late actual reaction % | Early gain movement % | Late gain movement % |
|---:|---|---:|---:|---:|---:|---:|
'''
for snr in (600,650,700):
 for arm in ('TF_J20_R2','TF_POINT20_R2'):
  l=select(snr,arm,'late');e=select(snr,arm,'early')
  s+=f"| {snr/100:g} | {'TF' if arm=='TF_J20_R2' else 'POINT'} | {med(l,'n_post_vh'):.4f} | {100*med(l,'correction'):.3f} | {100*med(l,'actual_reaction_ratio'):.3f} | {100*med(e,'gain_movement_ratio'):.3f} | {100*med(l,'gain_movement_ratio'):.3f} |\n"
s+='\n| SNR dB | TF initial vh_pre | Initial output correction % | Initial reaction % | Late correction / (P/N) | Late reaction / (P/N) |\n|---:|---:|---:|---:|---:|---:|\n'
for snr in (600,650,700):
 i=select(snr,'TF_J20_R2','initial');l=select(snr,'TF_J20_R2','late')
 s+=f"| {snr/100:g} | {med(i,'pre_vh'):.3f} | {100*med(i,'correction'):.2f} | {100*med(i,'actual_reaction_ratio'):.2f} | {med(l,'correction_over_p_over_n'):.3f} | {med(l,'reaction_over_p_over_n'):.3f} |\n"
s+='''
| Scaling / mechanism question | Saved-state finding | Limit |
|---|---|---|
| vh=O(1/N) | Post-transient posterior N vh medians0.567–0.710; exact relation N vh=1/(sv xb_power+P/N) agrees to8.88e−16. Consistent with1/N posterior scaling if sv and xb_power remain order-one. | FixedN=1024 only; no empirical asymptotic order or exponent estimate. |
| Variance effects O(P/N) | Late relative output correction≈1.18–1.20%, reaction≈0.76–0.82%; coefficients after division byP/N are≈1.51–1.54 and≈0.97–1.06. Consistent at the observed operating point. | Initialization violates a uniform small-effect interpretation: vh_pre=1/P and relative effects are order-one. Earlier iterations also have larger coefficients. |
| Gain-mean updates remain first-order | Early movement is6.07–16.41% for TF and4.16–4.55% for POINT, despite POINT propagating vh=0. Thus mean adaptation remains substantial without gain-variance propagation. | Net movement decays to0.58–0.83% for TF and0.23–0.42% for POINT in the late window. First-order large-N scaling cannot be identified from oneN; it does not mean movement dominates variance terms at every iteration. |
| Full propagation versus POINT | POINT retains joint gain-mean adaptation and gain pseudo-variance/shrinkage, but propagated vh and both explicit gain-variance diagnostics are exactly0. Full propagation has a large startup perturbation followed by small corrections. | TF here propagates a scalar gain variance; it is not a full gain covariance matrix or a new full-Gamma experiment. |
| Consistency checks | Saved trace vq,sv,channel norm,post-vx/post-vh,bar/vp match reconstruction exactly; posterior scaling identity residual≤8.88e−16. | Algebraic replay consistency is not independent evidence of asymptotic scaling or unchanged statistical performance. |
'''
(R/'TABLES.md').write_text(s)
