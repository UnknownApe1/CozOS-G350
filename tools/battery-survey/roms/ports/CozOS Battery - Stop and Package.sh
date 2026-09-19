#!/bin/bash
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
python3 "${HERE}/cozos-battery/battery_survey.py" stop-package
result=$?
sleep 12
exit "$result"
