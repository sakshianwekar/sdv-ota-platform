CC = gcc

CFLAGS = -Iinclude

SRC = src/main.c \
      src/version.c \
      src/sensor.c \
      src/heartbeat.c \
      src/diagnostics.c

OUT = build/motor_ecu

all:
	mkdir -p build
	$(CC) $(CFLAGS) $(SRC) -o $(OUT)

clean:
	rm -f $(OUT)
	