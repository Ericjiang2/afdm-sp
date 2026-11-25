# Degree-2 forest screen

Use the saved C1 L28 transfer curves at 6.5 and 8 dB. Reuse the original
Gaussian-approximation decoder and its 10 outer rounds, up to 50 BP updates,
and convergence threshold of 0.9999 check information. Compare the regular
ensemble, the original matching ensemble, and the constrained finite profiles.
The primary question is whether a feasible profile opens at the measured
6.5 dB point and how many rounds it takes. Also report the modeled startup
threshold under the same schedule. Linearly interpolate the two curves in
SNR and flag every threshold below 6.5 dB as extrapolated.

Screen the original family of variable degrees {2, 3, D} for D in
{6, 8, 12, 20, 30}. Use integer node counts for length 2048, 1024 checks,
N2 <= 1023 and at least one odd-degree variable so full row rank is possible.
The two adjacent check degrees use the exact integer split that balances
the edge count. Search a 16-node grid, include its feasible boundaries,
then search unit steps within 16 nodes of the best coarse profiles for
each D. Rank by the modeled 10-round SNR threshold within [5.0, 8.0] dB,
then by rounds to open and final check information at the measured 6.5 dB
point. Report the searched family and resolution with the result.

If a profile beats the regular startup threshold, attempt one concrete
matrix. Lay down degree-2 edges as a forest of paths on the check vertices.
Fill residual check capacities with the degree-3 and higher columns by
bipartite Havel–Hakimi with seeded ties. Verify exact degrees, forest
acyclicity, GF(2) rank, encoder parity, and the weight-1 through weight-4
spectrum. A candidate with a clean degree-2 subgraph can still have
low-weight words involving other variable degrees. Record these checks
and perform zero end-to-end receiver calls.
