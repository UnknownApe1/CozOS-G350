#!/bin/sh

set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
G350_IMAGE_ONLY='BR2_TARGET_KNULLI_IMAGES="rockchip/rk3326/g350"'

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

cd "$PROJECT_DIR"
sh "$PROJECT_DIR/scripts/cozos/preflight.sh"

printf 'Building the G350-only RK3326 image from %s\n' "$(git rev-parse --short HEAD)"
make rk3326-build \
    BATCH_MODE=1 \
    PARALLEL_BUILD=1 \
    EXTRA_OPTS="$G350_IMAGE_ONLY"

image=$(find "$PROJECT_DIR/output/rk3326/images/knulli/images/g350" \
    -maxdepth 1 -type f -name '*.img.gz' -print | sort | tail -n 1)

[ -n "$image" ] || fail "Build finished without producing a G350 image."

sha256sum "$image" > "$image.sha256"
printf 'Image: %s\n' "$image"
printf 'SHA-256: %s\n' "$image.sha256"
