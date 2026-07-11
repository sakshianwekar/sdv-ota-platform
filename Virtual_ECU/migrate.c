/*
 * migrate.c
 *
 * One-time migration: reads Virtual_ECU/MotorECU/config/version.db
 * and writes Virtual_ECU/MotorECU/config/version.json
 *
 * Actual version.db format (key=value):
 *   CurrentVersion=1.0
 *   ActiveSlot=A
 *
 * Usage (run from repo root):
 *   gcc Virtual_ECU/migrate.c Common/version_store/version_store.c \
 *       -ICommon/version_store -o migrate
 *   ./migrate Virtual_ECU/MotorECU/config/version.db \
 *              Virtual_ECU/MotorECU/config/version.json
 *
 * After confirming version.json looks correct:
 *   git rm Virtual_ECU/MotorECU/config/version.db
 */

#include "version_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -------------------------------------------------------------------------
 * Parse the key=value format used in the existing version.db
 * ---------------------------------------------------------------------- */
static int parse_old_db(const char *path, VersionInfo *out)
{
    FILE *fp = fopen(path, "r");
    if (!fp) {
        fprintf(stderr, "[migrate] ERROR: cannot open %s\n", path);
        return -1;
    }

    out->current_version[0] = '\0';
    out->active_slot[0]     = '\0';
    out->pending_slot[0]    = '\0';

    char line[128];
    while (fgets(line, sizeof(line), fp)) {
        /* strip trailing newline / CR */
        line[strcspn(line, "\r\n")] = '\0';

        /* split on '=' */
        char *eq = strchr(line, '=');
        if (!eq) continue;
        *eq = '\0';
        const char *key   = line;
        const char *value = eq + 1;

        if (strcmp(key, "CurrentVersion") == 0) {
            strncpy(out->current_version, value,
                    sizeof(out->current_version) - 1);
        } else if (strcmp(key, "ActiveSlot") == 0) {
            strncpy(out->active_slot, value,
                    sizeof(out->active_slot) - 1);
        }
        /* Any other keys are ignored — future-proof */
    }
    fclose(fp);

    /* pending_slot is always null after migration */
    out->pending_slot[0] = '\0';

    return 0;
}

/* -------------------------------------------------------------------------
 * main
 * ---------------------------------------------------------------------- */
int main(int argc, char *argv[])
{
    if (argc != 3) {
        fprintf(stderr,
            "Usage: %s <version.db path> <version.json path>\n"
            "Example:\n"
            "  %s Virtual_ECU/MotorECU/config/version.db"
            " Virtual_ECU/MotorECU/config/version.json\n",
            argv[0], argv[0]);
        return 1;
    }

    const char *db_path   = argv[1];
    const char *json_path = argv[2];

    VersionInfo info;
    memset(&info, 0, sizeof(info));

    printf("[migrate] Reading: %s\n", db_path);
    if (parse_old_db(db_path, &info) != 0) return 1;

    /* Validate before writing */
    if (strlen(info.current_version) == 0) {
        fprintf(stderr,
            "[migrate] ERROR: CurrentVersion not found in %s\n", db_path);
        return 1;
    }
    if (strcmp(info.active_slot, "A") != 0 &&
        strcmp(info.active_slot, "B") != 0) {
        fprintf(stderr,
            "[migrate] ERROR: ActiveSlot='%s' — must be A or B\n",
            info.active_slot);
        return 1;
    }

    printf("[migrate] Parsed  → version=%s  slot=%s\n",
           info.current_version, info.active_slot);

    printf("[migrate] Writing: %s\n", json_path);
    int rc = vs_write(json_path, &info);
    if (rc != VS_OK) {
        fprintf(stderr, "[migrate] ERROR: %s\n", vs_strerror(rc));
        return 1;
    }

    /* Read back to confirm */
    VersionInfo check;
    memset(&check, 0, sizeof(check));
    vs_read(json_path, &check);
    printf("[migrate] Verified contents:\n");
    vs_print(&check);

    printf("[migrate] SUCCESS. Run: git rm %s\n", db_path);
    return 0;
}
