/*
 * main.c — Firmware/motor_ecu_v1.2_broken/src/main.c
 *
 * Deliberately broken firmware for rollback demo:
 *   - Erratic RPM (0 or 3000) and fixed 120°C temperature
 *   - Stops writing heartbeat after 3 ticks → triggers health rollback
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "version.h"
#include "sensor.h"
#include "heartbeat.h"
#include "diagnostics.h"

int main()
{
    int tick = 0;

    printf("\n");
    printf("=================================\n");
    printf("Motor ECU Started\n");
    printf("Firmware Version : %s\n", get_version());
    printf("Mode             : BROKEN\n");
    printf("=================================\n\n");

    while (1)
    {
        tick++;
        int rpm  = get_rpm_broken();
        int temp = get_temperature_broken();

        printf("RPM  = %d  [BROKEN]\n", rpm);
        printf("TEMP = %d  [BROKEN]\n", temp);

        if (tick <= 3) {
            heartbeat_update();
        } else {
            printf("Heartbeat = STOPPED (broken firmware)\n");
        }

        run_diagnostics(rpm, temp);
        printf("----------------------------\n");
        sleep(1);
    }

    return 0;
}
