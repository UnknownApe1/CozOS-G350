#!/bin/sh

set -eu

MIN_DISK_GIB=80
MIN_MEMORY_GIB=8

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker is not installed or is not on PATH."
docker info >/dev/null 2>&1 || fail "Docker is installed but the Docker engine is not running."

available_kib=$(df -Pk . | awk 'NR == 2 { print $4 }')
available_gib=$((available_kib / 1024 / 1024))
[ "$available_gib" -ge "$MIN_DISK_GIB" ] || fail "At least ${MIN_DISK_GIB} GiB free is required; ${available_gib} GiB is available."

if [ -r /proc/meminfo ]; then
    memory_kib=$(awk '/^MemTotal:/ { print $2 }' /proc/meminfo)
    memory_gib=$((memory_kib / 1024 / 1024))
    [ "$memory_gib" -ge "$MIN_MEMORY_GIB" ] || fail "At least ${MIN_MEMORY_GIB} GiB RAM is required; ${memory_gib} GiB is available."
fi

printf 'CozOS G350 build preflight passed.\n'
printf 'Free disk: %s GiB\n' "$available_gib"
printf 'Docker: %s\n' "$(docker --version)"

