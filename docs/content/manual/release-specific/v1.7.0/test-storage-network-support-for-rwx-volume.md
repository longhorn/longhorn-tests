---
title: Storage Network Support for RWX Volume
---

## Related Issues

- https://github.com/longhorn/longhorn/issues/8184

## Test Longhorn Upgrade with Pre-existing RWX Volume Workloads and Storage Network Configured

Verify the behavior of Longhorn RWX volume workloads during and after the cluster upgrade process with existing storage network configured. Ensure no disruption to existing workload pods during the upgrade.

**Given** A cluster with Longhorn v1.6.2 installed.
```bash
> kubectl -n longhorn-system get daemonsets.apps longhorn-manager -o yaml | grep image:
        image: longhornio/longhorn-manager:v1.6.2
```
**And** The `storage-network` setting is set to a valid NAD.
```bash
> kubectl -n longhorn-system get setting storage-network
NAME              VALUE                          AGE
storage-network   kube-system/demo-192-168-0-0   66s
```
**And** The `auto-delete-pod-when-volume-detached-unexpectedly` setting is set to true.
```bash
> kubectl -n longhorn-system get setting auto-delete-pod-when-volume-detached-unexpectedly
NAME                                                VALUE   AGE
auto-delete-pod-when-volume-detached-unexpectedly   true    85s
```
**And** RWX volume workload 1 is created.
```bash
> kubectl get pod
NAME                     READY   STATUS    RESTARTS   AGE
rwx-1-6c6dd9764c-jrqvh   2/2     Running   0          98s
rwx-1-6c6dd9764c-k66f8   2/2     Running   0          98s
rwx-1-6c6dd9764c-rqnkf   2/2     Running   0          98s
```

**When** update Longhorn to v1.7.0.

**Then** Longhorn CSI plugin pods are not annotated with the storage network.
```bash
> kubectl -n longhorn-system get pod longhorn-csi-plugin-682cr -o yaml | grep k8s.v1.cni.cncf.io/networks
```

**And** workload 1 is not restarted.
```bash
> kubectl -n longhorn-system get pod -l app=longhorn-csi-plugin
NAME                        READY   STATUS    RESTARTS   AGE
longhorn-csi-plugin-682cr   3/3     Running   0          22s
longhorn-csi-plugin-bkbbr   3/3     Running   0          22s
longhorn-csi-plugin-dkzjz   3/3     Running   0          22s

> kubectl get pod
NAME                     READY   STATUS    RESTARTS   AGE
rwx-1-6c6dd9764c-jrqvh   2/2     Running   0          3m32s
rwx-1-6c6dd9764c-k66f8   2/2     Running   0          3m32s
rwx-1-6c6dd9764c-rqnkf   2/2     Running   0          3m32s
```

**And** workload 1 data is accessible.
```bash
> kubectl exec -it rwx-1-6c6dd9764c-jrqvh -- ls /data
Defaulted container "run" out of: run, nginx
index.html  lost+found
```
