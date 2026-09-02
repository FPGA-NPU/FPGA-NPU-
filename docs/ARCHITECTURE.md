# NPU v6 Architecture

## 1. Top-level

[`hardware/npu/rtl/top/neural_processing_unit_unified_6_0.v`](../hardware/npu/rtl/top/neural_processing_unit_unified_6_0.v)가 NPU 전체를 연결합니다.

```text
AXI-Lite CSR
    │
Layer Controller / Descriptor
    │
Frontend Selection
    ├─ Conv1
    ├─ Conv2~9 Pin4
    ├─ Global
    └─ FC
    │
Shared B-Core
    │
527 INT16 Q10 logits
```

## 2. Control

[`hardware/npu/rtl/control`](../hardware/npu/rtl/control)

- AXI-Lite CSR
- layer descriptor
- layer sequencing
- convolution parameter interface
- error aggregation

## 3. Frontend

[`hardware/npu/rtl/frontend`](../hardware/npu/rtl/frontend)

| Block | 역할 |
|---|---|
| `npu_conv1_frontend.v` | Conv1 single-Cin operand path |
| `npu_convn_frontend.v` | Conv2~Conv9 line/weight banks, prefetch, **4-Cin Pin4 operand 공급** |
| `npu_global_frontend.v` | Global Pool control/data bridge |
| `npu_fc_frontend.v` | FC activation/weight scheduling |

## 4. Shared Compute

[`hardware/npu/rtl/compute`](../hardware/npu/rtl/compute)

```text
b_compute_top_16
    │
    └─ unified_compute_core_16
         │
         ├─ Conv Compute Ctrl
         ├─ FC Compute Ctrl
         │
         └─ shared_mac_acc_core
              │
              └─ mac_array_16x3
                   16 OC × 3 Tap × 4 Cin
                   = 192 MAC/cycle
```

Conv와 FC가 별도 MAC array를 갖는 대신 **하나의 Shared Compute Path를 재사용**합니다.

## 5. Post-process

[`hardware/npu/rtl/postprocess`](../hardware/npu/rtl/postprocess)

Conv output:

```text
48-bit Accumulator
    ↓
Bias
    ↓
Per-channel Requantization
    ↓
INT16 Saturation
    ↓
ReLU
    ↓
Optional MaxPool
```

Global Pool은 temporal max + rounded mean을 계산하고, FC는 같은 Shared MAC을 사용한 뒤 FC post-process 경로로 전달됩니다.

## 6. Data Format

- Activation / Weight: signed INT16
- Accumulator / Bias valid width: signed 48-bit
- Requantization: output-channel별 right shift
- Rounding: nearest, ties away from zero
- Saturation: signed INT16
- Final FC2: 527 signed INT16 Q10 logits

정확한 layer dimension과 fixed-point 정보는 [`model/model_manifest.json`](../model/model_manifest.json), [`model/layer_config.csv`](../model/layer_config.csv)를 참고하세요.
