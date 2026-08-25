#ifndef UI_TYPES_H
#define UI_TYPES_H

#include "xil_types.h"

typedef enum
{
    SEC_NORMAL = 0,
    SEC_ACTIVITY = 1,
    SEC_INTRUSION_DAMAGE = 2,
    SEC_CRITICAL = 3,
    SEC_FACILITY_EMERGENCY = 4
} security_level_t;

/*
 * PS 후처리가 최종적으로 만들어 UI/UART에 전달하는 공용 결과 구조체.
 *
 * probability / group score는 PC UI 화면에는 표시하지 않아도
 * 로그/검증 및 threshold 판단을 위해 UART protocol에는 유지한다.
 *
 * *_1e4:
 *   8624 -> 0.8624 -> 86.24 %
 */
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

#endif
