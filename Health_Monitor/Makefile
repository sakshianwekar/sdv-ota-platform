CC     = gcc
CFLAGS = -Wall -Wextra -I.

SRC = health_monitor.c

ifeq ($(OS),Windows_NT)
    OUT   = build/health_monitor.exe
    MKDIR = if not exist build mkdir build
    CLEAN = del /Q build\*
else
    OUT   = build/health_monitor
    MKDIR = mkdir -p build
    CLEAN = rm -rf build/*
endif

all:
	$(MKDIR)
	$(CC) $(CFLAGS) $(SRC) -o $(OUT)

clean:
	$(CLEAN)

rebuild: clean all
