#!/bin/sh

set -x

ARCH=${ARCH:-riscv64}
BOARD=${BOARD:-qemu-plic}
PLATFORM_DIR=./platform/${ARCH}/${BOARD}

CONFIGS_DIR=${PLATFORM_DIR}/configs
IMAGE_DIR=${PLATFORM_DIR}/image
SCRIPTS_DIR=${PLATFORM_DIR}/scripts
VIRTDISK_DIR=${IMAGE_DIR}/virtdisk

ROOTFS_DIR=${IMAGE_DIR}/virtdisk/rootfs
ROOTFS_IMG=${IMAGE_DIR}/virtdisk/rootf1.ext4
IMAGE=${IMAGE_DIR}/kernel/Image
ZONE1_DTB=${IMAGE_DIR}/dts/zone1-linux.dtb
ZONE1_BOOT_SCRIPT=${SCRIPTS_DIR}/boot_zone1.sh

cp ${VIRTDISK_DIR}/rootfs1.ext4 ${ROOTFS_IMG}

mount -t ext4 ${ROOTFS_IMG} ${ROOTFS_DIR} || true

if [ -z "${HVISOR_TOOL_PATH}" ]; then
    HVISOR_TOOL_PATH=~/hvisor-tool
fi

echo "HVISOR_TOOL_PATH: ${HVISOR_TOOL_PATH}"

cp ${HVISOR_TOOL_PATH}/output/hvisor ${HVISOR_TOOL_PATH}/output/hvisor.ko ${ROOTFS_DIR}/root/
cp ${CONFIGS_DIR}/* ${ROOTFS_DIR}/root/
cp ${IMAGE} ${ROOTFS_DIR}/root/
cp ${ZONE1_DTB} ${ROOTFS_DIR}/root/
cp ${ZONE1_BOOT_SCRIPT} ${ROOTFS_DIR}/root/

umount ${ROOTFS_DIR}

