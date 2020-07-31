---
title: Testing xfs after custom fs params (xfs should ignore the custom fs params)
---
- create a volume + pv + pvc with filesystem `xfs` named `xfs-ignores`
- create a deployment that uses `xfs-ignores`
- verify that the pod enters running state and the volume is accessible
