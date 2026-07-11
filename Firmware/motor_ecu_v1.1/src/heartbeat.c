#include <stdio.h>
#include <time.h>

#include "heartbeat.h"

#define HEARTBEAT_FILE "../../../Virtual_ECU/MotorECU/runtime/heartbeat.txt"

static int counter = 0;

void heartbeat_update(void)
{
    counter++;

    printf("Heartbeat = %d\n", counter);

    FILE *fp = fopen(HEARTBEAT_FILE, "w");

    if(fp == NULL)
    {
        printf("ERROR: Unable to open heartbeat file\n");
        return;
    }

    fprintf(fp, "%ld", (long)time(NULL));

    fclose(fp);
}