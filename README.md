# NPU 기반 무인시설 환경음 분석 및 보안 모니터링 시스템

Zybo Z7-20의 Zynq-7000 PS/PL 구조를 이용해 LeeNet11(AudioSet 527 class) 기반 음향 이벤트 추론 결과를 실시간 보안 이벤트로 가공하고 PC UI에 표시하는 프로젝트입니다.

현재 저장소에는 **PS UI/후처리 인터페이스 골격**과 **PySide6 PC 모니터링 UI**가 포함되어 있습니다. PL NPU 연산 코어와 실제 `npu_driver` 연결은 이후 통합 단계에서 추가됩니다.

## 현재 데이터 경로

```text
PL NPU
  -> 527 x INT16 Q10 logits
  -> PS ps_postprocess()
  -> ui_result_t
  -> ui_send_result()
  -> PS UART1 / 115200
  -> PC PySide6 UI
  -> 실시간 이벤트 표시 + CSV 로그
```

현재 `ps/ui/ui_data_source.c`는 통합 전 검증을 위해 테스트 이벤트를 생성합니다. 최종 통합 시 이 파일 내부를 `npu_wait_done() -> npu_get_output() -> ps_postprocess()` 경로로 교체합니다.

## 디렉터리

```text
.
├── ps/
│   └── ui/           # Zybo/Vitis PS UI 모듈
├── pc_ui/            # PySide6 PC 모니터링 UI
└── docs/             # 구조 및 통합 문서
```

## 검증 완료

- Zybo Z7-20 PS UART1: MIO 48/49, 115200, 8-N-1
- `RESULT` UART packet 실보드 송수신
- PC UI에서 보안 상태/대표 감지 음향 실시간 표시
- 동일 이벤트 세션 유지 및 NORMAL 2회 연속 시 세션 종료
- Raw RESULT CSV 및 Event Session CSV 저장
- 테스트 이벤트 `Glass -> Normal -> Knock -> Normal` 실보드 연동 확인

## 주요 UART Packet

```text
RESULT,<seq>,<level>,<winner_class>,<winner_prob_1e4>,<activity_1e4>,<intrusion_1e4>,<critical_1e4>,<emergency_1e4>,<inference_us>
```

예:

```text
RESULT,1,2,441,8624,3120,8624,840,110,183500
```

`level=2`, `class=441`은 PC UI에서 `침입 / 파손 위험`, `유리 소리`로 표시됩니다.

자세한 통합 규격은 [`docs/UI_PS_INTEGRATION.md`](docs/UI_PS_INTEGRATION.md)를 참고하세요.
