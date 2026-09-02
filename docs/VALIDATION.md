# v6 Validation Summary

The checked-in v6 evidence is a board-validated signoff set for Zybo Z7-20 / XC7Z020 using Vivado/Vitis 2024.2.

## Timing and resources

| Metric | v6 |
|---|---:|
| LUT | 43,157 |
| FF | 58,781 |
| RAMB36 | 88 |
| RAMB18 | 59 |
| DSP | 192 |
| Setup WNS | +0.497 ns |
| Hold WHS | +0.008 ns |

## Golden bit-exact gate

The canonical fixed-point handoff was checked at Conv1 through Conv9, Global, FC1, and FC2. All 12 layer checkpoints reported zero mismatch, and the final FC2 output reported 527/527 logits matching.

This is an implementation-equivalence check for a fixed canonical input; it is not a dataset-wide accuracy measurement.

## v3 -> v6 throughput comparison

For the same knock demo payload:

| Metric | v3 | v6 | Improvement |
|---|---:|---:|---:|
| Conv2 active cycles | 54,613,797 | 8,960,303 | 6.095x fewer |
| Conv2 time | 546.209 ms | 116.577 ms | 4.685x faster |
| 12-layer operation sum | 1,013.876 ms | 259.431 ms | 3.908x faster |

The v6 `cycles/step` denominator is a four-input-channel Pin4 step, whereas the older scalar path used one input channel per step. Use active cycles and elapsed time for revision-to-revision comparisons.

## Evidence locations

- `hardware/reports/`: synthesis and post-route reports
- `validation/evidence/`: UART/XSCT logs and summary JSON/CSV
- `docs/HARDWARE_VALIDATION_20260831.md`: board validation details
- `docs/NPU_LeeNet11_v3_v6_Golden_BitExact_Review_20260831.md`: fixed-point and revision review
