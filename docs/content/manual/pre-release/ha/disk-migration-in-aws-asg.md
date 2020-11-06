---
title: Disk migration in AWS ASG
---

## Some Longhorn worker nodes in AWS Auto Scaling group is in replacement
1. Set `ReplicaReplenishmentWaitInterval`. Make sure it's longer than the time needs for node replacement.
2. Launch a Kubernetes cluster with the nodes in AWS Auto Scaling group. Then Deploy Longhorn.
3. Deploy some workloads using Longhorn volumes.
4. Wait for/Trigger the ASG instance replacement.
5. Verify new replicas won't be created before reaching `ReplicaReplenishmentWaitInterval`.
6. Verify the failed replicas are reused after the node recovery.
7. Verify if workloads still work fine with the volumes after the recovery.
