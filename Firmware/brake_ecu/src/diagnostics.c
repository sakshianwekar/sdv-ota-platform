#include <stdio.h>
#include "diagnostics.h"

void run_diagnostics(int pressure, int temp)
{
    if (pressure > 0 && temp < 100) {
        printf("Diagnostics : PASS\n");
    } else {
        printf("Diagnostics : FAIL\n");
    }
}
