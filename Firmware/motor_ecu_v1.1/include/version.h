/*
 * version.h — Firmware/motor_ecu_v1.1/include/version.h
 *
 * Version bumped to 1.1
 * get_active_slot() declaration carried forward from Phase 5
 */

#ifndef VERSION_H
#define VERSION_H

#include "version_store.h"

const char* get_version(void);
const char* get_active_slot(void);

#endif
