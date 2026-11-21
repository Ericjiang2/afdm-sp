MIXED8 Phase 1 committed as `d1a2ce0b`. Local and deinlab audits cleared **2200–2799** after confirming that 1600–2199 was already used. The fresh block remains blind.

| Gate | Result |
|---|---|
| G1 | PASS. CD and S matched all saved non-timing fields bit for bit across 600 archived frames. |
| G2 | PASS. Zero covariance and direct scores agreed on 10 synthetic cases, including 10 row refreshes. CD/Z detector inputs matched apart from paths and gains on all three smoke frames. |
| G3 | PASS. Fresh frames 2200–2799 and smoke frames 208–210 are disjoint from recorded allocations. |
| G4 | PASS. H matched the frozen slicer with the pilot restored. |
| G5 | PASS. Projected **0.250 core-hours** for 600 frames with 1.3× margin. Phase 1 used **0.180 core-hours**. |

F0, CD and TRUE_GEOMETRY reuse the frozen receiver. Z, H and Z-sel reuse the P1 wrappers. S and A2g use the frozen E-2 selector, with the all-delay guard enabled for A2g.  
The draft records 6 dB smoke timing to exercise the exchange branch. All 32 synthetic verdict tests passed, including [Newcombe Method 10](https://www.site.uottawa.ca/~nat/Courses/csi5388/Newcombe.1998.pdf). The slow scan and checksum typo were corrected before receiver execution. Confirmed `model: gpt-6.2-sol`.