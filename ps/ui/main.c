#include "platform.h"
#include "ui.h"

int main(void)
{
    init_platform();

    /*
     * UI/PS 담당 코드의 최상위 진입점.
     * 이후 main.c에는 기능 코드를 추가하지 않는다.
     */
    ui_start();

    cleanup_platform();
    return 0;
}
