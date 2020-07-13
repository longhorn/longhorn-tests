---
title: Testing ext4 without custom fs params
---
- create a volume + pv + pvc with filesystem `ext4` named `ext-ck-fail`
- create a deployment that uses `ext-ck-fail`
- verify `MountVolume.SetUp failed for volume "ext4-ck-fails"` is part of the pod events
- verify that the pod does not enter running state
