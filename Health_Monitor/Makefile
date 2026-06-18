CC = gcc

CFLAGS = -Wall -Iinclude

SRC =health_monitor.c

OUT = build/health_monitor

all:
	mkdir build
	$(CC) $(CFLAGS) $(SRC) -o $(OUT)

clean:
	rm -rf build/*