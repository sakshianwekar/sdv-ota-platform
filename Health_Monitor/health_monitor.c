

#include "health_monitor.h"

#define HEARTBEAT_TIMEOUT 5

int check_ecu_health(void)
{
    FILE *fp;

    long heartbeat_time;
    long current_time;

    fp = fopen(
        "../Virtual_ECU/MotorECU/runtime/heartbeat.txt",
        "r"
    );

    if(fp == NULL)
    {
        printf("Heartbeat file not found\n");
        return 0;
    }

    fscanf(fp, "%ld", &heartbeat_time);

    fclose(fp);

    current_time = time(NULL);

    long difference =
        current_time - heartbeat_time;

    printf("Heartbeat Age = %ld seconds\n",
            difference);

    if(difference <= HEARTBEAT_TIMEOUT)
    {
        printf("Health Status = GOOD\n");
        return 1;
    }

    printf("Health Status = FAILED\n");

    return 0;
}