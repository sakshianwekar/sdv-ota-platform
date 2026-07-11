/*
 * version.c  —  Firmware/motor_ecu/src/version.c
 *
 * Phase 5 change: get_version() now reads current_version from
 * Virtual_ECU/MotorECU/config/version.json instead of returning
 * a hardcoded string.
 *
 * Path resolution: this binary runs from Firmware/motor_ecu/build/,
 * so the relative path goes up two levels to reach Virtual_ECU/.
 * Adjust VERSION_JSON_PATH if your run directory differs.
 */

#include "version.h"
#include "version_store.h"

#include <stdio.h>
#include <string.h>

/* Path to version.json relative to where the binary is executed.
 * The ECU binary runs from Firmware/motor_ecu/build/, so:
 *   ../../.. = repo root
 */
#define VERSION_JSON_PATH \
    "../../../Virtual_ECU/MotorECU/config/version.json"

/* Static buffer — get_version() returns a pointer to this */
static char s_version[VERSION_STR_MAX] = "unknown";
static int  s_loaded = 0;

const char* get_version(void)
{
    if (s_loaded) return s_version;

    VersionInfo info;
    int rc = vs_read(VERSION_JSON_PATH, &info);
    if (rc == VS_OK) {
        strncpy(s_version, info.current_version,
                sizeof(s_version) - 1);
        s_version[sizeof(s_version) - 1] = '\0';
    } else {
        /* Fall back to compile-time default if file missing */
        fprintf(stderr,
            "[version] WARNING: could not read %s (%s)."
            " Using default.\n",
            VERSION_JSON_PATH, vs_strerror(rc));
        strncpy(s_version, "1.0", sizeof(s_version) - 1);
    }

    s_loaded = 1;
    return s_version;
}

/*
 * get_active_slot()
 *
 * New helper — Bootloader (Phase 6) and Health Monitor will call this
 * to know which flash slot is currently active.
 */
const char* get_active_slot(void)
{
    static char s_slot[SLOT_STR_MAX] = "A";
    static int  s_slot_loaded = 0;

    if (s_slot_loaded) return s_slot;

    VersionInfo info;
    int rc = vs_read(VERSION_JSON_PATH, &info);
    if (rc == VS_OK) {
        strncpy(s_slot, info.active_slot,
                sizeof(s_slot) - 1);
        s_slot[sizeof(s_slot) - 1] = '\0';
    } else {
        strncpy(s_slot, "A", sizeof(s_slot) - 1);
    }

    s_slot_loaded = 1;
    return s_slot;
}
