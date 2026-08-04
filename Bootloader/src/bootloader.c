/*
 * bootloader.c  —  Bootloader/src/bootloader.c
 *
 * Implements bl_stage(), bl_activate(), bl_rollback(), bl_status().
 *
 * Cross-platform notes:
 *   - File copy uses fread/fwrite (ANSI C, works everywhere)
 *   - Process restart uses system() with platform-specific commands
 *   - PID file used to track and kill the running ECU process
 */

#include "bootloader.h"
#include "version_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#ifndef _WIN32
#include <sys/stat.h>
#endif

/* -------------------------------------------------------------------------
 * Per-ECU paths (configured via bl_configure, default MotorECU)
 * ---------------------------------------------------------------------- */
typedef struct {
    char ecu_name[64];
    char version_json[512];
    char slot_a_dir[512];
    char slot_b_dir[512];
    char firmware_name[64];
    char ecu_binary_a[512];
    char ecu_binary_b[512];
    char pidfile[512];
    char pending_version[512];
    char previous_version[512];
} BlPaths;

static BlPaths g_paths;
static int g_paths_ready = 0;

static const char *firmware_name_for_ecu(const char *ecu_name)
{
    if (strcmp(ecu_name, "BrakeECU") == 0) return "brake_ecu";
    if (strcmp(ecu_name, "BatteryECU") == 0) return "battery_ecu";
    return "motor_ecu";
}

void bl_configure(const char *ecu_name)
{
    const char *name = (ecu_name && ecu_name[0]) ? ecu_name : BL_DEFAULT_ECU;
    const char *fw = firmware_name_for_ecu(name);

    strncpy(g_paths.ecu_name, name, sizeof(g_paths.ecu_name) - 1);
    g_paths.ecu_name[sizeof(g_paths.ecu_name) - 1] = '\0';

    snprintf(g_paths.version_json, sizeof(g_paths.version_json),
             "Virtual_ECU/%s/config/version.json", name);
    snprintf(g_paths.slot_a_dir, sizeof(g_paths.slot_a_dir),
             "Virtual_ECU/%s/flash/slotA", name);
    snprintf(g_paths.slot_b_dir, sizeof(g_paths.slot_b_dir),
             "Virtual_ECU/%s/flash/slotB", name);

    strncpy(g_paths.firmware_name, fw, sizeof(g_paths.firmware_name) - 1);
    g_paths.firmware_name[sizeof(g_paths.firmware_name) - 1] = '\0';
#ifdef _WIN32
    {
        size_t fw_len = strlen(g_paths.firmware_name);
        if (fw_len + 4 < sizeof(g_paths.firmware_name)) {
            strcat(g_paths.firmware_name, ".exe");
        }
    }
#endif
    snprintf(g_paths.ecu_binary_a, sizeof(g_paths.ecu_binary_a),
             "Virtual_ECU/%s/flash/slotA/%s", name, g_paths.firmware_name);
    snprintf(g_paths.ecu_binary_b, sizeof(g_paths.ecu_binary_b),
             "Virtual_ECU/%s/flash/slotB/%s", name, g_paths.firmware_name);
    snprintf(g_paths.pidfile, sizeof(g_paths.pidfile),
             "Virtual_ECU/%s/runtime/ecu.pid", name);
    snprintf(g_paths.pending_version, sizeof(g_paths.pending_version),
             "Virtual_ECU/%s/config/pending_version.txt", name);
    snprintf(g_paths.previous_version, sizeof(g_paths.previous_version),
             "Virtual_ECU/%s/config/previous_version.txt", name);

    g_paths_ready = 1;
}

static void ensure_paths(void)
{
    if (!g_paths_ready) {
        bl_configure(BL_DEFAULT_ECU);
    }
}

#define VERSION_JSON_PATH   g_paths.version_json
#define SLOT_A_DIR          g_paths.slot_a_dir
#define SLOT_B_DIR          g_paths.slot_b_dir
#define FIRMWARE_FILENAME   g_paths.firmware_name
#define ECU_BINARY_RELPATH_A g_paths.ecu_binary_a
#define ECU_BINARY_RELPATH_B g_paths.ecu_binary_b
#define ECU_PIDFILE         g_paths.pidfile
#define PENDING_VERSION_FILE g_paths.pending_version
#define PREVIOUS_VERSION_FILE g_paths.previous_version

/* -------------------------------------------------------------------------
 * Platform helpers
 * ---------------------------------------------------------------------- */
