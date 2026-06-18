CC = gcc

CFLAGS = -Wall -Iinclude

SRC = src/main.c \
      src/health_monitor.c

OUT = build/health_monitor

all:
	mkdir -p build
	$(CC) $(CFLAGS) $(SRC) -o $(OUT)

clean:
	rm -rf build/*