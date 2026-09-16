#!/bin/bash
# Launch from KNULLI's Ports list.
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS needs the Python 3 included with supported KNULLI builds."
    sleep 10
    exit 1
fi

# Keep the proven 0.4.1 power/brightness/tuning installer intact, then apply
# the G350 RK3326 boot artwork through the real /boot/bootlogo.bmp path.
python3 "${HERE}/cozos/overlay.py" install
result=$?
if [ "$result" -eq 0 ]; then
    python3 "${HERE}/cozos/bootlogo.py" install
    result=$?
fi

sleep 8
exit "$result"