#ifdef _WIN32
  #include <windows.h>
  #include <direct.h>
  #define KILL_CMD "taskkill /F /PID %ld"
  #define START_CMD "start /B \"\" \"%s\" > NUL 2>&1"
  #define SLEEP_1S() Sleep(1000)
#else
  #include <unistd.h>
  #include <sys/stat.h>
  #define KILL_CMD "kill %ld 2>/dev/null"
  #define START_CMD "%s > /dev/null 2>&1 &"
  #define SLEEP_1S() sleep(1)
#endif

/* -------------------------------------------------------------------------
 * Internal helpers
 * ---------------------------------------------------------------------- */

/*
 * copy_file()
 * Copies [src] to [dst] using raw fread/fwrite.
 * Returns 0 on success, -1 on failure.
 */
static int copy_file(const char *src, const char *dst)
{
    FILE *in = fopen(src, "rb");
    if (!in) {
        fprintf(stderr, "[bootloader] ERROR: cannot open source: %s\n", src);
        return -1;
    }

    FILE *out = fopen(dst, "wb");
    if (!out) {
        fprintf(stderr, "[bootloader] ERROR: cannot open dest: %s\n", dst);
        fclose(in);
        return -1;
    }

    char buf[4096];
    size_t n;
    int ok = 1;
    while ((n = fread(buf, 1, sizeof(buf), in)) > 0) {
        if (fwrite(buf, 1, n, out) != n) {
            fprintf(stderr, "[bootloader] ERROR: write failed for %s\n", dst);
            ok = 0;
            break;
        }
    }

    fclose(in);
    fclose(out);
    if (!ok) {
        return -1;
    }

#ifndef _WIN32
    if (chmod(dst, 0755) != 0) {
        fprintf(stderr, "[bootloader] WARNING: chmod failed for %s: %s\n",
                dst, strerror(errno));
    }
#endif

    return 0;
}

/*
 * get_inactive_slot()
 * Returns "B" if active is "A", "A" if active is "B".
 */
static const char *get_inactive_slot(const char *active)
{
    return (strcmp(active, "A") == 0) ? "B" : "A";
}

/*
 * slot_firmware_path()
 * Builds the full path to the firmware binary inside a slot dir.
 * e.g. "Virtual_ECU/MotorECU/flash/slotA/motor_ecu"
 */
static void slot_firmware_path(const char *slot, char *out, size_t out_len)
{
    const char *dir = (strcmp(slot, "A") == 0) ? SLOT_A_DIR : SLOT_B_DIR;
    snprintf(out, out_len, "%s/%s", dir, FIRMWARE_FILENAME);
}

static int ensure_dir_exists(const char *path)
{
#ifdef _WIN32
    char tmp[512];
    strncpy(tmp, path, sizeof(tmp) - 1);
    tmp[sizeof(tmp) - 1] = '\0';
    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/' || *p == '\\') {
            *p = '\0';
            _mkdir(tmp);
            *p = '/';
        }
    }
    return _mkdir(tmp) == 0 || GetFileAttributesA(tmp) != INVALID_FILE_ATTRIBUTES;
#else
    char tmp[512];
    strncpy(tmp, path, sizeof(tmp) - 1);
    tmp[sizeof(tmp) - 1] = '\0';
    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            mkdir(tmp, 0755);
            *p = '/';
        }
    }
    return mkdir(tmp, 0755) == 0 || access(tmp, F_OK) == 0;
#endif
}

/*
 * ecu_binary_path()
 * Returns the path to the ECU binary for the given slot.
 */
static const char *ecu_binary_path(const char *slot)
{
    return (strcmp(slot, "A") == 0)
        ? ECU_BINARY_RELPATH_A
        : ECU_BINARY_RELPATH_B;
}

/*
 * read_pid()
 * Reads the ECU PID from ECU_PIDFILE.
 * Returns PID on success, -1 if not found.
 */
static long read_pid(void)
{
    FILE *fp = fopen(ECU_PIDFILE, "r");
    if (!fp) return -1;
    long pid = -1;
    fscanf(fp, "%ld", &pid);
    fclose(fp);
    return pid;
}

/*
 * kill_ecu()
 * Sends kill signal to the running ECU process using its PID file.
 */
static void kill_ecu(void)
{
    long pid = read_pid();
    if (pid <= 0) {
        printf("[bootloader] No running ECU PID found — skipping kill\n");
        return;
    }
    char cmd[128];
    snprintf(cmd, sizeof(cmd), KILL_CMD, pid);
    printf("[bootloader] Stopping ECU (PID %ld)\n", pid);
    system(cmd);
    SLEEP_1S();   /* give it a moment to die */
}

