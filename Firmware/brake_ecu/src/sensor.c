#include <stdlib.h>
#include "sensor.h"

int get_brake_pressure(void)
{
    return 40 + (rand() % 20);
}

int get_temperature(void)
{
    return 30 + (rand() % 10);
}
