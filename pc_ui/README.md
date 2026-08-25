# FPGA NPU Acoustic Security Monitor UI v10

PySide6 기반 PC 모니터링 UI입니다.

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

화면의 확률 표시는 제거했습니다. Top-K 후보 목록도 제거하고 대표 AudioSet 클래스 하나만 표시합니다.

## UART

Zybo Z7-20에서 현재 검증된 연결은 다음과 같습니다.

```text
PS UART1
MIO 48 / 49
115200 baud
8-N-1
PC device: /dev/ttyUSB1
```

`RESULT` packet:

```text
RESULT,<seq>,<level>,<winner_class>,<winner_prob_1e4>,<activity_1e4>,<intrusion_1e4>,<critical_1e4>,<emergency_1e4>,<inference_us>
```

확률 필드는 PS/Vitis 프로토콜 호환 및 내부 판단/로그를 위해 수신하지만 메인 UI에는 표시하지 않습니다.

## 1. UART 장치 확인

```bash
ls -l /dev/ttyUSB*
```

현재 실보드에서는 `/dev/ttyUSB1`을 PS UART1 통신에 사용합니다. 필요하면 USB interface도 확인할 수 있습니다.

```bash
udevadm info --query=property --name=/dev/ttyUSB1 | grep -E 'ID_MODEL|ID_USB_INTERFACE_NUM'
```

Digilent Adept 연결에서 `/dev/ttyUSB0`은 JTAG/hw_server에서 사용될 수 있으므로 현재 UI 연결에는 `/dev/ttyUSB1`을 사용합니다.

## 2. Serial port 점유 확인

UI 실행 전에 `picocom`, `screen` 등 다른 프로그램이 `/dev/ttyUSB1`을 열고 있지 않아야 합니다.

```bash
sudo fuser -v /dev/ttyUSB1
```

하나의 serial device를 터미널 프로그램과 PySide6 UI가 동시에 열 수 없습니다.

## 3. 의존성 설치

```bash
cd pc_ui
pip install -r requirements.txt
```

## 4. 실제 Zybo UART 연결로 UI 실행

```bash
python main.py \
  --port /dev/ttyUSB1 \
  --baud 115200 \
  --labels /home/byeonguk/workspaces/NPU/npu_leenet11/audioset_tagging_cnn/metadata/class_labels_indices.csv
```

정상 연결 시 UI 우측 상단에 다음과 같이 표시됩니다.

```text
UART 연결됨 /dev/ttyUSB1
```

보드에서 `RESULT` packet이 들어오면 현재 보안 상태, 대표 감지 음향, 진행 중 이벤트 및 이벤트 기록이 갱신됩니다.

## 5. 로그 저장 위치 지정

기본적으로 `pc_ui/logs/` 아래에 다음 파일이 생성됩니다.

```text
logs/
├── raw_results_YYYYMMDD_HHMMSS.csv
└── event_sessions_YYYYMMDD_HHMMSS.csv
```

다른 위치를 지정하려면:

```bash
python main.py \
  --port /dev/ttyUSB1 \
  --baud 115200 \
  --labels /home/byeonguk/workspaces/NPU/npu_leenet11/audioset_tagging_cnn/metadata/class_labels_indices.csv \
  --log-dir ./logs
```

- `raw_results_*`: UART에서 수신한 모든 RESULT packet
- `event_sessions_*`: 종료된 보안 이벤트 세션 요약

## 6. 데모 모드

`--port` 옵션을 생략하면 실제 UART를 열지 않고 키보드 입력 기반 데모 모드로 동작합니다.

```bash
python main.py
```

데모 모드 키:

- `0`: 정상
- `1`: 노크
- `2`: 유리 파손
- `3`: 총성
- `4`: 화재 경보

## 이벤트 세션 정책

현재 세션 종료 조건은 `NORMAL(level=0)` packet 2회 연속 수신입니다.

## 참고

우측 상단 waveform은 UI 장식용입니다. 현재 UART 프로토콜은 음향 waveform sample 자체를 PC로 전송하지 않으므로 실제 오디오 파형이 아닙니다.
