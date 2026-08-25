# UI / PS 통합 구조 및 현재 검증 상태

## 1. 목적

이 문서는 Zybo Z7-20 기반 FPGA NPU 프로젝트에서 PS 담당 UI/후처리 코드의 역할, 현재 검증 상태, PL NPU와의 최종 연결 인터페이스를 공유하기 위한 문서입니다.

현재 PS/UI 경로는 실보드 UART와 PC UI까지 검증되었습니다. 앞으로 남은 핵심 작업은 PL에서 생성되는 **527개 INT16 Q10 logits**를 PS로 받아 실제 `ps_postprocess()`에 연결하는 것입니다.

## 2. 최종 구조

```text
[PL NPU]
  FC2 output: 527 x signed INT16 Q10 logits
        |
        v
[PS npu_driver]
  npu_wait_done()
  npu_get_output(logits, 527)
        |
        v
[PS ps_postprocess]
  Q10 -> sigmoid
  대표 AudioSet class 선택
  보안 event mapping
        |
        v
[ui_result_t]
        |
        v
[ui_send_result]
        |
        v
[PS UART1 / 115200]
        |
        v
[PC PySide6 UI]
  현재 보안 상태
  대표 감지 음향
  진행 중 이벤트
  이벤트 기록
  CSV 로그
```

## 3. 코드 책임 분리

### `main.c`

최종 진입점만 담당합니다.

```c
int main(void)
{
    init_platform();
    ui_start();
    cleanup_platform();
    return 0;
}
```

기능 코드는 `main.c`에 추가하지 않는 것을 원칙으로 합니다.

### `ui.c / ui.h`

UI/PS 담당 코드의 최상위 제어 모듈입니다.

- `ui_start()` : UI/PS 루프 시작
- `ui_send_result()` : 완성된 `ui_result_t`를 UART 모듈에 전달

### `ui_types.h`

PS 후처리와 UI 전송 사이의 공용 구조체를 정의합니다.

```c
typedef struct
{
    u32 seq;
    security_level_t level;
    int winner_class;
    u16 winner_probability_1e4;
    u16 activity_1e4;
    u16 intrusion_damage_1e4;
    u16 critical_1e4;
    u16 facility_emergency_1e4;
    u32 inference_us;
} ui_result_t;
```

### `ui_uart.c / ui_uart.h`

`ui_result_t`를 UART `RESULT` packet으로 변환합니다.

### `ui_data_source.c / ui_data_source.h`

현재는 통합 전 검증용 TEST source입니다.

현재 순환 테스트:

```text
Glass x3
NORMAL x2
Knock x2
NORMAL x2
반복
```

최종 통합 시 이 파일 내부만 실제 NPU provider로 교체합니다.

### `ps_postprocess.h`

향후 실제 PL 출력 후처리 API를 고정하기 위한 헤더입니다.

```c
int ps_postprocess(
    const s16 logits[527],
    ui_result_t *result
);
```

## 4. 실제 PL 연결 시 변경점

현재 테스트 값 생성부:

```c
make_glass(result);
```

최종 구조:

```c
npu_start();
npu_wait_done();
npu_get_output(logits, 527);
ps_postprocess(logits, result);
result->seq = g_seq++;
```

따라서 최종 통합 시 `main.c`, `ui.c`, `ui_uart.c`, PC UI는 유지하고 데이터 공급부만 실제 PL 결과로 변경할 수 있습니다.

## 5. UART 규격

보드: Zybo Z7-20

```text
PS UART1
MIO 48 / 49
115200 baud
8-N-1
```

Packet:

```text
RESULT,<seq>,<level>,<winner_class>,<winner_prob_1e4>,<activity_1e4>,<intrusion_1e4>,<critical_1e4>,<emergency_1e4>,<inference_us>
```

예:

```text
RESULT,1,2,441,8624,3120,8624,840,110,183500
```

보안 등급:

```text
0 NORMAL
1 ACTIVITY
2 INTRUSION_DAMAGE
3 CRITICAL
4 FACILITY_EMERGENCY
```

## 6. PC UI 동작

PC UI는 UART 결과를 받아 다음 정보를 표시합니다.

- 현재 보안 상태
- 대표 감지 음향 1개
- 진행 중 이벤트 번호
- 최초/최종 감지 시각
- 지속 시간
- 감지 횟수
- 종료 이벤트 기록

확률 값은 화면에는 표시하지 않지만 검증 및 threshold 정책을 위해 Raw CSV에는 유지합니다.

## 7. 이벤트 세션 정책

동일 이벤트의 반복 추론 결과는 별도 이벤트로 생성하지 않고 하나의 세션으로 유지합니다.

현재 종료 조건:

```text
NORMAL packet 2회 연속 수신
```

종료 시 이벤트 기록과 `event_sessions_*.csv`에 저장됩니다.

## 8. CSV 로그

PC UI 실행 시 기본적으로 `pc_ui/logs/` 아래 두 파일을 생성합니다.

```text
raw_results_YYYYMMDD_HHMMSS.csv
event_sessions_YYYYMMDD_HHMMSS.csv
```

### Raw log

모든 RESULT packet을 기록합니다.

### Event session log

종료된 이벤트별로 다음을 기록합니다.

- event id
- first / last / end timestamp
- duration
- max security level
- representative class
- representative sound
- hit count

## 9. 실보드 검증 결과

2026-08-25 Zybo Z7-20에서 다음 경로를 확인했습니다.

```text
Vitis PS test source
 -> ui_result_t
 -> ui_uart_send_result
 -> PS UART1
 -> /dev/ttyUSB1
 -> PySide6 UI
 -> Event session / CSV
```

실제 저장 로그에서 확인된 예:

| Event | 보안 상태 | 대표 감지 음향 | Hits | Duration |
|---|---|---|---:|---:|
| #001 | 침입 / 파손 위험 | 유리 소리 | 2 | 6.000 s |
| #002 | 활동 감지 | 노크 소리 | 2 | 6.001 s |
| #003 | 침입 / 파손 위험 | 유리 소리 | 3 | 8.001 s |

## 10. Bring-up 중 확인된 중요 사항

초기에는 프로젝트 Board Part가 Zybo Z7-20으로 선택되어 있었지만 PS7 내부 DDR preset이 다른 메모리 설정으로 남아 있어 APU/DAP 오류와 UART 무출력 문제가 발생했습니다.

잘못된 DDR 예:

```text
MT41J128M8 JP-125
DRAM width 8 bit
Device capacity 1024 Mbit
Board delay 0.25
```

Zybo Z7-20 Board Preset 재적용 후:

```text
MT41K256M16 RE-125
DRAM width 16 bit
Device capacity 4096 Mbit
Board delay0 0.221
```

으로 수정되었고 이후 ELF 실행과 UART 통신이 정상화되었습니다.

따라서 Zybo PS Block Design 생성 시 **Board Part 선택뿐 아니라 ZYNQ7 Processing System에 Board Preset이 실제 적용되어 있는지 확인해야 합니다.**

## 11. 다음 작업

1. Golden 527 Q10 logits 기반 `ps_postprocess()` 구현 및 보드 검증
2. Q10 -> sigmoid -> Top1 class 처리
3. Security whitelist mapping 적용
4. 실제 `npu_driver` API와 `ui_data_source_get()` 연결
5. PL inference timing을 `inference_us`에 실제 측정값으로 반영
6. 최종 threshold 정책 검증 및 고정
