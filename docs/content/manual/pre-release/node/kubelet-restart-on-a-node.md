---
title: Test kubelet restart on a node of the cluster
---

### Related issues:
https://github.com/longhorn/longhorn/issues/2629

### Case 1: Kubelet restart on RKE1 multi node cluster:
1. Create a RKE1 cluster with config of 1 etcd/control plane and 3 worker nodes.
2. Deploy Longhorn on the cluster.
3. Deploy prometheus monitoring app on the cluster which is using Longhorn storage class or deploy a statefulSet with Longhorn volume.
4. Write some data into the mount point and compute the md5sum.
5. Restart the kubelet on the node where the statefulSet or Prometheus pod is running using the command `sudo docker restart kubelet`
6. Observe the volume. It becomes degraded but is still running. 
7. Once the node is back, the volume of the workload should work fine and the data is intact.
8. Scale down then re-scale up the workload. Verify the existing data is correct.

### Case 2: Kubelet restart on one node RKE1 cluster:
1. Create a RKE1 cluster with config of 1 node all role.
2. Deploy Longhorn on the cluster.
3. Deploy prometheus monitoring app on the cluster which is using Longhorn storage class or deploy a statefulSet with Longhorn volume.
4. Write some data into the mount point and compute the md5sum.
5. Restart the kubelet on the node using the command `sudo docker restart kubelet`
6. Check the instance manager pods on the node are still running.
7. Observe the volume. It gets detached and the pod gets terminated (since the only replica of the volume becomes failed).
8. Once the pod is terminated, a new pod should be created and get attached to the volume successfully.
9. Verify that the mount of the volume is successful and data is safe.

### Case 3: rke2-server/rke2-agent restart on RKE2 multi node cluster:
1. Create a RKE2 cluster with config of 1 control plane and 3 worker nodes.
2. Deploy Longhorn on the cluster.
3. Deploy prometheus monitoring app on the cluster which is using Longhorn storage class or deploy a statefulSet with Longhorn volume.
4. Write some data into the mount point and compute the md5sum.
5. Restart the rke-agent service on the node where the statefulSet or Prometheus pod is running using the command `systemctl restart rke2-agent.service`
6. Observe the volume. It becomes degraded but is still running.
7. Once the node is back, the volume of the workload should work fine and the data is intact.
8. Scale down then re-scale up the workload. Verify the existing data is correct.
9. Create a StatefulSet with Longhorn volume on the control plane node.
10. Once the StatefulSet is up and running, Write some data into the mount point and compute the md5sum.
11. Restart the rke2-service on the control plane node using the command `systemctl restart rke2-server.service`.
12. Observe the volume. It becomes degraded but is still running.
13. Once the node is back, the volume of the workload should work fine and the data is intact.
14. Scale down then re-scale up the workload. Verify the existing data is correct.

### Case 4: Kubelet restart on a node with RWX volume on a RKE1 Cluster:
1. Create a RKE1 cluster with config of 1 etcd/control plane and 3 worker nodes.
2. Deploy Longhorn on the cluster.
3. Deploy a statefulSet attached with an RWX volume.
4. Write some data into the mount point and compute the md5sum.
5. Restart the kubelet on the node where the share-manager pod is running using the command `sudo docker restart kubelet`
6. Observe the volume. It gets detached and the share-manager pod gets terminated.
7. Watch the pod of the StatefulSet using the command `kubectl get pods -n <namespace> -w`.
8. The pods (share manager and StatefulSet, instance manager pods are not included) should be terminated and restarted.
9. Verify that the mount of the volume is successful and data is safe.
10. Repeat the above steps where the StatefulSet pod and share-manager pod are attached to different nodes and restart the node where the statefulSet pod is running.

### Case 5: Kubelet restart on a node with RWX volume on a RKE2 Cluster:
1. Repeat the steps from the case 4 on an RKE2 cluster.
