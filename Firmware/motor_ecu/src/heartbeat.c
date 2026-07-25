#include <stdio.h>
#include <time.h>

#ifdef _WIN32
  #include <windows.h>
#else
  #include <unistd.h>
#endif

#include "heartbeat.h"

#define HEARTBEAT_FILE "Virtual_ECU/MotorECU/runtime/heartbeat.txt"
#define PID_FILE       "Virtual_ECU/MotorECU/runtime/ecu.pid"

static int counter = 0;

static void write_pid_once(void)
{
    static int done = 0;
    if (done) return;
    done = 1;

    FILE *fp = fopen(PID_FILE, "w");
    if (fp == NULL) return;

#ifdef _WIN32
    fprintf(fp, "%ld\n", (long)GetCurrentProcessId());
#else
    fprintf(fp, "%ld\n", (long)getpid());
#endif
    fclose(fp);
}

void heartbeat_update(void)
{
    write_pid_once();
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