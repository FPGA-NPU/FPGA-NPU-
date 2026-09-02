# Custom NPU IP — v6

Vivado custom IP로 패키징된 LeeNet11 INT16 NPU입니다.
**실제 RTL은 [`rtl/`](rtl/) 아래에서 기능별로 분리**되어 있습니다.

## 데이터 흐름

```text
Top / Layer Control
        │
        ▼
Frontend Selection
 ├─ Conv1
 ├─ ConvN Pin4
 ├─ Global
 └─ FC
        │
        ▼
Shared Compute Core
        │
        ▼
192-MAC Array + Accumulator
        │
        ▼
Post-process / Global / FC
```

## 폴더

| 폴더 | 역할 |
|---|---|
| [`rtl/top`](rtl/top) | 전체 NPU IP top |
| [`rtl/control`](rtl/control) | AXI-Lite CSR, 레이어 제어, descriptor/parameter 관리 |
| [`rtl/frontend`](rtl/frontend) | 레이어별 operand 공급 및 scheduling |
| [`rtl/compute`](rtl/compute) | Conv/FC 공유 MAC datapath와 compute control |
| [`rtl/postprocess`](rtl/postprocess) | Requant, ReLU, MaxPool, Global Pool, FC output |
| [`rtl/memory`](rtl/memory) | Operand/result buffer, FC tiled-weight store |
| [`rtl/common`](rtl/common) | 공용 RTL definition |

Vivado IP 등록 정보는 `component.xml`, GUI 정의는 `xgui/`에 있습니다.
