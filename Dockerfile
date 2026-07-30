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

RUN pip3 install --no-cache-dir cryptography fastapi "uvicorn[standard]"

RUN make -C Firmware/motor_ecu            && echo "motor_ecu v1.0: OK"
RUN make -C Firmware/motor_ecu_v1.1       && echo "motor_ecu v1.1: OK"
RUN make -C Firmware/motor_ecu_v1.2_broken && echo "motor_ecu v1.2_broken: OK"
RUN make -C Firmware/brake_ecu            && echo "brake_ecu: OK"
RUN make -C Firmware/battery_ecu          && echo "battery_ecu: OK"
RUN make -C Health_Monitor              && echo "health_monitor: OK"
RUN make -C Bootloader                  && echo "bootloader: OK"

RUN python3 Tools/gen_keys.py

CMD ["bash", "-c", \
     "echo '=== SDV OTA Platform — Build Complete ===' && \
      echo '' && \
      echo 'motor_ecu v1.0:   ' $(test -f Firmware/motor_ecu/build/motor_ecu && echo OK || echo MISSING) && \
      echo 'motor_ecu v1.1:   ' $(test -f Firmware/motor_ecu_v1.1/build/motor_ecu && echo OK || echo MISSING) && \
      echo 'motor_ecu v1.2:   ' $(test -f Firmware/motor_ecu_v1.2_broken/build/motor_ecu && echo OK || echo MISSING) && \
      echo 'brake_ecu:        ' $(test -f Firmware/brake_ecu/build/brake_ecu && echo OK || echo MISSING) && \
      echo 'battery_ecu:      ' $(test -f Firmware/battery_ecu/build/battery_ecu && echo OK || echo MISSING) && \
      echo 'health_monitor:   ' $(test -f Health_Monitor/build/health_monitor && echo OK || echo MISSING) && \
      echo 'bootloader:       ' $(test -f Bootloader/build/bootloader && echo OK || echo MISSING) && \
      echo '' && \
      echo 'Run demos:' && \
      echo '  docker compose run dev bash' && \
      echo '  ./Scripts/run_demo.sh          # full OTA + rollback' && \
      echo '  ./Scripts/run_fleet_demo.sh    # multi-ECU fleet update']
