#!/bin/bash

insmod hvisor.ko
mkdir -p /dev/pts
mount -t devpts devpts /dev/pts
./hvisor virtio start virtio_cfg.json &
./hvisor zone start zone1_linux.json