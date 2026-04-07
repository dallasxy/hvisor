#!/bin/bash
# Success when minicom runscript exits 0 (see test.scr: exit 0 / exit 1).
#
case "${TERM:-}" in
    ''|unknown|dumb) export TERM=vt100 ;;
esac

sudo minicom -o -D /dev/ttyUSB1 -b 1500000 -S ./test.scr &
PID=$!

cleanup() {
    if kill -0 "$PID" 2>/dev/null; then
        sudo kill -9 "$PID" 2>/dev/null || true
        wait "$PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

wait "$PID"
exit $?
