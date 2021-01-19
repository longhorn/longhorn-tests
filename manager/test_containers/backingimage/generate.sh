#!/bin/bash -e

if [ ! -f parrot.qcow2 ]; then
  qemu-img create -f qcow2 parrot.img 32M
  mkdir -p parrot
  sudo modprobe nbd max_part=63
  sudo qemu-nbd -f qcow2 -c /dev/nbd0 parrot.img
  sudo mkfs -t ext4 /dev/nbd0
  sudo mount /dev/nbd0 parrot
#  Please update this link if the downloaded file is invalid
  curl -L https://cultofthepartyparrot.com/guests-01a9353989.zip -o parrot.zip
  sudo unzip -o parrot.zip -d parrot
  rm -f parrot.zip
  sudo umount parrot
  sudo killall qemu-nbd
  rmdir parrot
  qemu-img convert -c -O qcow2 parrot.img parrot.qcow2
  rm -f parrot.img
fi

if [ ! -f parrot.raw ]; then
  qemu-img convert -f qcow2 -O raw parrot.qcow2 parrot.raw
fi

# Need to upload the image files to the Longhorn S3 storage.
# https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
# https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.raw
pwd parrot.qcow2
pwd parrot.raw
