CC     = gcc
CFLAGS = -Wall -Wextra -Iinclude -I../Common/version_store

SRC = src/main.c \
      src/bootloader.c \
      ../Common/version_store/version_store.c

ifeq ($(OS),Windows_NT)
    OUT   = build/bootloader.exe
    MKDIR = if not exist build mkdir build
    CLEAN = del /Q build\*
else
    OUT   = build/bootloader
    MKDIR = mkdir -p build
    CLEAN = rm -rf build/*
endif

all:
	$(MKDIR)
	$(CC) $(CFLAGS) $(SRC) -o $(OUT)

clean:
	$(CLEAN)

rebuild: clean all
