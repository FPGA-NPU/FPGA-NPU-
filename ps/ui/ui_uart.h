#ifndef UI_UART_H
#define UI_UART_H

#include "ui_types.h"

/*
 * PS UART1은 BSP/ps7_init에서 115200으로 초기화된다.
 * 현재 init 함수는 인터페이스 일관성을 위한 진입점이다.
 */
void ui_uart_init(void);

/*
 * ui_result_t -> RESULT packet
 *
 * RESULT,<seq>,<level>,<winner_class>,<winner_prob_1e4>,
 *        <activity_1e4>,<intrusion_1e4>,<critical_1e4>,
 *        <emergency_1e4>,<inference_us>
 */
void ui_uart_send_result(const ui_result_t *result);

#endif
