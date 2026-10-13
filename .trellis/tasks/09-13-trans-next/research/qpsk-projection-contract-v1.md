# Exact circular QPSK edge projection qualification

For `x=a(s_I+i s_Q)`, independent bit priors and a circular Gaussian likelihood,
`log p(x) = 2 Re(t* x)/T + L_I s_I/2 + L_Q s_Q/2 + constant` because
`|x|²=2a²`. With a=.5, the mean is
`.5[tanh(Re(t)/T+L_I/2)+i tanh(Im(t)/T+L_Q/2)]` and the variance is
`.5-|mean|²`. Here `t=mean_ext=mu_ext/var_ext` in the existing BP kernel.
This is a standard factorization of an existing update, not a novel detector.

The explicit `bp_edge_projection='qpsk_tanh'` control passes through the common
receiver to every outer and terminal BP invocation. Default None preserves
enumerated arithmetic. Reject a different amplitude/order, noncircular
projection, probability-level cavity observers and an SISO/PIC combination.
Retain the existing prior initialization, variance floor, mean-only damping,
final node projection, LLR convention, CE and decoder. No truth input or
runtime fallback is introduced. The float64 Torch helper stays on its device;
existing NumPy feedback helpers cannot replace it without transfers.

Unit v2:17 tests PASS, enumerated four-symbol sums, sparse/diagonal/no-edge BP,
zero/nonzero/no prior, temperatures and unchanged default. v1 had a real-H test
fixture incompatible with existing complex BP; preserve the failure. Unit v3:
11 tests PASS including real tiny CE/BP/LDPC delivery and SISO/default regression.
These are not N1024 qualification.

Engineering contract: reuse two prior engineering blocks, 7/8dB, five arms
MEAN/REFRESH47/QPSK_MEAN/QPSK_REF47/QPSK_REF47_REPEAT=20F. 1800 seconds,
4GiB output, one CPU thread. Old BP fields exactly replay against saved refs;
analytic path hard symbols/support/decoded/info bits exact, continuous fields
allclose rtol1e-5/atol1e-6 (chain contains complex64 CE casts). Optimized repeat
must be exact on all numeric fields. Save original inputs, all normal raw
receiver states and profile calls; raw-readback scores must match. Record
operator times as inclusive instrumented diagnosis, not deployment COST.

A failed comparison remains failed. Do not relax tolerances using results.
Successful engineering is followed by raw CE/decoder replay and a bounded
development comparison before shared use. No CONF or scientific FER claim is
admitted by this contract; formal timing must remove diagnostic overhead by
actually measuring the production path with the same controls.

Engineering completed:20F,66.64s external; eight old BP exact replays, four
optimized exact repeat pairs and all hard outputs passed. Maximum continuous
relative error was7.12e-10. Instrumented mean times were1.622/1.661s for old
MEAN/REFRESH47,1.361/1.385s for analytic arms (repeat1.347s). Raw auditor v2
passed2716 arrays,180CE,20 terminal and28 retained nested LDPC replays in16.51s
external. First auditor failed on a missing helper module before raw reads;
its source/exit/log remain intact. Detailed bindings: [results](qpsk-engineering-results-v1.json).

Development admission now freezes128F on the previous32 development blocks,
7/8dB, QPSK_MEAN/QPSK_REF47 only,1800s/4GiB/one thread. Each pair compares
against its original audited BP state under the same hard/soft criteria.
Receiver algorithm files must match the qualified engineering manifest; only
the profile runner may change for stage routing. Admission tests reject
changed raw qualification or changed algorithm; audit-module import is checked
before launch. This stage does not generate new confirmation inputs or admit
claims of population noninferiority.
