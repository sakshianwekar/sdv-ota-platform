/*
 * bootloader.h  —  Bootloader/include/bootloader.h
 *
 * The Bootloader is the ONLY component allowed to write to flash slots.
 * Nothing else — not the Installer, not the OTA Client — touches
 * Virtual_ECU/MotorECU/flash/ directly. This mirrors real automotive
 * bootloaders that run in protected memory.
 *
 * Three operations:
 *   stage    — write new firmware into the INACTIVE slot
 *   activate — flip active_slot to pending_slot, restart ECU
 *   rollback — flip back to previous slot, restart ECU
 *
 * All state is persisted in version.json via the version_store API.
 */

#ifndef BOOTLOADER_H
#define BOOTLOADER_H

#ifdef __cplusplus
extern "C" {
#endif

#include "version_store.h"

/* -------------------------------------------------------------------------
 * Paths  (relative to repo root — where the bootloader binary is run from)
 * ---------------------------------------------------------------------- */
#define VERSION_JSON_PATH  "Virtual_ECU/MotorECU/config/version.json"
#define SLOT_A_DIR         "Virtual_ECU/MotorECU/flash/slotA"
#define SLOT_B_DIR         "Virtual_ECU/MotorECU/flash/slotB"
#define FIRMWARE_FILENAME  "motor_ecu"        /* copied into slot dir     */

/* ECU process name — used to kill + restart the running ECU */
#define ECU_BINARY_RELPATH_A  "Virtual_ECU/MotorECU/flash/slotA/motor_ecu"
#define ECU_BINARY_RELPATH_B  "Virtual_ECU/MotorECU/flash/slotB/motor_ecu"
#define ECU_PIDFILE           "Virtual_ECU/MotorECU/runtime/ecu.pid"

/* -------------------------------------------------------------------------
 * Return codes
 * ---------------------------------------------------------------------- */
#define BL_OK               0
#define BL_ERR_ARGS        -1   /* Bad arguments passed to function        */
#define BL_ERR_VERSION     -2   /* Could not read/write version.json        */
#define BL_ERR_COPY        -3   /* File copy into slot failed               */
#define BL_ERR_NO_PENDING  -4   /* activate called with no pending_slot     */
#define BL_ERR_RESTART     -5   /* ECU process restart failed               */
#define BL_ERR_SAME_SLOT   -6   /* Tried to stage into the active slot      */

/* -------------------------------------------------------------------------
 * API
 * ---------------------------------------------------------------------- */

/*
 * bl_stage()
 *
 * Copies [firmware_path] into the INACTIVE flash slot.
 * Sets pending_slot in version.json.
 * Does NOT restart the ECU — that happens in bl_activate().
 *
 * Returns BL_OK on success, BL_ERR_* on failure.
 */
int bl_stage(const char *firmware_path);

/*
 * bl_activate()
 *
 * Flips active_slot → pending_slot in version.json.
 * Clears pending_slot to null.
 * Restarts the ECU process from the new active slot.
 *
 * Returns BL_OK on success, BL_ERR_* on failure.
 */
int bl_activate(void);

/*
 * bl_rollback()
 *
 * Flips active_slot back to whichever slot it wasn't.
 * Clears pending_slot to null.
 * Restarts the ECU process from the restored slot.
 * Called automatically by Health Monitor on sustained failure (Phase 11).
 *
 * Returns BL_OK on success, BL_ERR_* on failure.
 */
int bl_rollback(void);

/*
 * bl_status()
 *
 * Prints current version.json state to stdout.
 * Useful for debugging and demo scripts.
 */
void bl_status(void);

/*
 * bl_strerror()
 * Human-readable string for a BL_ERR_* code.
 */
const char *bl_strerror(int err);

#ifdef __cplusplus
}
#endif

#endif /* BOOTLOADER_H */
