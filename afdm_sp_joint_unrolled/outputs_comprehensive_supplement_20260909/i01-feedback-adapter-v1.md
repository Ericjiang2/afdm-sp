# I-01 legal feedback adapter integration

BaselineReceiver.run now explicitly forwards an optional CodeFeedback through ObservedReceiver.run to the existing outer receiver. The boundary accepts only the exact legal controller class bound to the same LDPC code object; arbitrary keyword or truth-bearing interfaces are not added. Returned consumer records are copied. None retains the original output field set; disabled feedback adds only an empty feedback record list. The final terminal BP and LDPC remain in the complete receiver path.

18 tests pass, including three new real N32 adapter tests for None/disabled numerical equality (1e-12 tolerance), legal/zero/sham actual CE and detector consumption, final decoded shapes/graph trace, audit schema, record-copy isolation and input rejection. Tiny test assembly bypasses the production N1024 constructor only; it runs actual adapter, CE, BP and LDPC algorithms. This is not production N1024 validation or any FER/cost claim.

No source snapshot used by current remote pilot runs was modified. Six-arm oracle handling, schedule/cost allocation, full N1024 engineering validation and the 192-block study remain open in CSV I-01.
