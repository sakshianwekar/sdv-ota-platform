#include <stdio.h>
#include "diagnostics.h"

void run_diagnostics(int soc, int voltage)
{
    if (soc > 10 && voltage > 300) {
        printf("Diagnostics : PASS\n");
    } else {
        printf("Diagnostics : FAIL\n");
    }
}
