#include "ui_data_source.h"

#include "sleep.h"

typedef enum
{
    TEST_GLASS_1 = 0,
    TEST_GLASS_2,
    TEST_GLASS_3,
    TEST_NORMAL_1,
    TEST_NORMAL_2,
    TEST_KNOCK_1,
    TEST_KNOCK_2,
    TEST_NORMAL_3,
    TEST_NORMAL_4,
    TEST_WAIT
} test_state_t;

static u32 g_seq;
static test_state_t g_state;

static void clear_result(ui_result_t *r)
{
    r->seq = g_seq++;
    r->level = SEC_NORMAL;
    r->winner_class = -1;
    r->winner_probability_1e4 = 0;
    r->activity_1e4 = 0;
    r->intrusion_damage_1e4 = 0;
    r->critical_1e4 = 0;
    r->facility_emergency_1e4 = 0;
    r->inference_us = 183500;
}

static void make_glass(ui_result_t *r)
{
    clear_result(r);

    r->level = SEC_INTRUSION_DAMAGE;
    r->winner_class = 441; /* AudioSet: Glass */

    r->winner_probability_1e4 = 8624;
    r->activity_1e4 = 3120;
    r->intrusion_damage_1e4 = 8624;
    r->critical_1e4 = 840;
    r->facility_emergency_1e4 = 110;
}

static void make_knock(ui_result_t *r)
{
    clear_result(r);

    r->level = SEC_ACTIVITY;
    r->winner_class = 359; /* AudioSet: Knock */

    r->winner_probability_1e4 = 7341;
    r->activity_1e4 = 7341;
    r->intrusion_damage_1e4 = 2120;
    r->critical_1e4 = 210;
    r->facility_emergency_1e4 = 50;
}

static void make_normal(ui_result_t *r)
{
    clear_result(r);
}

void ui_data_source_init(void)
{
    g_seq = 1;
    g_state = TEST_GLASS_1;
}

int ui_data_source_get(ui_result_t *result)
{
    if (result == 0) {
        return -1;
    }

    switch (g_state)
    {
        case TEST_GLASS_1:
        case TEST_GLASS_2:
        case TEST_GLASS_3:
            make_glass(result);
            g_state = (test_state_t)(g_state + 1);
            sleep(2);
            break;

        case TEST_NORMAL_1:
        case TEST_NORMAL_2:
            make_normal(result);
            g_state = (test_state_t)(g_state + 1);
            sleep(2);
            break;

        case TEST_KNOCK_1:
        case TEST_KNOCK_2:
            make_knock(result);
            g_state = (test_state_t)(g_state + 1);
            sleep(2);
            break;

        case TEST_NORMAL_3:
        case TEST_NORMAL_4:
            make_normal(result);
            g_state = (test_state_t)(g_state + 1);
            sleep(2);
            break;

        case TEST_WAIT:
        default:
            /*
             * 테스트 시퀀스 반복 전에 잠시 대기.
             * 다음 호출부터 새 Event 세션이 생성된다.
             */
            make_normal(result);
            g_state = TEST_GLASS_1;
            sleep(4);
            break;
    }

    return 0;
}
