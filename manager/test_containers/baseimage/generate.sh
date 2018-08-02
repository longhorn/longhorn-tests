#!/bin/bash -e

if [ ! -f parrot.qcow2 ]; then
  qemu-img create -f qcow2 parrot.img 32M
  mkdir -p parrot
  sudo modprobe nbd max_part=63
  sudo qemu-nbd -f qcow2 -c /dev/nbd0 parrot.img
  sudo mkfs -t ext4 /dev/nbd0
  sudo mount /dev/nbd0 parrot
  curl -L http://cultofthepartyparrot.com/guests-0b1895434d.zip -o parrot.zip
  sudo unzip -o parrot.zip -d parrot
  rm -f parrot.zip
  sudo umount parrot
  sudo killall qemu-nbd
  rmdir parrot
  qemu-img convert -c -O qcow2 parrot.img parrot.qcow2
  rm -f parrot.img
fi

docker build \
  -t rancher/longhorn-test:baseimage-ext4 \
  --build-arg BASE_IMAGE=parrot.qcow2 \
    .

docker push rancher/longhorn-test:baseimage-ext4
