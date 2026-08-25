# Zybo Z7-20 PS Bring-up Notes

## UART

- PS UART1
- MIO 48 / 49
- 115200 baud
- 8-N-1
- Linux device during verification: `/dev/ttyUSB1`

## DDR preset issue found during bring-up

Board Part가 Zybo Z7-20으로 설정되어 있어도 기존 `processing_system7_0` 내부 설정에 다른 DDR preset이 남아 있을 수 있습니다.

검증 시 잘못된 값:

```text
PARTNO          MT41J128M8 JP-125
DRAM_WIDTH      8 Bits
DEVICE_CAPACITY 1024 MBits
BOARD_DELAY0    0.25
```

Zybo Board Preset 적용 후 정상 값:

```text
PARTNO          MT41K256M16 RE-125
DRAM_WIDTH      16 Bits
DEVICE_CAPACITY 4096 MBits
BOARD_DELAY0    0.221
```

잘못된 DDR 설정에서는 DDR의 `0x00100000`에 배치된 ELF 실행이 불안정해지고 DAP/APU 접근 오류 및 UART 무출력이 함께 나타났습니다.

## Vivado quick checks

```tcl
set ps [get_bd_cells processing_system7_0]
get_property CONFIG.PCW_UIPARAM_DDR_PARTNO $ps
get_property CONFIG.PCW_UIPARAM_DDR_DRAM_WIDTH $ps
get_property CONFIG.PCW_UIPARAM_DDR_DEVICE_CAPACITY $ps
get_property CONFIG.PCW_UIPARAM_DDR_BOARD_DELAY0 $ps

get_property CONFIG.PCW_UART1_PERIPHERAL_ENABLE $ps
get_property CONFIG.PCW_UART1_UART1_IO $ps
get_property CONFIG.PCW_UART1_BAUD_RATE $ps
```
