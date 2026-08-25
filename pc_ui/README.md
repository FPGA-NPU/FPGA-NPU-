# FPGA NPU Acoustic Security Monitor UI v9

사용자가 선택한 최종 방향에 맞춰 이미지 콘셉트를 PySide6 코드로 구현한 버전입니다.

## 화면 구성

- 상단: `FPGA NPU 기반 실시간 음향 보안 이벤트 모니터링 시스템`
- 좌측 상단: 현재 보안 상태
- 우측 상단: 감지된 소리(대표 감지 음향)
- 중단: 진행 중인 보안 이벤트
  - 이벤트 번호
  - 최초 감지 시각
  - 최종 감지 시각
  - 지속 시간
  - 감지 횟수
- 하단: 이벤트 발생 기록

화면의 확률 표시는 모두 제거했습니다.
Top-K 후보 목록도 제거하고 대표 AudioSet 클래스 하나만 표시합니다.
`보안 이벤트 분류` 별도 패널도 제거했습니다.

## UART

기존 RESULT 패킷을 그대로 사용합니다.

```text
RESULT,<seq>,<level>,<winner_class>,<winner_prob_1e4>,<activity_1e4>,<intrusion_1e4>,<critical_1e4>,<emergency_1e4>,<inference_us>
```

확률 필드는 PS/Vitis 프로토콜 호환 및 내부 판단을 위해 수신하지만 UI에는 표시하지 않습니다.

## 실행

```bash
pip install -r requirements.txt
python main.py
```

`--port`가 없으면 데모 모드입니다.

데모 모드 키:
- `0`: 정상
- `1`: 노크
- `2`: 유리 파손
- `3`: 총성
- `4`: 화재 경보

실제 UART 연결 시작 코드:

```bash
python main.py --port /dev/ttyUSB0 --baud 115200 \
  --labels /home/byeonguk/workspaces/NPU/npu_leenet11/audioset_tagging_cnn/metadata/class_labels_indices.csv
```

## 참고

우측 상단 waveform은 UI 장식용입니다. 현재 UART 프로토콜은 음향 waveform 샘플 자체를 PC로 보내지 않으므로 실제 오디오 파형을 표시하는 기능은 아닙니다.


## v10 - CSV 영구 로그

프로그램 실행 시 기본적으로 UI 폴더 아래 `logs/`에 다음 두 파일을 생성합니다.

```text
logs/
├── raw_results_YYYYMMDD_HHMMSS.csv
└── event_sessions_YYYYMMDD_HHMMSS.csv
```

- `raw_results_*`: UART에서 수신한 모든 RESULT 패킷
- `event_sessions_*`: 종료된 보안 이벤트 세션 요약

다른 위치를 사용하려면:

```bash
python main.py --port /dev/ttyUSB1 --baud 115200 --log-dir ./my_logs
```

현재 세션 종료 조건은 NORMAL(level=0) 패킷 2회 연속입니다.