/*
 * apply_pending_version()
 * If pending_version.txt exists, save current_version to previous_version.txt
 * and update current_version before activation.
 */
static void apply_pending_version(VersionInfo *info)
{
    FILE *pf = fopen(PENDING_VERSION_FILE, "r");
    if (!pf) return;

    char new_version[VERSION_STR_MAX];
    if (fscanf(pf, "%31s", new_version) != 1) {
        fclose(pf);
        remove(PENDING_VERSION_FILE);
        return;
    }
    fclose(pf);
    remove(PENDING_VERSION_FILE);

    char old_version[VERSION_STR_MAX];
    strncpy(old_version, info->current_version, sizeof(old_version) - 1);
    old_version[sizeof(old_version) - 1] = '\0';

    FILE *prev = fopen(PREVIOUS_VERSION_FILE, "w");
    if (prev) {
        fprintf(prev, "%s\n", old_version);
        fclose(prev);
    }

    strncpy(info->current_version, new_version,
            sizeof(info->current_version) - 1);
    info->current_version[sizeof(info->current_version) - 1] = '\0';
    printf("  version updated: %s → %s\n", old_version, new_version);
}

/*
 * restore_previous_version()
 * On rollback, restore current_version from previous_version.txt if present.
 */
static void restore_previous_version(VersionInfo *info)
{
    FILE *prev = fopen(PREVIOUS_VERSION_FILE, "r");
    if (!prev) return;

    char prev_version[VERSION_STR_MAX];
    if (fscanf(prev, "%31s", prev_version) == 1) {
        printf("  version restored: %s → %s\n",
               info->current_version, prev_version);
        strncpy(info->current_version, prev_version,
                sizeof(info->current_version) - 1);
    }
    fclose(prev);
    remove(PREVIOUS_VERSION_FILE);
}

/*
 * start_ecu()
 * Launches the ECU binary from the given slot in the background.
 * The ECU is responsible for writing its own PID to ECU_PIDFILE on startup.
 */
static int start_ecu(const char *slot)
{
    const char *binary = ecu_binary_path(slot);
    char cmd[256];
    snprintf(cmd, sizeof(cmd), START_CMD, binary);
    printf("[bootloader] Starting ECU from slot%s: %s\n", slot, binary);
    int rc = system(cmd);
    SLEEP_1S();   /* give it a moment to start */
    return (rc == 0) ? 0 : -1;
}

/* -------------------------------------------------------------------------
 * Public API
 * ---------------------------------------------------------------------- */

int bl_stage(const char *firmware_path)
{
    ensure_paths();

    if (!firmware_path || strlen(firmware_path) == 0) {
        fprintf(stderr, "[bootloader] stage: firmware_path is required\n");
        return BL_ERR_ARGS;
    }

    /* Read current state */
    VersionInfo info;
    int rc = vs_read(VERSION_JSON_PATH, &info);
    if (rc != VS_OK) {
        fprintf(stderr, "[bootloader] stage: cannot read %s — %s\n",
                VERSION_JSON_PATH, vs_strerror(rc));
        return BL_ERR_VERSION;
    }

    /* Determine the inactive slot */
    const char *inactive = get_inactive_slot(info.active_slot);

    printf("[bootloader] STAGE\n");
    printf("  firmware  : %s\n", firmware_path);
    printf("  active    : slot%s\n", info.active_slot);
    printf("  staging → : slot%s\n", inactive);

    /* Build destination path */
    char dst[512];
    slot_firmware_path(inactive, dst, sizeof(dst));

    const char *inactive_dir = (strcmp(inactive, "A") == 0) ? SLOT_A_DIR : SLOT_B_DIR;
    ensure_dir_exists(inactive_dir);

    /* Copy firmware into inactive slot */
    if (copy_file(firmware_path, dst) != 0) {
        return BL_ERR_COPY;
    }
    printf("  copied to : %s\n", dst);

    /* Update pending_slot in version.json */
    strncpy(info.pending_slot, inactive, sizeof(info.pending_slot) - 1);
    rc = vs_write(VERSION_JSON_PATH, &info);
    if (rc != VS_OK) {
        fprintf(stderr, "[bootloader] stage: cannot write version.json — %s\n",
                vs_strerror(rc));
        return BL_ERR_VERSION;
    }

    printf("  pending_slot set to: %s\n", info.pending_slot);
    printf("[bootloader] STAGE complete\n\n");
    return BL_OK;
}

