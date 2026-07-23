/*
 * health_monitor.h — Health_Monitor/health_monitor.h
 *
 * Phase 11 changes:
 *   - Added GRACE_PERIOD_SECONDS — how long to watch ECU after activation
 *   - Added FAILURE_THRESHOLD    — consecutive failures before rollback
 *   - Added activation state functions: hm_start_grace_period(), hm_clear_grace_period()
 *   - Added check_ecu_health_with_rollback() — the main Phase 11 function
 */

#ifndef HEALTH_MONITOR_H
#define HEALTH_MONITOR_H

#include <stdio.h>
#include <time.h>

/* -------------------------------------------------------------------------
 * Tunable constants
 * ---------------------------------------------------------------------- */

/* Seconds before an ECU heartbeat is considered stale */
#define HEARTBEAT_TIMEOUT    5

/* After activation, watch the ECU for this many seconds before relaxing */
#define GRACE_PERIOD_SECONDS 30

/* How many consecutive failed checks before triggering rollback */
#define FAILURE_THRESHOLD    3

/* -------------------------------------------------------------------------
 * API
 * ---------------------------------------------------------------------- */

/*
 * check_ecu_health()
 * Original function — unchanged.
 * Returns 1 if healthy, 0 if not.
 */
int check_ecu_health(void);

/*
 * hm_start_grace_period()
 * Call this immediately after bootloader activate.
 * Puts the monitor into "watching" mode for GRACE_PERIOD_SECONDS.
 * During this window, FAILURE_THRESHOLD consecutive failures trigger rollback.
 */
void hm_start_grace_period(void);

/*
 * hm_clear_grace_period()
 * Call this to manually exit grace period (e.g. after successful activation).
 */
void hm_clear_grace_period(void);

/*
 * check_ecu_health_with_rollback()
 * Phase 11 main function — replaces the simple loop in main().
 * During grace period: counts consecutive failures, calls rollback if threshold hit.
 * Outside grace period: logs health status only, no rollback.
 * Returns 1 if healthy, 0 if unhealthy, -1 if rollback was triggered.
 */
int check_ecu_health_with_rollback(void);

#endif /* HEALTH_MONITOR_H */
