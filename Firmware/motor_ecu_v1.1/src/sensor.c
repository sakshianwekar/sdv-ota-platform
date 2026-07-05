/*
 * sensor.c — Firmware/motor_ecu_v1.1/src/sensor.c
 *
 * Changes from v1.0:
 *   - get_rpm_eco()         RPM capped at 60% of v1.0 max (max ~960 vs ~1600)
 *   - get_temperature_eco() temp reduced by 5C vs v1.0
 *
 * v1.0 functions are kept so the file compiles against the same sensor.h
 * — they are just not called in v1.1 main.c
 */

#include <stdlib.h>
#include "sensor.h"

/* ── v1.0 originals (unchanged) ─────────────────────────────────────── */
int get_rpm(void)
{
    return 1400 + (rand() % 200);   /* 1400–1600 RPM */
}

int get_temperature(void)
{
    return 40 + (rand() % 10);      /* 40–49 °C */
}

/* ── v1.1 Eco Mode variants ─────────────────────────────────────────── */

/*
 * get_rpm_eco()
 * 60% of v1.0 max: base 840, range 840–960
 * v1.0 was 1400–1600, so 60% = 840–960
 */
int get_rpm_eco(void)
{
    return 840 + (rand() % 120);
}

/*
 * get_temperature_eco()
 * 5°C cooler than v1.0: base 35, range 35–44°C
 * v1.0 was 40–49°C
 */
int get_temperature_eco(void)
{
    return 35 + (rand() % 10);
}
