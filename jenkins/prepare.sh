#!/bin/sh

set -eux

ARCH=${ARCH:?ARCH is required}
BOARD=${BOARD:?BOARD is required}
WORKSPACE_ROOT=${WORKSPACE_ROOT:-$(pwd)}
HVISOR_TOOL_PATH=${HVISOR_TOOL_PATH:-${WORKSPACE_ROOT}/hvisor-tool}

case "${HVISOR_TOOL_PATH}" in
    /*) ;;
    *) HVISOR_TOOL_PATH="${WORKSPACE_ROOT}/${HVISOR_TOOL_PATH}" ;;
esac

PLATFORM_DIR="${WORKSPACE_ROOT}/platform/${ARCH}/${BOARD}"
CONFIGS_DIR="${PLATFORM_DIR}/configs"
IMAGE_DIR="${PLATFORM_DIR}/image"
SCRIPTS_DIR="${PLATFORM_DIR}/scripts"
VIRTDISK_DIR="${IMAGE_DIR}/virtdisk"

ROOTFS_DIR="${VIRTDISK_DIR}/rootfs"
ROOTFS_IMG="${VIRTDISK_DIR}/rootfs1.ext4"
IMAGE="${IMAGE_DIR}/kernel/Image"
ZONE1_DTB="${IMAGE_DIR}/dts/zone1-linux.dtb"
ZONE1_DTS_DIR="${IMAGE_DIR}/dts"
ZONE1_BOOT_SCRIPT="${SCRIPTS_DIR}/boot_zone1.sh"

mkdir -p "${ROOTFS_DIR}"

if [ ! -f "${ROOTFS_IMG}" ]; then
    echo "error: rootfs image not found: ${ROOTFS_IMG}"
    exit 1
fi

if mountpoint -q "${ROOTFS_DIR}"; then
    umount "${ROOTFS_DIR}"
fi

mount -t ext4 "${ROOTFS_IMG}" "${ROOTFS_DIR}"
trap 'umount "${ROOTFS_DIR}"' EXIT

echo "ARCH: ${ARCH}"
echo "BOARD: ${BOARD}"
echo "HVISOR_TOOL_PATH: ${HVISOR_TOOL_PATH}"

cp "${HVISOR_TOOL_PATH}/output/hvisor" "${HVISOR_TOOL_PATH}/output/hvisor.ko" "${ROOTFS_DIR}/root/"
cp "${CONFIGS_DIR}/"* "${ROOTFS_DIR}/root/"
cp "${IMAGE}" "${ROOTFS_DIR}/root/"

if [ ! -f "${ZONE1_DTB}" ]; then
    if [ -d "${ZONE1_DTS_DIR}" ]; then
        echo "zone1 dtb is missing, building it from ${ZONE1_DTS_DIR}"
        make -C "${ZONE1_DTS_DIR}" all || true
    else
        echo "warning: dts directory not found: ${ZONE1_DTS_DIR}"
    fi
fi

if [ -f "${ZONE1_DTB}" ]; then
    cp "${ZONE1_DTB}" "${ROOTFS_DIR}/root/"
else
    echo "warning: zone1 dtb is unavailable, skip copying ${ZONE1_DTB}"
fi

cp "${ZONE1_BOOT_SCRIPT}" "${ROOTFS_DIR}/root/"
if [ -f "${ROOTFS_DIR}/root/boot_zone1.sh" ]; then
    chmod +x "${ROOTFS_DIR}/root/boot_zone1.sh"
fi
if [ -f "${ROOTFS_DIR}/root/screen_zone1.sh" ]; then
    chmod +x "${ROOTFS_DIR}/root/screen_zone1.sh"
fi
