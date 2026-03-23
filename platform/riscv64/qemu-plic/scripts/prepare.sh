#!/bin/bash
CONFIGS_DIR=./platform/riscv64/qemu-plic/configs
IMAGE_DIR=./platform/riscv64/qemu-plic/image
SCRIPTS_DIR=./platform/riscv64/qemu-plic/scripts

ROOTFS_DIR=${IMAGE_DIR}/virtdisk/rootfs
ROOTFS_IMG=${IMAGE_DIR}/virtdisk/rootf1.ext4
IMAGE=${IMAGE_DIR}/kernel/Image
ZONE1_DTB=${IMAGE_DIR}/dts/zone1-linux.dtb
ZONE1_BOOT_SCRIPT=${SCRIPTS_DIR}/boot_zone1.sh


mount -t ext4 ${ROOTFS_IMG} ${ROOTFS_DIR}

cp ${HVISOR_TOOL_PATH}/output/hvisor ${HVISOR_TOOL_PATH}/output/hvisor.ko ${ROOTFS_DIR}/home/riscv/
cp ${CONFIGS_DIR}/* ${ROOTFS_DIR}/home/riscv/
cp ${IMAGE} ${ROOTFS_DIR}/home/riscv/
cp ${ZONE1_DTB} ${ROOTFS_DIR}/home/riscv/
cp ${ZONE1_BOOT_SCRIPT} ${ROOTFS_DIR}/home/riscv/

umount ${ROOTFS_DIR}

