/*
 * version_store.h
 *
 * Single source of truth for reading and writing version.json.
 * Every component (Virtual_ECU, Bootloader, Health_Monitor, Installer)
 * must use these functions — nothing touches version.json directly.
 *
 * Schema (version.json):
 * {
 *   "current_version": "1.0",
 *   "active_slot":     "A",
 *   "pending_slot":    null        <- null when no update is staged
 * }
 *
 * Cross-platform: uses only ANSI C stdio + stdlib. No OS-specific calls.
 * Compiles on Linux (gcc), macOS (clang), and Windows (MSVC / MinGW).
 */

#ifndef VERSION_STORE_H
#define VERSION_STORE_H

#ifdef __cplusplus
extern "C" {
#endif

/* -------------------------------------------------------------------------
 * Types
 * ---------------------------------------------------------------------- */

#define VERSION_STR_MAX  32
#define SLOT_STR_MAX      4   /* "A", "B", or "" (empty = no pending) */

typedef struct {
    char current_version[VERSION_STR_MAX];  /* e.g. "1.0"  */
    char active_slot    [SLOT_STR_MAX];     /* "A" or "B"  */
    char pending_slot   [SLOT_STR_MAX];     /* "A", "B", or "" when null */
} VersionInfo;

/* Return codes */
#define VS_OK               0
#define VS_ERR_FILE        -1   /* Could not open / create file           */
#define VS_ERR_PARSE       -2   /* JSON is malformed or missing fields    */
#define VS_ERR_INVALID     -3   /* Caller passed bad arguments            */
#define VS_ERR_WRITE       -4   /* Write / flush to disk failed           */

/* -------------------------------------------------------------------------
 * API
 * ---------------------------------------------------------------------- */

/*
 * vs_read()
 *
 * Reads and parses version.json at [path].
 * Populates [out].
 * Returns VS_OK on success, VS_ERR_* on failure.
 *
 * Thread-safety: NOT thread-safe. Callers must serialise access externally
 * if multiple processes share the file.
 */
int vs_read(const char *path, VersionInfo *out);

/*
 * vs_write()
 *
 * Serialises [info] to version.json at [path].
 * Writes atomically via a temp file + rename so a crash mid-write never
 * leaves a half-written JSON file.
 * Returns VS_OK on success, VS_ERR_* on failure.
 */
int vs_write(const char *path, const VersionInfo *info);

/*
 * vs_print()
 *
 * Pretty-prints [info] to stdout. Useful for debugging and demo logs.
 */
void vs_print(const VersionInfo *info);

/*
 * vs_strerror()
 *
 * Returns a human-readable string for a VS_ERR_* code.
 */
const char *vs_strerror(int err);

#ifdef __cplusplus
}
#endif

#endif /* VERSION_STORE_H */
