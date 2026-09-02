# Hardware

```text
hardware/
├── npu/       # Custom NPU RTL — start here
├── soc/       # Minimal Zybo Z7-20 SoC sources
├── baseline/  # Exact verified v6 XSA
└── reports/   # Timing / utilization / hierarchy
```

## 1. NPU RTL

[`npu/rtl/README.md`](npu/rtl/README.md)에서 RTL 구조를 한눈에 볼 수 있습니다.

핵심 경로:

```text
npu/rtl/
├── top/
├── control/
├── frontend/
├── compute/
├── postprocess/
├── memory/
└── common/
```

## 2. SoC source

Vivado 생성물을 통째로 저장하지 않고 재구성에 필요한 최소 파일만 유지합니다.

```text
soc/
├── design_SoC.bd
├── design_SoC_wrapper.v
├── constraints/audio_io.xdc
└── rebuild.tcl
```

Vivado 2024.2 Tcl Console:

```tcl
source hardware/soc/rebuild.tcl
```

## 3. Verified baseline

`baseline/verified_v6.xsa`

```text
SHA-256
992fc64e1515aa17b24d4d6b59b26bb6e9fb870a714d3da3382de0919b226ea9
```

## 4. Reports

- `reports/timing_summary.rpt`
- `reports/utilization.rpt`
- `reports/npu_hierarchy.rpt`
