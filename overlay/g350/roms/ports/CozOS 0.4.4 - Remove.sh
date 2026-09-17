#!/bin/bash
# Launch from KNULLI's Ports list.
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS needs the Python 3 included with supported KNULLI builds."
    sleep 10
    exit 1
fi
python3 "${HERE}/cozos/rootsplash.py" remove
splash_result=$?
python3 "${HERE}/cozos/bootlogo.py" remove
legacy_result=$?
python3 "${HERE}/cozos/overlay.py" remove
overlay_result=$?
result=$splash_result
if [ "$result" -eq 0 ] && [ "$legacy_result" -ne 0 ]; then result=$legacy_result; fi
if [ "$result" -eq 0 ] && [ "$overlay_result" -ne 0 ]; then result=$overlay_result; fi
sleep 10
exit "$result"
