#!/bin/bash
# Launch from KNULLI's Ports list.
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS needs the Python 3 included with supported KNULLI builds."
    sleep 10
    exit 1
fi
python3 "${HERE}/cozos/overlay.py" install
overlay_result=$?
if [ "$overlay_result" -eq 0 ]; then
    # Remove the verified but unused 0.4.3 /boot logo, then install the path
    # selected by this G350's actual KNULLI system-splash init script.
    python3 "${HERE}/cozos/bootlogo.py" remove
    legacy_result=$?
    if [ "$legacy_result" -eq 0 ]; then
        python3 "${HERE}/cozos/rootsplash.py" install
        splash_result=$?
    else
        splash_result=$legacy_result
    fi
else
    splash_result=0
fi
result=$overlay_result
if [ "$result" -eq 0 ] && [ "$splash_result" -ne 0 ]; then
    result=$splash_result
fi
sleep 10
exit "$result"
