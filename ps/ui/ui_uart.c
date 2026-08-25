#include "ui_uart.h"
#include "xil_printf.h"

void ui_uart_init(void)
{
    /*
     * Zybo Z7-20:
     *   PS UART1
     *   MIO 48/49
     *   115200 baud
     *   8-N-1
     *
     * ps7_init/BSP에서 이미 초기화되므로 추가 설정 없음.
     */
}

void ui_uart_send_result(const ui_result_t *result)
{
    if (result == 0) {
        return;
    }

    /*
     * xil_printf에서 32-bit 정수는 %u/%d를 사용한다.
     * %lu 사용 시 환경에 따라 argument decoding 문제가 생길 수 있으므로
     * 현재 검증된 형식을 유지한다.
     */
    xil_printf(
        "RESULT,%u,%d,%d,%u,%u,%u,%u,%u,%u\r\n",
        (unsigned int)result->seq,
        (int)result->level,
        result->winner_class,
        (unsigned int)result->winner_probability_1e4,
        (unsigned int)result->activity_1e4,
        (unsigned int)result->intrusion_damage_1e4,
        (unsigned int)result->critical_1e4,
        (unsigned int)result->facility_emergency_1e4,
        (unsigned int)result->inference_us
    );
}
