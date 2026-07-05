/*
 * sensor.h — Firmware/motor_ecu_v1.1/include/sensor.h
 *
 * Added declarations for v1.1 Eco Mode functions.
 * v1.0 declarations unchanged so nothing else breaks.
 */

#ifndef SENSOR_H
#define SENSOR_H

/* v1.0 — standard mode */
int get_rpm(void);
int get_temperature(void);

/* v1.1 — Eco Mode (60% RPM, 5°C cooler) */
int get_rpm_eco(void);
int get_temperature_eco(void);

#endif
