#ifndef PS_POSTPROCESS_H
#define PS_POSTPROCESS_H

#include "xil_types.h"
#include "ui_types.h"

#define AUDIOSET_CLASS_COUNT 527

/*
 * 최종 PL 출력:
 *   logits[527]
 *   signed INT16
 *   Q10
 *
 * 이 함수가 향후 담당할 처리:
 *
 *   Q10 logits
 *      -> real value
 *      -> sigmoid
 *      -> winner_class / winner probability
 *      -> security class mapping
 *      -> ui_result_t
 *
 * 실제 구현은 Golden 527 logits 보드 검증 단계에서 추가한다.
 */
int ps_postprocess(
    const s16 logits[AUDIOSET_CLASS_COUNT],
    ui_result_t *result
);

#endif
