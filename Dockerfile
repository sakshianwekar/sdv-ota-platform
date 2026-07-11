FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    make \
    cmake \
    python3 \
    python3-pip \
    python3-venv \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN make -C Firmware/motor_ecu   && echo "motor_ecu: OK"
RUN make -C Health_Monitor       && echo "health_monitor: OK"
RUN make -C Bootloader           && echo "bootloader: OK"

CMD ["bash", "-c", \
     "echo '=== SDV OTA Platform — Build Complete ===' && \
      echo '' && \
      echo 'motor_ecu:      ' $(test -f Firmware/motor_ecu/build/motor_ecu && echo OK || echo MISSING) && \
      echo 'health_monitor: ' $(test -f Health_Monitor/build/health_monitor && echo OK || echo MISSING) && \
      echo 'bootloader:     ' $(test -f Bootloader/build/bootloader && echo OK || echo MISSING) && \
      echo '' && \
      echo 'Run commands inside container:' && \
      echo '  docker compose run dev bash' && \
      echo '  ./Bootloader/build/bootloader status'"]
