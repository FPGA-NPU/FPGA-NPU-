# FPGA NPU for Real-Time Acoustic Security Monitoring

Zybo Z7-20(Zynq-7020)에 **LeeNet11 INT16 추론기를 직접 RTL로 구현**한 FPGA NPU 프로젝트입니다.
PL에서 12개 레이어를 수행하고 527개 AudioSet logits를 PS로 전달한 뒤, 보안 이벤트로 후처리하여 PC UI에 표시합니다.

## 핵심 결과

| 항목 | v6 결과 |
|---|---:|
| NPU 구조 | Custom RTL, Shared Conv/FC Compute |
| Peak compute | **192 MAC/cycle** (`16 OC × 3 Tap × 4 Cin`) |
| DSP | 192 |
| LUT / FF | 43,157 / 58,781 |
| Timing | WNS **+0.497 ns**, WHS **+0.008 ns** |
| Golden verification | **12 / 12 layers PASS** |
| Final output | **527 / 527 logits exact match** |
| Conv2 active cycles vs v3 | **6.095× reduction** |
| 12-layer operation time vs v3 | **3.908× improvement** |

## 시스템 구조

```text
MIC / DDR Demo Audio
        │
        ▼
   Zynq PS / DDR
        │ AXI DMA
        ▼
┌────────────────────────────────────────┐
│               Custom NPU               │
│                                        │
│  Control → Frontend → Shared Compute   │
│                         │              │
│                    192-MAC Array       │
│                         │              │
│                    Post-process        │
│                    ├─ Global Pool      │
│                    └─ FC               │
└────────────────────────────────────────┘
        │
        ▼
527 × INT16 Q10 logits
        │
        ▼
PS Post-processing → Security Event → UART → PC UI
```

## 처음 볼 때는 여기부터

| 보고 싶은 내용 | 바로가기 |
|---|---|
| **NPU 전체 구조** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| **RTL 전체 지도** | [`hardware/npu/rtl/README.md`](hardware/npu/rtl/README.md) |
| NPU Top | [`neural_processing_unit_unified_6_0.v`](hardware/npu/rtl/top/neural_processing_unit_unified_6_0.v) |
| Conv2~9 Pin4 입력 공급 | [`npu_convn_frontend.v`](hardware/npu/rtl/frontend/npu_convn_frontend.v) |
| Shared MAC | [`shared_mac_acc_core.v`](hardware/npu/rtl/compute/shared_mac_acc_core.v) |
| **192-MAC datapath** | [`mac_array_16x3.v`](hardware/npu/rtl/compute/mac_array_16x3.v) |
| Conv 후처리 | [`conv_postprocess_16.v`](hardware/npu/rtl/postprocess/conv_postprocess_16.v) |
| PS 추론 흐름 | [`npu_inference.c`](software/ps/npu_inference.c) |
| NPU Driver | [`npu_unified_driver.c`](software/ps/npu_unified_driver.c) |
| PC Monitoring UI | [`software/pc_ui`](software/pc_ui) |
| Golden 검증 결과 | [`docs/VALIDATION.md`](docs/VALIDATION.md) |
| v3 → v6 최적화 | [`docs/OPTIMIZATION_V3_TO_V6.md`](docs/OPTIMIZATION_V3_TO_V6.md) |

## Repository Layout

```text
.
├── hardware/
│   ├── npu/                  # Custom NPU IP
│   │   └── rtl/
│   │       ├── top/          # NPU top
│   │       ├── control/      # CSR / layer control / descriptor
│   │       ├── frontend/     # Conv1 / ConvN / Global / FC input scheduling
│   │       ├── compute/      # Shared MAC / 192-MAC array / mode controllers
│   │       ├── postprocess/  # Requant / ReLU / MaxPool / Global / FC output
│   │       ├── memory/       # Operand / result / FC tile storage
│   │       └── common/       # Shared definitions
│   ├── soc/                  # Minimal Vivado SoC sources + rebuild.tcl
│   ├── baseline/             # Exact verified v6 XSA
│   └── reports/              # Timing / utilization / hierarchy
│
├── software/
│   ├── ps/                   # Zynq bare-metal application
│   └── pc_ui/                # PySide6 monitoring UI
│
├── model/                    # LeeNet11 HW mapping metadata
├── validation/               # Golden/demo validation scripts + evidence
└── docs/                     # Architecture / optimization / validation
```

## RTL 구조

```text
NPU Top
  │
  ├─ Control
  │   ├─ AXI-Lite CSR
  │   ├─ Layer Controller
  │   └─ Descriptor / Conv Parameters
  │
  ├─ Frontend
  │   ├─ Conv1
  │   ├─ Conv2~Conv9 Pin4
  │   ├─ Global
  │   └─ FC
  │
  └─ Shared Compute
      ├─ Conv / FC Control
      ├─ Shared MAC + Accumulator
      │   └─ 16 OC × 3 Tap × 4 Cin = 192 MAC/cycle
      └─ Post-process
          ├─ Requantization
          ├─ ReLU / MaxPool
          ├─ Global Pool
          └─ FC Post-process
```

## Vivado 재구성

생성된 `.xpr`, `.cache`, `.gen`, `.runs`, `.hw` 디렉터리는 저장소에 포함하지 않습니다.
최소 SoC 원본만 `hardware/soc/`에 유지합니다.

```text
hardware/soc/
├── design_SoC.bd
├── design_SoC_wrapper.v
├── constraints/audio_io.xdc
└── rebuild.tcl
```

Vivado 2024.2 Tcl Console에서:

```tcl
source hardware/soc/rebuild.tcl
```

재생성된 프로젝트는 `build/vivado/` 아래에 생성됩니다.

## 검증 기준본

`hardware/baseline/verified_v6.xsa`는 v6 실보드 검증에 사용한 정확한 hardware handoff입니다.

```text
SHA-256
992fc64e1515aa17b24d4d6b59b26bb6e9fb870a714d3da3382de0919b226ea9
```

Golden 검증에서는 다음 전체 경로가 bit-exact를 통과했습니다.

```text
Conv1 → Conv2 → ... → Conv9 → Global → FC1 → FC2
12 / 12 layers : mismatch 0
Final FC2      : 527 / 527 logits exact match
```

## Binary / Dataset Policy

모델 binary, Golden tensor binary, demo WAV/PCM, bitstream, ELF는 source repository에서 제외했습니다.
소스 구조와 검증 근거를 중심으로 공개하며, 외부 자산 관련 내용은 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)를 참고하세요.
