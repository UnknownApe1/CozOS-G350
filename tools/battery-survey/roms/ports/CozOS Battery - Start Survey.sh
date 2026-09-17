#!/bin/bash
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
python3 "${HERE}/cozos-battery/battery_survey.py" start
result=$?
sleep 10
exit "$result"
