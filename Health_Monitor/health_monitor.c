/*
 * health_monitor.c  —  Health_Monitor/health_monitor.c
 *
 * Phase 5 change: main() moved here from health_monitor.h (header fix).
 * The check_ecu_health() logic is UNCHANGED — it never read version.db,
 * it only reads the heartbeat file, so no other edits needed for Phase 5.
 *
 * Phase 11 will extend this file to call bootloader rollback on failure.
 */

#include "health_monitor.h"
#include <stdio.h>
#include <time.h>

#define HEARTBEAT_FILE \
    "../../Virtual_ECU/MotorECU/runtime/heartbeat.txt"

/* -------------------------------------------------------------------------
 * check_ecu_health() — unchanged logic from original
 * ---------------------------------------------------------------------- */
int check_ecu_health(void)
{
    FILE *fp;
    long heartbeat_time;
    long current_time;

    fp = fopen(HEARTBEAT_FILE, "r");
    if (fp == NULL) {
        printf("Heartbeat file not found\n");
        return 0;
    }

    fscanf(fp, "%ld", &heartbeat_time);
    fclose(fp);

    current_time = time(NULL);
    long difference = current_time - heartbeat_time;

    printf("Heartbeat Age = %ld seconds\n", difference);

    if (difference <= HEARTBEAT_TIMEOUT) {
        printf("Health Status = GOOD\n");
        return 1;
    }

    printf("Health Status = FAILED\n");
    return 0;
}

/* -------------------------------------------------------------------------
 * main() — moved here from health_monitor.h
 *
 * Phase 11 will change this loop to call bootloader rollback when
 * check_ecu_health() returns 0 during the post-activation grace period.
 * ---------------------------------------------------------------------- */
int main(void)
{
    printf("[health_monitor] Starting. Timeout = %ds\n", HEARTBEAT_TIMEOUT);

    while (1) {
        check_ecu_health();

        /* Sleep 1 second between checks.
         * Using a portable approach: on POSIX this is sleep(1),
         * on Windows it's Sleep(1000). */
#ifdef _WIN32
        #include <windows.h>
        Sleep(1000);
#else
        #include <unistd.h>
        sleep(1);
#endif
    }

    return 0;
}
