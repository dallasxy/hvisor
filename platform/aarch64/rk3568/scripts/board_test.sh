#!/bin/bash

LOG_FILE=./board_test.log
rm -f "$LOG_FILE"

sudo minicom -o -D /dev/ttyUSB0 -b 1500000 -S ./test.scr -C "$LOG_FILE" &
PID=$!

#TODO: send com command to boot

sleep 120

while kill -0 "$PID" 2>/dev/null; do
    if rg -q "test success" "$LOG_FILE"; then
        sudo kill -9 "$PID"
        wait "$PID" 2>/dev/null
        exit 0
    fi
    sleep 10
done

wait "$PID"
exit $?