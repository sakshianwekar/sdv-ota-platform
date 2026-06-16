#include <stdio.h>
#include "heartbeat.h"

static int counter = 0;

void heartbeat_update(void)
{
    counter++;

    printf("Heartbeat = %d\n", counter);
}