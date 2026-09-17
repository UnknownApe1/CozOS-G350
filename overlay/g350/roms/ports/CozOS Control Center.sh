#!/bin/bash
# One stable Ports entry for installing, maintaining, and removing CozOS.
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS needs the Python 3 included with supported KNULLI builds."
    sleep 10
    exit 1
fi

# EmulationStation launches Ports without a terminal.  The Control Center uses
# a controller-driven terminal UI, so open it in KNULLI's bundled SDL terminal
# when no TTY is attached. VaixTerm maps the handheld controls to terminal keys.
if { [ ! -t 0 ] || [ ! -t 1 ]; } && command -v vaixterm >/dev/null 2>&1; then
    exec vaixterm -w 640 -h 480 --no-credit --force-full-render \
        -e "python3 \"${HERE}/cozos/control_center.py\""
fi

python3 "${HERE}/cozos/control_center.py"
result=$?
sleep 3
exit "$result"
