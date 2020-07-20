---
title: Testing ext4 with custom fs params2 (no metadata_csum)
---
- set the following filesystem parameters: `-O ^metadata_csum`
- create a volume + pv + pvc with filesystem `ext4` named `ext4-no-ck`
- create a deployment that uses `ext4-no-ck`
- verify that the pod enters running state and the volume is accessible
