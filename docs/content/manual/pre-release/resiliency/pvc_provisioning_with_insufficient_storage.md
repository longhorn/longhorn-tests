---
title: "PVC provisioning with insufficient storage"
---

#### Related Issue:
- https://github.com/longhorn/longhorn/issues/4654
- https://github.com/longhorn/longhorn/issues/3529
- https://github.com/longhorn/longhorn/issues/6461

#### Root Cause Analysis
- https://github.com/longhorn/longhorn/issues/4654#issuecomment-1264870672

This case need to be tested on both RWO/RWX volumes

1. Create a PVC with size larger than `8589934591` GiB.
    - Deployment keep in pending status, RWO/RWX volume will keep in a create -> delete loop.
1. Create a PVC with size <= `8589934591` GiB, but greater than the actual available space size.
    - RWO/RWX volume will be created, and the associated PV for this volume will have annotation "**longhorn.io/volume-scheduling-error**": "**insufficient storage**" in it.
    - We can observe "**Scheduling Failure**" and "**Replica Scheduling Failure**" error messages on the Longhorn UI with the following details
        - **Scheduling Failure**
        - Replica Scheduling Failure
        - Error Message: insufficient storage
1. Create a PVC with size < the actual available space size，Resize the PVC to a not schedulable size
    - After resize PVC to a not schedulable size, both RWO/RWX were still in scheduling status.

We can modify/use https://raw.githubusercontent.com/longhorn/longhorn/master/examples/rwx/rwx-nginx-deployment.yaml to deploy RWO/RWX PVC for this test 