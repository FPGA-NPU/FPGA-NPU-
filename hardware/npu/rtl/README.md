# RTL Map

이 디렉터리가 NPU 설계의 핵심입니다.

## 추천 읽기 순서

1. **Top** — [`top/neural_processing_unit_unified_6_0.v`](top/neural_processing_unit_unified_6_0.v)
2. **Pin4 Frontend** — [`frontend/npu_convn_frontend.v`](frontend/npu_convn_frontend.v)
3. **Shared Compute Top** — [`compute/b_compute_top_16.v`](compute/b_compute_top_16.v)
4. **Shared MAC Core** — [`compute/shared_mac_acc_core.v`](compute/shared_mac_acc_core.v)
5. **192-MAC Array** — [`compute/mac_array_16x3.v`](compute/mac_array_16x3.v)
6. **Conv Post-process** — [`postprocess/conv_postprocess_16.v`](postprocess/conv_postprocess_16.v)
7. **Global / FC** — [`postprocess/global_pool_16.v`](postprocess/global_pool_16.v), [`postprocess/fc_postprocess_16.v`](postprocess/fc_postprocess_16.v)

## Folder Map

### `top/`
- `neural_processing_unit_unified_6_0.v` — CSR/control, frontend selection, shared Core를 연결하는 최상위 NPU IP

### `control/`
- `npu_unified_csr_axi_lite.v` — PS 제어용 AXI4-Lite CSR
- `npu_unified_layer_controller.v` — layer sequence / start / done control
- `npu_unified_descriptor_rom.v` — layer descriptor
- `npu_unified_conv_param_system.v` — convolution parameter interface/storage
- `npu_unified_error_reporter.v` — 오류 상태 취합

### `frontend/`
- `npu_conv1_frontend.v` — single-Cin Conv1 path
- `npu_convn_frontend.v` — Conv2~Conv9 **4-Cin Pin4** operand generation/prefetch
- `npu_global_frontend.v` — Global Pool interface
- `npu_fc_frontend.v` — FC scheduling

### `compute/`
- `b_compute_top_16.v` — shared B-core top
- `unified_compute_core_16.v` — Conv/FC unified compute path
- `shared_mac_acc_core.v` — shared MAC + accumulation
- `mac_array_16x3.v` — **16 OC × 3 Tap × 4 Cin = 192 MAC/cycle**
- `conv_compute_ctrl.v` — Conv scheduling
- `fc_compute_ctrl.v` — FC scheduling

### `postprocess/`
- `accumulator_bias_16.v` — accumulation / bias
- `requantize48_to_int16_16.v` — 48-bit → INT16 requantization
- `relu48_16.v` — ReLU
- `maxpool1d48_16.v` — MaxPool
- `conv_postprocess_16.v` — Conv post-process integration
- `global_pool_16.v` — temporal max + rounded mean
- `fc_postprocess_16.v` — FC output processing

### `memory/`
- `npu_unified_operand_buffer.v` — Conv1/FC operand boundary buffer
- `npu_unified_result_buffer.v` — result boundary buffer
- `npu_fc_tile_store.v` — FC tiled-weight storage

### `common/`
- `npu_defs.vh` — shared constants / macros / definitions
