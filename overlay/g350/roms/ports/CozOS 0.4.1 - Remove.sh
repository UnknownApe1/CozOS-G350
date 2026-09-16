#!/bin/bash
# Launch from KNULLI's Ports list.
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS needs the Python 3 included with supported KNULLI builds."
    sleep 10
    exit 1
fi

# Restore the real RK3326 boot logo first. If it was edited after CozOS,
# bootlogo.py refuses to overwrite the newer file and leaves the overlay intact.
python3 "${HERE}/cozos/bootlogo.py" remove
result=$?
if [ "$result" -eq 0 ]; then
    python3 "${HERE}/cozos/overlay.py" remove
    result=$?
fi

sleep 8
exit "$result"
