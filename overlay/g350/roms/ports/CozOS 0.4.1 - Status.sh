#!/bin/bash
# Launch from KNULLI's Ports list.
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS needs the Python 3 included with supported KNULLI builds."
    sleep 10
    exit 1
fi

python3 "${HERE}/cozos/overlay.py" status
overlay_result=$?
echo
python3 "${HERE}/cozos/bootlogo.py" status
logo_result=$?

result=$overlay_result
if [ "$logo_result" -ne 0 ]; then
    result=$logo_result
fi
sleep 8
exit "$result"
