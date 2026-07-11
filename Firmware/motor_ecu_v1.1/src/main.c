/*
 * main.c — Firmware/motor_ecu_v1.1/src/main.c
 *
 * Firmware v1.1 — Eco Mode
 * Changes from v1.0:
 *   - Prints "v1.1 [ECO]" on startup so the demo visibly shows
 *     the firmware changed after an OTA update
 *   - Calls get_rpm_eco() and get_temperature_eco() instead of
 *     the standard functions — RPM capped at 60%, temp reduced 5C
 *   - Everything else identical to v1.0
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
    printf("\n");
    printf("=================================\n");
    printf("Motor ECU Started\n");
    printf("Firmware Version : %s\n", get_version());
    printf("Mode             : ECO\n");
    printf("=================================\n\n");

    while(1)
    {
        int rpm  = get_rpm_eco();
        int temp = get_temperature_eco();

        printf("RPM  = %d  [ECO]\n", rpm);
        printf("TEMP = %d  [ECO]\n", temp);
        heartbeat_update();
        run_diagnostics(rpm, temp);
        printf("----------------------------\n");
        sleep(1);
    }

    return 0;
}
