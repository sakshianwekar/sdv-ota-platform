#include <stdlib.h>
#include "sensor.h"

int get_rpm(void)
{
    return 1400 + (rand() % 200);
}

int get_temperature(void)
{
    return 40 + (rand() % 10);
}