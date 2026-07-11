/*
 * version.h  —  Firmware/motor_ecu/include/version.h
 *
 * Phase 5 change: added get_active_slot() declaration.
 * get_version() signature is unchanged — nothing else breaks.
 */

#ifndef VERSION_H
#define VERSION_H

#include "version_store.h"   /* for VERSION_STR_MAX, SLOT_STR_MAX */

/*
 * get_version()
 * Returns the current firmware version string, e.g. "1.0".
 * Reads from version.json on first call, cached after that.
 */
const char* get_version(void);

/*
 * get_active_slot()
 * Returns the currently active flash slot: "A" or "B".
 * Used by Bootloader (Phase 6) and Health Monitor (Phase 11).
 */
const char* get_active_slot(void);

#endif /* VERSION_H */
