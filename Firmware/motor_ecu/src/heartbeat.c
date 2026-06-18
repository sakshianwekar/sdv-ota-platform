#include <stdio.h>
#include "heartbeat.h"

static int counter = 0;

void heartbeat_update(void)
{
    counter++;

    printf("Heartbeat = %d\n", counter);
    FILE *fp;

fp = fopen("Virtual_ECU/MotorECU/runtime/heartbeat.txt","w");

fprintf(fp,"%ld",time(NULL));

fclose(fp);
}