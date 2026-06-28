/*
 * main.c  —  Bootloader/src/main.c
 *
 * CLI interface for the bootloader.
 *
 * Usage (run from repo root):
 *   ./bootloader stage   <firmware_path>
 *   ./bootloader activate
 *   ./bootloader rollback
 *   ./bootloader status
 *
 * Examples:
 *   ./bootloader stage   Firmware/motor_ecu/build/motor_ecu
 *   ./bootloader activate
 *   ./bootloader rollback
 *   ./bootloader status
 *
 * The bootloader MUST be run from the repo root so all relative
 * paths (version.json, flash slots, PID file) resolve correctly.
 */

#include "bootloader.h"
#include <stdio.h>
#include <string.h>

static void print_usage(const char *prog)
{
    printf("Usage:\n");
    printf("  %s stage   <firmware_path>   copy firmware into inactive slot\n", prog);
    printf("  %s activate                  flip to staged slot, restart ECU\n", prog);
    printf("  %s rollback                  flip back to previous slot, restart ECU\n", prog);
    printf("  %s status                    print current version.json state\n", prog);
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    const char *cmd = argv[1];
    int rc = BL_OK;

    if (strcmp(cmd, "stage") == 0) {
        if (argc < 3) {
            fprintf(stderr, "ERROR: 'stage' requires a firmware path.\n");
            fprintf(stderr, "  Usage: %s stage <firmware_path>\n", argv[0]);
            return 1;
        }
        rc = bl_stage(argv[2]);

    } else if (strcmp(cmd, "activate") == 0) {
        rc = bl_activate();

    } else if (strcmp(cmd, "rollback") == 0) {
        rc = bl_rollback();

    } else if (strcmp(cmd, "status") == 0) {
        bl_status();
        return 0;

    } else {
        fprintf(stderr, "ERROR: unknown command '%s'\n\n", cmd);
        print_usage(argv[0]);
        return 1;
    }

    if (rc != BL_OK) {
        fprintf(stderr, "[bootloader] FAILED: %s\n", bl_strerror(rc));
        return 1;
    }

    return 0;
}
