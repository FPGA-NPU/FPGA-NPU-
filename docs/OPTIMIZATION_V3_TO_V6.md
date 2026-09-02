# npu_leenet11 model suitability and v3/v6 Golden bit-exact review

Date: 2026-08-31

## Conclusion

the validated LeeNet11 INT16 model handoff is a valid
reference for the canonical v3/v6 NPU Golden bit-exact gate. Both boards runs
passed every layer and the final 527 logits with zero mismatches.

This conclusion applies to deterministic hardware equivalence for the supplied
INT16 model and canonical 10-second input. It does not by itself measure the
model's dataset-wide AudioSet mAP or real-world classification accuracy.

## Model identity and structure

- model: PANNs LeeNet11
- checkpoint: `LeeNet11_mAP=0.266.pth`
- official checkpoint MD5: `61ba7a7a85542fe4e97240db974eb158`
- checkpoint iteration: 540000
- trainable parameters: 748,367
- input: 320,000 mono PCM16/Q15 samples at 32 kHz
- body: nine Conv1D blocks, K=3
- Conv1: 1 -> 64, stride 3, no max pool
- Conv2–Conv9: Conv/BN/ReLU followed by K=3, stride-3 max pool
- channel progression: 64, 64, 64, 128, 128, 128, 128, 128, 256
- global operation: temporal max plus temporal rounded mean
- FC1: 256 -> 512, ReLU
- FC2: 512 -> 527 AudioSet logits

The supplied FP32 structure audit passed strict checkpoint loading, all layer
dimensions, all temporal output shapes, Global Max+Mean, deterministic eval
mode, and a manual-forward comparison with maximum error 0.

## Fixed-point contract

- activation and weight storage: signed INT16
- accumulator and valid bias width: signed 48-bit
- bias container: signed little-endian INT64
- activation layout: channel-major, time index fastest
- per-output-channel requantization
- signed rounding: nearest, ties away from zero
- output saturation: signed INT16
- final PL result: 527 signed INT16 Q10 logits

The model asset audit passed all 20 checks, including parameter/blob slice
identity, 64-byte alignment, no overlapping regions, bias width, rshift
formula, layer CSV/manifest consistency, input WAV/PCM identity, every Golden
shape/Q-format/byte size, sigmoid reproduction, and 527 class labels.

The Golden manifest reports no saturation. Against FP32 for the canonical
sample, INT16 probability RMSE is `4.1141890553261226e-05`, maximum probability
error is `0.000847134943333494`, and the FP32/INT16 Top-10 class indices are
identical. This supports the quantized reference fidelity for this sample.

## Original-to-validation asset identity

The original handoff was compared recursively against
`Docs/LeeNet11-NPU-INT16-v1_B_Golden_BitExact_Handoff/hw_handoff_v1`.

| Check | Result |
|---|---:|
| Original files | 135 |
| Matching validation files | 135 |
| Model/Golden mismatches | 0 |
| Docs-only files | 1 reconstructed WAV for listening |

Key identities:

| Artifact | Size | SHA-256 |
|---|---:|---|
| `model_params.bin` | 1,509,455 B | `14139436A146E3C82B7EB4134856F38181C912A6031908E53B522AFD52F3DEC3` |
| `00_input_int16_q15.bin` | 640,000 B | `78BE03769667AF131D8AC2D17154B28723157E51F1C7AEA1F530EA575E03F682` |
| `01_conv1_out_int16.bin` | 13,653,376 B | `EFC9902AECEFF751A3D93161FE94DF34BDF600EB315AC78C2B1A61F0EBD3F6B3` |
| `12_fc2_out_int16.bin` | 1,054 B | `F0899AE3F9B8765BD5811B4BABA388D5FB631EFC077EDC7F0A273DF4207B7376` |

Therefore the existing hardware harness loads the same model, input, and
Golden tensors as the model directory named in this review; it is not using a
different exported revision.

## Fresh Zybo v3/v6 Golden run

Common conditions:

- board: Zybo Z7-20
- UART: COM4, 115200 baud
- input/model/Golden: the identical original handoff described above
- comparison: every stored INT16 element after each layer
- chain: Conv1–Conv9 -> GLOBAL -> FC1 -> FC2, no reset between layers

| Revision | Passed layers | Failed layer | Final values | Mismatches | Golden gate | Operation sum |
|---|---:|---|---:|---:|---|---:|
| v3 | 12/12 | none | 527 | 0 | PASS | 1,013.875 ms |
| v6 | 12/12 | none | 527 | 0 | PASS | 259.324 ms |

Layer element counts that passed in both revisions:

| Layer | Compared INT16 values |
|---|---:|
| Conv1 | 6,826,688 |
| Conv2 | 2,275,584 |
| Conv3 | 758,528 |
| Conv4 | 505,728 |
| Conv5 | 168,576 |
| Conv6 | 56,192 |
| Conv7 | 18,816 |
| Conv8 | 6,272 |
| Conv9 | 4,352 |
| GLOBAL | 256 |
| FC1 | 512 |
| FC2 | 527 |

Because v3 and v6 independently match the same Golden tensor at every layer,
their layer outputs and final logits are also mutually bit-exact.

The reported Golden-chain wall time includes software comparison of millions
of DDR values and must not be used as the normal inference latency. The
operation sum is shown only as supporting performance context; the acceptance
criterion in this review is zero numeric mismatch.

## Evidence

- original model manifest:
  `model/model_manifest.json`
- original Golden manifest:
  `validation/manifests/golden_manifest.json`
- v3 UART log:
  `validation/evidence/20260831_104648_v3_golden_uart.log`
- v6 UART log:
  `validation/evidence/20260831_104748_v6_golden_uart.log`
- parsed comparison:
  `validation/evidence/20260831_104748_golden_summary.json`

## Acceptance decision

Accepted for:

- RTL/SoC regression between v3 and v6;
- per-layer arithmetic, layout, pooling, requantization, and FC checking;
- detecting any single-bit functional deviation for the canonical payload.

Not sufficient alone for:

- AudioSet dataset-wide mAP comparison;
- microphone-domain robustness or environmental accuracy;
- quantization accuracy over many audio samples;
- statistical equivalence across a validation corpus.

Those accuracy claims require a labeled multi-sample dataset evaluation in
addition to this bit-exact hardware gate.
