---
title: "Workload type: Deployment"
---
Volume Attachment Recovery Policy : **Immediate:**
- Have a workload deployed using longhorn volume
- change the `terminationGracePeriodSeconds: 480` in the yaml of the workload.
- Power down the node where the pod is attached on
- The replacement pod is created after 5 minutes from when the original pod goes into `Unknown` state. And this replacement pod is in "creating/pending" state
- the volume is able to attach/mount and workload come up in about 30 seconds
- data is accessible after the pod comes up active

Volume Attachment Recovery Policy: **wait:**

- Have a workload deployed using longhorn volume
- change the `terminationGracePeriodSeconds: 480` in the yaml of the workload.
- Power down the node where the pod is attached on
- The replacement pod is created after 5 minutes from when the original pod goes into Unknown state. And this replacement pod is in "creating/pending" state
- the volume is able to attach/mount and workload come up only after about 15 minutes.
- data is accessible after the pod comes up active

Volume Attachment Recovery Policy: **never:**

- Have a workload deployed using longhorn volume
- change the `terminationGracePeriodSeconds: 480` in the yaml of the workload.
- Power down the node where the pod is attached on
- The replacement pod is created after 5 minutes from when the original pod goes into Unknown state. And this replacement pod is in "creating/pending" state
- the volume is NOT able to attach/mount and workload come up even for an hour.
- Delete the pod stuck in "Unknown" status
- Replacement pod comes up in about 1 minute
- data is accessible after the pod comes up active
