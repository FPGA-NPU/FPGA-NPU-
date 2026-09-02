# Zynq PS Firmware

NPU 실행, DMA 제어, 오디오 capture/playback, 527-logit 후처리와 UART 결과 전송을 담당하는 bare-metal 코드입니다.

## 추천 읽기 순서

1. `helloworld.c` — application entry / mode control
2. `npu_inference.c` — Conv1~FC2 inference sequence
3. `npu_unified_driver.c` — NPU CSR driver
4. `ps_postprocess.c` — 527 logits → security event mapping
5. `audio_capture.c` / `audio_playback.c` — MIC / DEMO audio path
6. `ui_uart.c` — PC UI RESULT packet

## Module Map

| 파일 | 역할 |
|---|---|
| `helloworld.c` | PS application top |
| `npu_inference.c/.h` | 12-layer NPU execution |
| `npu_unified_driver.c/.h` | NPU register/CSR access |
| `npu_memory_map.h` | DDR/MMIO address map |
| `ps_postprocess.c/.h` | Q10 logits 후처리 / security mapping |
| `audio_capture.c/.h` | microphone capture |
| `audio_playback.c/.h` | demo audio playback |
| `ssm2603.c/.h` | audio codec control |
| `ui_uart.c/.h` | UART RESULT protocol |
| `ui_types.h` | PS ↔ PC 공용 결과 구조 |