int bl_activate(void)
{
    ensure_paths();

    /* Read current state */
    VersionInfo info;
    int rc = vs_read(VERSION_JSON_PATH, &info);
    if (rc != VS_OK) {
        fprintf(stderr, "[bootloader] activate: cannot read version.json — %s\n",
                vs_strerror(rc));
        return BL_ERR_VERSION;
    }

    /* Must have a pending slot */
    if (strlen(info.pending_slot) == 0) {
        fprintf(stderr,
            "[bootloader] activate: no pending_slot set. Run stage first.\n");
        return BL_ERR_NO_PENDING;
    }

    printf("[bootloader] ACTIVATE\n");
    printf("  current active : slot%s  (version %s)\n",
           info.active_slot, info.current_version);
    printf("  activating     : slot%s\n", info.pending_slot);

    /* Apply pending version before flipping slots */
    apply_pending_version(&info);

    /* Flip active_slot → pending_slot, clear pending */
    strncpy(info.active_slot, info.pending_slot,
            sizeof(info.active_slot) - 1);
    info.pending_slot[0] = '\0';   /* null */

    /* Write updated state BEFORE restarting ECU */
    rc = vs_write(VERSION_JSON_PATH, &info);
    if (rc != VS_OK) {
        fprintf(stderr, "[bootloader] activate: cannot write version.json — %s\n",
                vs_strerror(rc));
        return BL_ERR_VERSION;
    }

    printf("  version.json updated: active_slot=%s  pending_slot=null\n",
           info.active_slot);

    /* Restart ECU on the new slot */
    kill_ecu();
    if (start_ecu(info.active_slot) != 0) {
        fprintf(stderr, "[bootloader] activate: ECU restart failed\n");
        return BL_ERR_RESTART;
    }

    printf("[bootloader] ACTIVATE complete — ECU running on slot%s\n\n",
           info.active_slot);
    return BL_OK;
}

int bl_rollback(void)
{
    ensure_paths();

    /* Read current state */
    VersionInfo info;
    int rc = vs_read(VERSION_JSON_PATH, &info);
    if (rc != VS_OK) {
        fprintf(stderr, "[bootloader] rollback: cannot read version.json — %s\n",
                vs_strerror(rc));
        return BL_ERR_VERSION;
    }

    const char *fallback = get_inactive_slot(info.active_slot);

    printf("[bootloader] ROLLBACK\n");
    printf("  current (bad) slot : slot%s\n", info.active_slot);
    printf("  rolling back to    : slot%s\n", fallback);

    /* Restore version, flip active_slot to the other slot, clear pending */
    restore_previous_version(&info);
    strncpy(info.active_slot, fallback, sizeof(info.active_slot) - 1);
    info.pending_slot[0] = '\0';

    rc = vs_write(VERSION_JSON_PATH, &info);
    if (rc != VS_OK) {
        fprintf(stderr, "[bootloader] rollback: cannot write version.json — %s\n",
                vs_strerror(rc));
        return BL_ERR_VERSION;
    }

    printf("  version.json updated: active_slot=%s  pending_slot=null\n",
           info.active_slot);

    /* Restart ECU on the restored slot */
    kill_ecu();
    if (start_ecu(info.active_slot) != 0) {
        fprintf(stderr, "[bootloader] rollback: ECU restart failed\n");
        return BL_ERR_RESTART;
    }

    printf("[bootloader] ROLLBACK complete — ECU restored to slot%s\n\n",
           info.active_slot);
    return BL_OK;
}

void bl_status(void)
{
    ensure_paths();

    VersionInfo info;
    int rc = vs_read(VERSION_JSON_PATH, &info);
    if (rc != VS_OK) {
        fprintf(stderr, "[bootloader] status: cannot read version.json — %s\n",
                vs_strerror(rc));
        return;
    }

    printf("[bootloader] STATUS (%s)\n", g_paths.ecu_name);
    printf("  version      : %s\n", info.current_version);
    printf("  active_slot  : %s\n", info.active_slot);
    printf("  pending_slot : %s\n",
           strlen(info.pending_slot) ? info.pending_slot : "null");
}

const char *bl_strerror(int err)
{
    switch (err) {
        case BL_OK:             return "OK";
        case BL_ERR_ARGS:       return "Bad arguments";
        case BL_ERR_VERSION:    return "version.json read/write failed";
        case BL_ERR_COPY:       return "Firmware copy into slot failed";
        case BL_ERR_NO_PENDING: return "No pending_slot set — run stage first";
        case BL_ERR_RESTART:    return "ECU process restart failed";
        case BL_ERR_SAME_SLOT:  return "Cannot stage into the active slot";
        default:                return "Unknown error";
    }
}
