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
    printf("Battery ECU Started\n");
    printf("Firmware Version : %s\n", get_version());
    printf("=================================\n\n");

    while (1) {
        int soc = get_soc();
        int voltage = get_voltage();

        printf("SOC     = %d %%\n", soc);
        printf("VOLTAGE = %d V\n", voltage);

        heartbeat_update();
        run_diagnostics(soc, voltage);

        printf("----------------------------\n");
        sleep(1);
    }

    return 0;
}
