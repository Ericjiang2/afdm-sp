1. **The rank claim holds for the complete co-delay kernel. A fixed path support can require fewer summaries.** Use Proposition 1’s indices \(t\) for time and \(n\) for symbol. Fix a complete unitary synthesis \(W\), a common integer delay \(\ell\), and \(S_W=(|W_{tn}|^2)_{tn}\). For every \(v\in\mathbb R_+^N\), require recovery of the co-delay entry at every Doppler difference \(\delta\) from \(Av\) alone, where \(A\) is a fixed real matrix. The minimum number of rows of \(A\) is \(\operatorname{rank}_{\mathbb R}S_W\).

   **Proof.** The integer delay permutes the time-energy vector to \(p=P_\ell S_Wv\). The co-delay entry is \(\sum_t p_t e^{2\pi\mathrm i\delta t/N}\), so coordinates of \(S_Wv\) in a basis of its image suffice. Conversely, the entries at \(\delta=0,\ldots,N-1\) recover \(p\) by Fourier inversion. For any \(h\in\ker A\), write \(h=h^+-h^-\). The nonnegative vectors \(h^+,h^-\) have identical summaries, hence identical \(p\), so \(S_Wh=0\). Thus \(\ker A\subseteq\ker S_W\), proving minimality even for nonlinear reconstruction.

   **Waveforms.** AFDM and ordinary OFDM both have \(S_W=\mathbf1\mathbf1^\top/N\), of rank \(1\). For the paper’s rectangular-pulse OTFS with \(N=m_0k_0\), columns in row \(q\) share the profile \(k_0^{-1}\mathbf1_{\{t\equiv q\bmod m_0\}}\). The \(m_0\) profiles have disjoint nonempty supports, so their rank is exactly \(m_0\), attained by the row variance totals. Unspread single carrier, defined here by \(W=I_N\), has rank \(N\). On a **singleton** path support its block is just \([\,\sum_n v_n\,]\), so one summary suffices even when \(N>1\).

2. **This generalizes the existing common-integer-delay remark.** Since \(S_W\) is doubly stochastic, rank one forces \(S_W=\mathbf1\mathbf1^\top/N\), recovering the time-flatness criterion. Unequal-delay AFDM entries can depend on \(\widehat v[d]\) even at fixed total variance, so the same count does not cover the whole \(\Gamma_{\rm F}\). At a specified common fractional delay \(\tau\), the proof gives the rank of the **delayed** energy matrix \((|(\mathsf S_\tau W)_{tn}|^2)_{tn}\).

3. **Use a remark.** The following can follow the existing modulation-independence remark.

   ```latex
   \begin{afdmremark}[Linear summaries for co-delay reconstruction]
   Let $W$ be a complete unitary synthesis matrix and $S_W=(|W_{tn}|^2)_{tn}$.
   At a common integer delay $\ell$, the minimum number of real linear
   summaries of $v$ from which all co-delay entries can be recovered,
   for every $v\ge0$ and every Doppler difference, is $\operatorname{rank}S_W$.
   Indeed, the entries are Fourier samples of the cyclic shift of $S_Wv$,
   and the $N$ integer-frequency samples recover this vector.
   Coordinates in a basis of $\operatorname{im}S_W$ therefore suffice.
   For any sufficient summary $Av$ and $h\in\ker A$, the positive and
   negative parts of $h$ have identical summaries, so $S_Wh=0$.
   \end{afdmremark}
   ```

4. **Include it as a short algebraic consequence.** Its contribution is the necessity of the OTFS row totals up to a change of linear coordinates. That statement needs no OTFS simulation and makes no prediction about OTFS receiver performance. Avoid calling it a decoder-interface lower bound. For this paper’s QPSK data, a receiver that already has the soft means obtains every variance from \(v_n=E_s-|\mu_n|^2\), with zero additional variance values transmitted.