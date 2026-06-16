CC = gcc

CFLAGS = -Wall -Iinclude

SRC = src/main.c \
      src/version.c \
      src/sensor.c \
      src/heartbeat.c \
      src/diagnostics.c

OUT = build/motor_ecu.exe

all:
	@if not exist build mkdir build
	$(CC) $(CFLAGS) $(SRC) -o $(OUT)

clean:
	del /Q build\*

rebuild: clean all