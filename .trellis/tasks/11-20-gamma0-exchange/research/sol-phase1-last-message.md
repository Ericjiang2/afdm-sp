Phase 1 committed as `31758eae`. Local and deinlab audits cleared frames **9400–9799**. The block remains blind and the protocol is still a draft.

| Gate | Result |
|---|---|
| G1 | PASS. CD matched the archived fields bit for bit on all 110 triggered Stage 3 keys. |
| G2 | PASS. Zero covariance and direct-solve scores matched on 10 synthetic keys, including 10 row refreshes. Detector inputs matched on three smoke keys apart from paths and gains. |
| G3 | PASS. All 400 fresh frames had eight distinct true delays in each of the four cells. |
| G4 | PASS. H matched the frozen slicer with the pilot restored. |
| G5 | PASS. Three timed smoke keys project **2.045 core-hours** for 13,600 keys, including Z-sel and the 1.3× margin. |

E-1 first-edit phantom rates were **A2 93.59%** and **A1 1.61%**. The anchors remain **S lower bound ≥80%** and **CD upper bound ≤5%**.  
Z and H wrap the frozen geometry call to change only its inputs. S uses E-1’s diagonal selector. Z-sel refits CD gains on Z’s exact support. No frozen code was copied.  
§7 endpoints and thresholds were retained. The remote audit recovered from timeouts using the verified inventory, a newer-file scan, and a manifest-schema scan. The stale Git lock was preserved after ten retries.  
All 24 synthetic verdict tests passed. Confirmed `model: gpt-6.2-sol`.