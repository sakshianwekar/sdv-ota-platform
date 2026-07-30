#include <stdio.h>
#include <string.h>

#include "version.h"
#include "version_store.h"

#define VERSION_JSON_PATH "Virtual_ECU/BrakeECU/config/version.json"

static char s_version[VERSION_STR_MAX] = "unknown";
static int  s_loaded = 0;

const char* get_version(void)
{
    if (s_loaded) return s_version;

    VersionInfo info;
    int rc = vs_read(VERSION_JSON_PATH, &info);
    if (rc == VS_OK) {
        strncpy(s_version, info.current_version, sizeof(s_version) - 1);
        s_version[sizeof(s_version) - 1] = '\0';
    } else {
        strncpy(s_version, "1.0", sizeof(s_version) - 1);
    }

    s_loaded = 1;
    return s_version;
}

const char* get_active_slot(void)
{
    static char s_slot[SLOT_STR_MAX] = "A";
    static int  s_slot_loaded = 0;

    if (s_slot_loaded) return s_slot;

    VersionInfo info;
    int rc = vs_read(VERSION_JSON_PATH, &info);
    if (rc == VS_OK) {
        strncpy(s_slot, info.active_slot, sizeof(s_slot) - 1);
        s_slot[sizeof(s_slot) - 1] = '\0';
    }

    s_slot_loaded = 1;
    return s_slot;
}
