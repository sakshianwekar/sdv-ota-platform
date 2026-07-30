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
    printf("Brake ECU Started\n");
    printf("Firmware Version : %s\n", get_version());
    printf("=================================\n\n");

    while (1) {
        int pressure = get_brake_pressure();
        int temp = get_temperature();

        printf("PRESSURE = %d bar\n", pressure);
        printf("TEMP     = %d C\n", temp);

        heartbeat_update();
        run_diagnostics(pressure, temp);

        printf("----------------------------\n");
        sleep(1);
    }

    return 0;
}
