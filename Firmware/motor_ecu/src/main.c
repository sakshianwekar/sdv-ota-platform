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
    printf("=================================\n\n");

    while(1)
    {
        int rpm = get_rpm();
        int temp = get_temperature();

        printf("RPM  = %d\n", rpm);
        printf("TEMP = %d\n", temp);

        heartbeat_update();

        run_diagnostics(rpm,temp);

        printf("----------------------------\n");

        sleep(1);
    }

    return 0;
}
