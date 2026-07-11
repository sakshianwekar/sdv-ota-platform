CC     = gcc
CFLAGS = -Wall -Wextra -Iinclude -I../../Common/version_store

SRC = src/main.c \
      src/version.c \
      src/sensor.c \
      src/heartbeat.c \
      src/diagnostics.c \
      ../../Common/version_store/version_store.c

# Cross-platform output name and mkdir
ifeq ($(OS),Windows_NT)
    OUT   = build/motor_ecu.exe
    MKDIR = if not exist build mkdir build
    CLEAN = del /Q build\*
else
    OUT   = build/motor_ecu
    MKDIR = mkdir -p build
    CLEAN = rm -rf build/*
endif

all:
	$(MKDIR)
	$(CC) $(CFLAGS) $(SRC) -o $(OUT)

clean:
	$(CLEAN)

rebuild: clean all
