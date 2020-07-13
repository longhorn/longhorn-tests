---
title: Testing ext4 with custom fs params1 (no 64bit, no metadata_csum)
---
- set the following filesystem parameters: `-O ^64bit,^metadata_csum`
- create a volume + pv + pvc with filesystem `ext4` named `ext4-no-ck-no-64`
- create a deployment that uses `ext4-no-ck-no-64`
- verify that the pod enters running state and the volume is accessible
