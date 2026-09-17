#!/bin/bash
# Stable Ports bootstrap/launcher for CozOS. The launcher itself stays in Ports;
# versioned Control Center application files live under userdata/system/cozos.
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
BUNDLED="${HERE}/cozos"
STATE="${COZOS_STATE:-/userdata/system/cozos}"
APPS="${STATE}/apps"
ACTIVE="${STATE}/active-version"
BOOTSTRAP_VERSION="0.6.0"

if ! command -v python3 >/dev/null 2>&1; then
    echo "CozOS needs the Python 3 included with supported KNULLI builds."
    sleep 10
    exit 1
fi

mkdir -p "${APPS}"
if [ ! -s "${ACTIVE}" ]; then
    DEST="${APPS}/${BOOTSTRAP_VERSION}"
    STAGE="${APPS}/${BOOTSTRAP_VERSION}.bootstrap"
    rm -rf "${STAGE}"
    mkdir -p "${STAGE}"
    cp -a "${BUNDLED}/." "${STAGE}/"
    if [ ! -f "${STAGE}/main.py" ] || [ ! -f "${STAGE}/updater.py" ]; then
        echo "CozOS bootstrap validation failed. The Ports package is incomplete."
        rm -rf "${STAGE}"
        sleep 10
        exit 1
    fi
    rm -rf "${DEST}"
    mv "${STAGE}" "${DEST}"
    printf '%s\n' "${BOOTSTRAP_VERSION}" > "${ACTIVE}.tmp"
    mv "${ACTIVE}.tmp" "${ACTIVE}"
fi

VERSION="$(tr -d '\r\n' < "${ACTIVE}")"
APP="${APPS}/${VERSION}"
ENTRY="${APP}/main.py"
if [ ! -f "${ENTRY}" ]; then
    echo "CozOS active version ${VERSION} is incomplete."
    echo "Delete ${ACTIVE} to force a safe bootstrap from the Ports package."
    sleep 10
    exit 1
fi

if { [ ! -t 0 ] || [ ! -t 1 ]; } && command -v vaixterm >/dev/null 2>&1; then
    export SDL_GAMECONTROLLER_USE_BUTTON_LABELS=1
    exec vaixterm -w 640 -h 480 --no-credit --force-full-render \
        -e "cd \"${APP}\" && python3 \"${ENTRY}\""
fi

cd "${APP}" || exit 1
python3 "${ENTRY}"
result=$?
sleep 3
exit "$result"
