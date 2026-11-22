import sys, numpy as np
import c_l2_c08_iface as m
C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; nat = ctx.native; od = nat.decoder_messages
code = ctx.code; print('code keys', [k for k in code][:20]); H = code['H']; print('H', H.shape)
out = []
for fr in range(41000, 41012):
    for s in ('U', 'G'):
        b = st.inputs(ctx, fr, s, 100); raw, obs, truth = st.observed(ctx, b, 100, 550)
        if fr == 41000 and s == 'U': print('truth keys', list(truth)[:30], 'raw keys', list(raw)[:30] if isinstance(raw, dict) else type(raw))
        L = []
        def dec(code_, llr, maxiter=50):
            L.append(np.asarray(llr, float).copy()); return od(code_, llr, maxiter=maxiter)
        nat.decoder_messages = dec
        try: d, arr, syn, _ = st.e1.f0_state(ctx, obs)
        finally: nat.decoder_messages = od
        out.append((L, d, syn, truth))
import pickle; pickle.dump([(L, syn, {k: np.asarray(v) for k, v in t.items() if hasattr(v, '__len__')}) for L, d, syn, t in out], open('/tmp/c22.pkl', 'wb'))
