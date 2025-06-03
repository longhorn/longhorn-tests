---
title: Test kubelet restart on a node of the cluster
---

### Related issues:
https://github.com/longhorn/longhorn/issues/2629

### Note:
- This is a refine version for match current behavior
- Using below command to restart kubelet
   - systemctl restart k3s-agent
   - systemctl restart rke2-agent

### Case 1: Restart Volume Node Kubelet Immediately
1. Create cluster with config of 1 etcd/control plane and 3 worker nodes.
2. Deploy Longhorn on the cluster.
3. Deploy a statefulSet with Longhorn volume.
4. Write some data into the mount point and compute the md5sum.
5. Restart the kubelet on the node where the statefulSet Pod is running
6. The volume kept healthy
7. Scale down then re-scale up the workload. Verify the existing data is correct.

### Case 2: Restart Volume Node Kubelet Immediately On Single node cluster
1. Create a single node cluster.
2. Follow the same steps and expected outcomes as in Case 1.

### Case 3: Restart Volume Node Kubelet After Temporary Downtime
1. Create cluster with config of 1 etcd/control plane and 3 worker nodes.
2. Deploy Longhorn on the cluster.
3. Deploy a statefulSet with Longhorn volume.
4. Write some data into the mount point and compute the md5sum.
5. Stop the kubelet on the node where the statefulSet Pod is running.
6. Observe volume status changed.
   - RWO volume become unknown.
   - RWX volume become degraded.
7. Start the kubelet stopped in step 6.
8. Volume become healthy.
9. Scale down then re-scale up the workload. Verify the existing data is correct.

### Case 4: Restart Volume Node Kubelet After Temporary Downtime On Single node cluster
1. Create a single node cluster.
2. Follow the same steps and expected outcomes as in Case 3, except that in step 6 the RWX volume transitions to a **Detached** state.
