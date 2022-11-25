---
title: Test filesystem trim
---

## Related issue
https://github.com/longhorn/longhorn/issues/836

## Case 1: Test filesystem trim during writing

**Given** A 10G volume created.

*And* Volume attached to `node-1`.

*And* Make a filesystem like EXT4 or XFS for the volume.

*And* Mount the filesystem on a mount point.

**Then** Run the below shell script with the correct mount point specified:
```shell
#!/usr/bin/env bash

MOUNT_POINT=${1}

dd if=/dev/urandom of=/mnt/data bs=1M count=8000
sync
CKSUM=`md5sum /mnt/data | awk '{print $1}'`

for INDEX in {1..10..1};
do
  rm -rf ${MOUNT_POINT}/data

  dd if=/mnt/data of=${MOUNT_POINT}/data &

  RAND_SLEEP_INTERVAL=$(($(($RANDOM%50))+10))
  sleep ${RAND_SLEEP_INTERVAL}

  fstrim ${MOUNT_POINT}
  while [ `ps aux | grep "dd if" | grep -v grep | wc -l` -eq "1" ]
  do
    sleep 1
  done

  CUR_CKSUM=`md5sum ${MOUNT_POINT}/data | awk '{print $1}'`
  if [ $CUR_CKSUM != $CKSUM ]
  then
    echo "invalid file found, expected checksum $CKSUM, current checksum $CUR_CKSUM"
    exit 1
  fi

  rm -f ${MOUNT_POINT}/data
done
```

**Then** The script execution should succeed.


## Case 2: Test flag `unmapMarkSnapChainRemoved` unchanged after volume engine upgrade

**Given** 2 engine images that contain the filesystem trim PR deployed.

*And* A volume created.

*And* Volume attached to `node-1`.

*And* Volume field `unmapMarkSnapChainRemoved` is set to `enabled`.

*And* Start monitoring the log of instance manager pods.

*And* Upgrade this attached volume with another engine image.

**Then** There is no logs in the instance manager pods during and after the upgrade:
```log
"Get backend <replica address> UnmapMarkSnapChainRemoved false"
"Set backend <replica address> UnmapMarkSnapChainRemoved true"
```

*And* This flag still works for the volume. (Trimming the filesystem of the volume will trigger snapshot auto removal.)
