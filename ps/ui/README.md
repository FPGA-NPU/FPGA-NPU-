# Zybo PS UI Module

Vitis standalone application에서 사용하는 UI/PS 모듈입니다.

## Sources

- `main.c`: `init_platform()` 후 `ui_start()`만 호출
- `ui.c/.h`: UI/PS 최상위 제어
- `ui_types.h`: `ui_result_t`, security level 정의
- `ui_uart.c/.h`: `RESULT` UART packet 송신
- `ui_data_source.c/.h`: 현재 테스트 데이터 공급, 최종 NPU 데이터 공급부로 교체
- `ps_postprocess.h`: 527 x Q10 logits 후처리 API 골격
- `INTEGRATION_EXAMPLE.c.txt`: 실제 PL 연결 예시

## Vitis build source

현재 테스트 빌드에는 아래 `.c` 파일을 추가합니다.

```text
main.c
ui.c
ui_uart.c
ui_data_source.c
```

최종 PL 연결 시 `ui_data_source.c` 내부에서 `npu_driver`와 `ps_postprocess()`를 호출하도록 변경합니다.
