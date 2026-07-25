/*
 * sensor.c — Firmware/motor_ecu_v1.2_broken/src/sensor.c
 *
 * Deliberately broken sensors for rollback demo:
 *   - get_temperature_broken() always returns 120°C
 *   - get_rpm_broken() returns 0 or 3000 (erratic)
 */

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

int get_rpm_broken(void)
{
    return (rand() % 2 == 0) ? 0 : 3000;
}

int get_temperature_broken(void)
{
    return 120;
}
