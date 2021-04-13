---
title: "Workload type: Stateful set"
---
Volume Attachment Recovery Policy: **Immediate:**
- Have a stateful set workload deployed using volume claim template using longhorn storage class.
- Number of pods - 6.
- 2 pods are scheduled on N1.
- Power off N1. The 2 pods go into `Terminating` state.
- replacement pods are NOT created.
- force delete the 2 pods in `Terminating` state.
- replacement pods are created.
- first pod comes up in about 30 seconds.
- data is accessible in the volume.
- It takes another 1 minute approx for the second pod to come up.
- data is accessible in the volume.

Volume Attachment Recovery Policy: **wait:**
- Have a stateful set workload deployed using volume claim template using longhorn storage class.
- Number of pods - 6.
- 1 pod is scheduled on N1.
- Power off N1. The pod goes into `Terminating` state.
- replacement pod is NOT created.
- force delete this pod in `Terminating` state.
- replacement pod is created.
- It comes up in about 30 seconds.
- data is accessible in the volume.

Volume Attachment Recovery Policy: **never:**
- Have a stateful set workload deployed using volume claim template using longhorn storage class.
- Number of pods - 6.
- 2 pods are scheduled on N1.
- Power off N1. The 2 pods go into `Terminating` state.
- replacement pods are NOT created.
- force delete the 2 pods in `Terminating` state.
- replacement pods are created.
- first pod comes up in about 30 seconds.
- data is accessible in the volume.
- It takes another 1 minute approx for the second pod to come up.
- data is accessible in the volume.

**Note:** All the above behavior will depend on `NodeDownPodDeletionPolicy`. It is assumed that `NodeDownPodDeletionPolicy` is set to `do-nothing` while executing the above scenarios.
