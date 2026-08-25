#include "ui.h"

#include "ui_uart.h"
#include "ui_data_source.h"

void ui_send_result(const ui_result_t *result)
{
    if (result == 0) {
        return;
    }

    ui_uart_send_result(result);
}

void ui_start(void)
{
    ui_result_t result;

    ui_uart_init();
    ui_data_source_init();

    while (1)
    {
        /*
         * 현재:
         *   ui_data_source_get() -> 테스트 결과 생성
         *
         * 최종:
         *   ui_data_source_get()
         *      -> npu_wait_done()
         *      -> npu_get_output(logits, 527)
         *      -> ps_postprocess(logits, &result)
         *
         * main.c와 ui_uart.c는 수정할 필요가 없다.
         */
        if (ui_data_source_get(&result) == 0)
        {
            ui_send_result(&result);
        }
    }
}
