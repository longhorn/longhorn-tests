---
title: "[#2206](https://github.com/longhorn/longhorn/issues/2206) Fix the spinning disk on Longhorn"
---

This case requires the creation of a slow virtual disk with `dmsetup`.
1. Make a slow disk:
    - Make a disk image file: `truncate -s 10g slow.img`
    - Create a loopback device: `losetup --show -P -f slow.img`
    - Get the block size of the loopback device: `blockdev --getsize /dev/loopX`
    - Create slow device: `echo "0 <blocksize> delay /dev/loopX 0 500" | dmsetup create dm-slow`
    - Format slow device: `mkfs.ext4 /dev/mapper/dm-slow`
    - Mount slow device: `mount /dev/mapper/dm-slow /mnt`
2. Build longhorn-engine and run it on the slow disk.
    - `make` or use a tag from docker hub in next step.
    - `docker run --privileged -v /dev:/host/dev -v /proc:/host/proc -v /mnt:/volume longhornio/longhorn-engine:<tag> launch-simple-longhorn slow-vol 10g tgt-blockdev`
3. Perform intense I/O and verify that it doesn't fail.
    - This uses an iodepth of 16 to maximize the number of threads in tgtd.  An iodepth of 16 or more will maximize the number of threads in tgtd. `fio --name=random-writers --ioengine=libaio --rw=randwrite --bs=1280k --direct=1 --size=3000m --numjobs=1 --filename=/dev/longhorn/slow-vol --iodepth=16 --verify=sha256`
    - This exceeds the number of operations tgtd and longhorn can handle simultaneously. `fio --name=random-writers --ioengine=libaio --rw=randwrite --bs=16k --direct=1 --size=10m --numjobs=4 --filename=/dev/longhorn/slow-vol --iodepth=128 --verify=sha256`
    - This tests performing one I/O operation at a time: `fio --name=random-writers --ioengine=libaio --rw=randwrite --bs=4k --direct=1 --size=10m --numjobs=1 --filename=/dev/longhorn/slow-vol --iodepth=1 --verify=sha256`


5. Repeat with different filesystems, i.e use `mkfs.xfs` instead of `mkfs.ext4`.

