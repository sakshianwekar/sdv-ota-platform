#include <stdlib.h>
#include "sensor.h"

int get_soc(void)
{
    return 80 + (rand() % 15);
}

int get_voltage(void)
{
    return 380 + (rand() % 20);
}
