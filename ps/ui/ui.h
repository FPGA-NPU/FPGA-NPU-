#ifndef UI_H
#define UI_H

#include "ui_types.h"

/*
 * UI/PS 모듈 전체 시작.
 *
 * main.c에서는 이 함수 하나만 호출한다.
 * 현재는 ui_data_source가 테스트 결과를 공급하며,
 * 나중에는 PL NPU 결과를 PS에서 후처리하여 공급하도록 교체한다.
 */
void ui_start(void);

/*
 * 이미 완성된 ui_result_t 한 건을 PC UI로 전송.
 *
 * 다른 모듈에서 결과를 직접 전달해야 할 때 사용할 수 있다.
 */
void ui_send_result(const ui_result_t *result);

#endif
