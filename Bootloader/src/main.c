/*
 * main.c  —  Bootloader/src/main.c
 *
 * CLI interface for the bootloader.
 *
 * Usage (run from repo root):
 *   ./bootloader [--ecu MotorECU] stage   <firmware_path>
 *   ./bootloader [--ecu MotorECU] activate
 *   ./bootloader [--ecu MotorECU] rollback
 *   ./bootloader [--ecu MotorECU] status
 */

#include "bootloader.h"
#include <stdio.h>
#include <string.h>

static void print_usage(const char *prog)
{
    printf("Usage:\n");
    printf("  %s [--ecu NAME] stage   <firmware_path>   copy firmware into inactive slot\n", prog);
    printf("  %s [--ecu NAME] activate                  flip to staged slot, restart ECU\n", prog);
    printf("  %s [--ecu NAME] rollback                  flip back to previous slot, restart ECU\n", prog);
    printf("  %s [--ecu NAME] status                    print current version.json state\n", prog);
    printf("\nSupported ECUs: MotorECU, BrakeECU, BatteryECU\n");
}

int main(int argc, char *argv[])
{
    const char *ecu_name = BL_DEFAULT_ECU;
    int argi = 1;

    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    if (strcmp(argv[argi], "--ecu") == 0) {
        if (argc < 4) {
            fprintf(stderr, "ERROR: --ecu requires a name (MotorECU, BrakeECU, BatteryECU)\n");
            return 1;
        }
        ecu_name = argv[argi + 1];
        argi += 2;
    }

    bl_configure(ecu_name);

    if (argi >= argc) {
        print_usage(argv[0]);
        return 1;
    }

    const char *cmd = argv[argi];
    int rc = BL_OK;

    if (strcmp(cmd, "stage") == 0) {
        if (argc < argi + 2) {
            fprintf(stderr, "ERROR: 'stage' requires a firmware path.\n");
            fprintf(stderr, "  Usage: %s [--ecu NAME] stage <firmware_path>\n", argv[0]);
            return 1;
        }
        rc = bl_stage(argv[argi + 1]);

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
