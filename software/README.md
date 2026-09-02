# Software

```text
software/
├── ps/       # Zynq bare-metal firmware
└── pc_ui/    # PySide6 monitoring UI
```

## PS firmware

[`ps/README.md`](ps/README.md)에서 파일별 역할과 추천 읽기 순서를 확인할 수 있습니다.

전체 실행 흐름:

```text
Audio input
   ↓
npu_inference
   ↓
NPU driver / DMA
   ↓
527 INT16 Q10 logits
   ↓
ps_postprocess
   ↓
ui_result_t
   ↓
UART RESULT packet
```

## PC UI

[`pc_ui/README.md`](pc_ui/README.md) 참고.
UART RESULT packet을 받아 현재 보안 상태, 대표 감지 음향, 진행 이벤트 및 이력을 표시합니다.
