#!/bin/bash
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
python3 "${HERE}/cozos-battery/battery_survey.py" snapshot
result=$?
sleep 12
exit "$result"
