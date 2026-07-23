/*
 * health_monitor.c — Health_Monitor/health_monitor.c
 *
 * Phase 11: Health-checked activation + automatic rollback wiring.
 *
 * How it works:
 *   1. After bootloader activate, call hm_start_grace_period()
 *   2. For the next GRACE_PERIOD_SECONDS, every failed health check
 *      increments a consecutive failure counter
 *   3. If the counter hits FAILURE_THRESHOLD, bootloader rollback
 *      is called automatically — no human input
 *   4. A single good heartbeat resets the failure counter
 *   5. After the grace period expires with no rollback, the ECU
 *      is considered stable and monitoring continues normally
 *
 * Why consecutive failures, not single failure:
 *   One missed heartbeat could be a slow tick or filesystem delay.
 *   FAILURE_THRESHOLD=3 means 3 seconds of sustained failure
 *   before rollback — avoids false positives.
 */

#include "health_monitor.h"

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

#ifdef _WIN32
  #include <windows.h>
  #define SLEEP_1S() Sleep(1000)
#else
  #include <unistd.h>
  #define SLEEP_1S() sleep(1)
#endif

/* -------------------------------------------------------------------------
 * Paths
 * ---------------------------------------------------------------------- */
#define HEARTBEAT_FILE \
    "Virtual_ECU/MotorECU/runtime/heartbeat.txt"

#define BOOTLOADER_CMD \
    "./Bootloader/build/bootloader"

#define OTA_LOG_FILE \
    "Virtual_ECU/MotorECU/logs/ota.log"

/* -------------------------------------------------------------------------
 * Internal state
 * ---------------------------------------------------------------------- */
static int   g_in_grace_period    = 0;
static time_t g_grace_start       = 0;
static int   g_consecutive_fails  = 0;

/* -------------------------------------------------------------------------
 * Logging helper — writes to both stdout and ota.log
 * ---------------------------------------------------------------------- */
static void ota_log(const char *level, const char *msg)
{
    time_t now = time(NULL);
    char timebuf[32];
    struct tm *t = localtime(&now);
    strftime(timebuf, sizeof(timebuf), "%Y-%m-%d %H:%M:%S", t);

    /* stdout */
    printf("[%s] %s  %s\n", timebuf, level, msg);
    fflush(stdout);

    /* ota.log */
    FILE *fp = fopen(OTA_LOG_FILE, "a");
    if (fp) {
        fprintf(fp, "[%s] %s  %s\n", timebuf, level, msg);
        fclose(fp);
    }
}

/* -------------------------------------------------------------------------
 * check_ecu_health() — original logic, unchanged
 * ---------------------------------------------------------------------- */
int check_ecu_health(void)
{
    FILE *fp = fopen(HEARTBEAT_FILE, "r");
    if (fp == NULL) {
        printf("Heartbeat file not found\n");
        return 0;
    }

    long heartbeat_time;
    fscanf(fp, "%ld", &heartbeat_time);
    fclose(fp);

    long current_time = (long)time(NULL);
    long difference   = current_time - heartbeat_time;

    printf("Heartbeat Age = %ld seconds\n", difference);

    if (difference <= HEARTBEAT_TIMEOUT) {
        printf("Health Status = GOOD\n");
        return 1;
    }

    printf("Health Status = FAILED\n");
    return 0;
}

/* -------------------------------------------------------------------------
 * Grace period control
 * ---------------------------------------------------------------------- */
void hm_start_grace_period(void)
{
    g_in_grace_period   = 1;
    g_grace_start       = time(NULL);
    g_consecutive_fails = 0;
    ota_log("INFO", "Grace period started — watching ECU for stability");
}

void hm_clear_grace_period(void)
{
    g_in_grace_period   = 0;
    g_consecutive_fails = 0;
    ota_log("INFO", "Grace period cleared");
}

/* -------------------------------------------------------------------------
 * check_ecu_health_with_rollback() — Phase 11 core function
 * ---------------------------------------------------------------------- */
int check_ecu_health_with_rollback(void)
{
    int healthy = check_ecu_health();

    /* ── Outside grace period: just log, no rollback ── */
    if (!g_in_grace_period) {
        if (!healthy) {
            ota_log("WARNING", "ECU unhealthy outside grace period — monitoring");
        }
        return healthy;
    }

    /* ── Inside grace period ── */
    long elapsed = (long)(time(NULL) - g_grace_start);

    /* Grace period expired with no rollback — ECU is stable */
    if (elapsed >= GRACE_PERIOD_SECONDS) {
        ota_log("INFO",
            "Grace period expired — ECU stable, activation confirmed");
        hm_clear_grace_period();
        return healthy;
    }

    char msg[128];

    if (healthy) {
        /* Good heartbeat — reset failure counter */
        g_consecutive_fails = 0;
        snprintf(msg, sizeof(msg),
            "ECU healthy during grace period (%lds/%ds)",
            elapsed, GRACE_PERIOD_SECONDS);
        ota_log("INFO", msg);
        return 1;
    }

    /* Failed heartbeat — increment counter */
    g_consecutive_fails++;
    snprintf(msg, sizeof(msg),
        "ECU FAILED during grace period — consecutive failures: %d/%d  (%lds/%ds)",
        g_consecutive_fails, FAILURE_THRESHOLD,
        elapsed, GRACE_PERIOD_SECONDS);
    ota_log("WARNING", msg);

    /* Threshold hit — trigger automatic rollback */
    if (g_consecutive_fails >= FAILURE_THRESHOLD) {
        ota_log("ERROR",
            "FAILURE THRESHOLD REACHED — triggering automatic rollback");

        char cmd[256];
        snprintf(cmd, sizeof(cmd), "%s rollback", BOOTLOADER_CMD);

        ota_log("INFO", "Calling: bootloader rollback");
        int rc = system(cmd);

        if (rc == 0) {
            ota_log("INFO",
                "Rollback complete — ECU restored to previous slot");
        } else {
            ota_log("ERROR", "Rollback command failed — manual intervention required");
        }

        hm_clear_grace_period();
        return -1;   /* -1 signals rollback was triggered */
    }

    return 0;
}

/* -------------------------------------------------------------------------
 * main()
 * ---------------------------------------------------------------------- */
int main(int argc, char *argv[])
{
    printf("[health_monitor] Starting\n");
    printf("[health_monitor] Heartbeat timeout : %ds\n", HEARTBEAT_TIMEOUT);
    printf("[health_monitor] Grace period      : %ds\n", GRACE_PERIOD_SECONDS);
    printf("[health_monitor] Failure threshold : %d consecutive failures\n\n",
           FAILURE_THRESHOLD);

    /*
     * If called with --grace argument, start grace period immediately.
     * This is how the Installer (Phase 10) will call it after activation:
     *   ./Health_Monitor/build/health_monitor --grace
     */
    if (argc > 1 && strcmp(argv[1], "--grace") == 0) {
        ota_log("INFO", "Started in grace period mode (post-activation)");
        hm_start_grace_period();
    }

    while (1) {
        int result = check_ecu_health_with_rollback();

        if (result == -1) {
            ota_log("INFO",
                "Rollback triggered — health monitor returning to normal mode");
            /* Continue monitoring after rollback */
        }

        SLEEP_1S();
    }

    return 0;
}
