#ifndef UI_DATA_SOURCE_H
#define UI_DATA_SOURCE_H

#include "ui_types.h"

void ui_data_source_init(void);

/*
 * 한 번 호출할 때 ui_result_t 한 건을 반환한다.
 *
 * return 0 : result valid
 * return != 0 : result unavailable/error
 *
 * 현재 구현은 UART/UI 검증용 TEST SOURCE.
 * 최종 구현에서는 PL NPU 결과 provider로 교체한다.
 */
int ui_data_source_get(ui_result_t *result);

#endif
