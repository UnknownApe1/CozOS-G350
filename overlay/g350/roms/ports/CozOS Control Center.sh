#!/bin/bash
# One stable Ports entry for installing, maintaining, and removing CozOS.
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS needs the Python 3 included with supported KNULLI builds."
    sleep 10
    exit 1
fi

python3 "${HERE}/cozos/control_center.py"
result=$?
sleep 3
exit "$result"
