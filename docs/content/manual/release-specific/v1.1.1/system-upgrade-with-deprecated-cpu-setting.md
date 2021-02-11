---
title: Test system upgrade with the deprecated CPU setting
---

## Related issue
https://github.com/longhorn/longhorn/issues/2207

## Test step
1. Deploy a cluster that each node has different CPUs.
2. Launch Longhorn v1.1.0.
3. Deploy some workloads using Longhorn volumes.
4. Upgrade to the latest Longhorn version. Validate:
    1. all workloads work fine and no instance manager pod crash during the upgrade.
    2. The fields `node.Spec.EngineManagerCPURequest` and `node.Spec.ReplicaManagerCPURequest` of each node are the same as the setting `Guaranteed Engine CPU` value in the old version * 1000.
    3. The old setting `Guaranteed Engine CPU` is deprecated with an empty value. 
5. Modify new settings `Guaranteed Engine Manager CPU` and `Guaranteed Replica Manager CPU`. Validate all workloads work fine and no instance manager pod restart.
6. Scale down all workloads and wait for the volume detachment.
7. Set `node.Spec.EngineManagerCPURequest` and `node.Spec.ReplicaManagerCPURequest` to 0 for some node. Verify the new settings will be applied to those node and the related instance manager pods will be recreated with the CPU requests matching the new settings.
8. Scale up all workloads and verify the data as well as the volume r/w.
9. Do cleanup.
