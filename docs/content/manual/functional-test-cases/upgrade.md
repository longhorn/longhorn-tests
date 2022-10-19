---
title: 9. Upgrade
---

| **#**| **Test name** | **Description** |
| --- | --- | --- |
| 1   | Higher version of Longhorn engine and lower version of volume | Test Longhorn upgrade<br><br>1.  Create a volume, generate and write `data` into the volume.<br>2.  Keep the volume attached, then upgrade Longhorn system.<br>3.  Write data in volume.<br>4.  Take snapshot#1. Compute the checksum#1<br>5.  Write data to volume. Compute the checksum#2<br>6.  Take backup<br>7.  Revert to snapshot#1<br>8.  Restore the backup. |
| 2   | Restore the backup taken with older engine version | 1.  Create a volume, attach to a pod and write data into the volume. Compute md5sum of data<br>2.  Take a backup.<br>3.  Upgrade engine.<br>4.  Make the upgraded engine as default.<br>5.  Restore the backup, verify the checksum |