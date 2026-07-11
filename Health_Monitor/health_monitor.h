/*
 * health_monitor.h  —  Health_Monitor/health_monitor.h
 *
 * Phase 5/6 fix: main() must never live in a header.
 * Headers declare; .c files define.
 * main() has been moved to health_monitor.c.
 */

#ifndef HEALTH_MONITOR_H
#define HEALTH_MONITOR_H

#include <stdio.h>
#include <time.h>

#define HEARTBEAT_TIMEOUT 5   /* seconds before ECU is considered unhealthy */

/*
 * check_ecu_health()
 *
 * Reads the heartbeat timestamp from the ECU runtime file.
 * Returns 1 if the ECU is healthy (heartbeat within timeout).
 * Returns 0 if the ECU is unhealthy or heartbeat file is missing.
 */
int check_ecu_health(void);

#endif /* HEALTH_MONITOR_H */
