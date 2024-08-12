---
title: RWX Fast Failover
---

## Related issues

- https://github.com/longhorn/longhorn/issues/6205

## LEP

- https://github.com/longhorn/longhorn/pull/9069

## Test Failover with I/O

**Given** Longhorn cluster with 3 worker nodes.

**And** Enable the feature by setting `rwx-enable-fast-failover` to true.
    Ensure that setting `auto-delete-pod-when-volume-detached-unexpectedly` is set to its default value of true.

**And** Deploy an RWX volume with default storage class.  Run an app pod with the RWX volume on each worker node.  Execute the command in each app pod

        `( exec 7<>/data/testfile-${i}; flock -x 7; while date | dd conv=fsync >&7 ; do sleep 1; done )`

        where ${i} is the node number.

**Then** Turn off or restart the node where share-manager is running.

**Verify** The share-manager pod is recreated on a different node.
    - In the client side, IO to the RWX volume will hang until a share-manager pod replacement is successfully created on another node.  
    - During the outage, the server rejects READ and WRITE operations and non-reclaim locking requests (i.e., other LOCK and OPEN operations) with an error of NFS4ERR_GRACE.  
    - New share-manager pod is created in under 20 seconds.  
    - Outage, including grace period, should be less than 60 seconds.  

## Test Mount Options

**Given** Longhorn cluster with 3 worker nodes.

**And** Enable the feature by setting `rwx-enable-fast-failover` to true.
    Ensure that setting `auto-delete-pod-when-volume-detached-unexpectedly` is set to its default value of true.

**And** Create a custom storage class with settings (nfsOptions: "hard,timeo=50,retrans=1")

```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: longhorn-test-hard
provisioner: driver.longhorn.io
allowVolumeExpansion: true
reclaimPolicy: Delete
volumeBindingMode: Immediate
parameters:
  numberOfReplicas: "3"
  staleReplicaTimeout: "2880"
  fromBackup: ""
  fsType: "ext4"
  nfsOptions: "hard,timeo=50,retrans=1"
```

**And** Use the deployment in [example]([https://github.com/longhorn/longhorn/blob/master/examples/rwx/rwx-nginx-deployment.yaml](https://github.com/longhorn/longhorn/blob/master/examples/rwx/rwx-nginx-deployment.yaml) ) with the custom storage class.  

**Then** Turn off the node where share-manager is running.

**Verify** The share-manager pod is recreated on a different node.  
    - The other active clients should not run into stale handle errors after the failover.  
    - New share-manager pod is created in under 20 seconds.  
    - Outage, including grace period, should be less than 60 seconds.  

**Repeat** Using a different storage class with soft NFS mount

```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: longhorn-test-soft
provisioner: driver.longhorn.io
allowVolumeExpansion: true
reclaimPolicy: Delete
volumeBindingMode: Immediate
parameters:
  numberOfReplicas: "3"
  staleReplicaTimeout: "2880"
  fromBackup: ""
  fsType: "ext4"
  nfsOptions: "soft,timeo=250,retrans=5"
```

**Repeat** The mount option cases with `Automatically Delete Workload Pod when The Volume Is Detached Unexpectedly` disabled.

## Test Resource Usage

**Given** Longhorn cluster with 3 worker nodes.

**And** Default Longhorn storage class (including normal mount options.  Results should be independent of mount options.)

**And** `Enable RWX Fast Failover` set to true.  `Automatically Delete Workload Pod when The Volume Is Detached Unexpectedly` also set to true.

Make multiple deployments with a script such as
```shell
#!/bin/bash

for i in {1..60}; do
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rwx-volume-pvc-$i
  namespace: default
spec:
  accessModes:
    - ReadWriteMany
  volumeMode: Filesystem
  storageClassName: longhorn-test
  resources:
    requests:
      storage: 200Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-$i
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app-$i
  template:
    metadata:
      labels:
        app: app-$i
    spec:
      containers:
      - name: app
        image: busybox
        command: ["/bin/sh", "-c", "exec 7<>/data/testfile-$(hostname -s); flock -x 7; while date | dd conv=fsync >&7 ; do sleep 1; done"]
        volumeMounts:
        - mountPath: /data
          name: rwx-volume-pvc-$i
      volumes:
      - name: rwx-volume-pvc-$i
        persistentVolumeClaim:
          claimName: rwx-volume-pvc-$i
EOF
done
```

**Then** with the `rwx-enable-fast-failover` setting off, check the CPU and memory use totals for longhorn-manager and longhorn-share-manager pods, using something like `kubectl -n longhorn-system top pod`.  Establish baseline values.

**Then** set `rwx-enable-fast-failover` to true, and scale down and up the deployments so that they will start updating and monitoring the leases.

**Verify** that the CPU and memory use grows, but only by a small amount.

Here is the expected outcome:

| **Metric**                           | **Fast Failover Enabled** | **Fast Failover Disabled** | **Difference**             |
|--------------------------------------|---------------------------|----------------------------|----------------------------|
| **1. Number of API Requests**        | 59 req/s                  | 37.5 req/s                 | **+57.3%**                 |
| **2. RPC Rate**                      | 57 ops/s                  | 37 ops/s                   | **+54.1%**                 |
| **3. Memory Usage**                  | Higher Peaks/Minima       | Lower Peaks/Minima         | More usage with Fast Failover Enabled |
| **4. Longhorn Manager CPU/RAM**      | 417MB / 0.13 CPU          | 405MB / 0.1 CPU            | **+3% RAM** / **+30% CPU** |
| **5. Share Manager CPU/RAM**         | 2.25GB / 0.26 CPU         | 2.2GB / 0.235 CPU          | **+2.3% RAM** / **+10.6% CPU** |

Ref. https://github.com/longhorn/longhorn/issues/6205#issuecomment-2262625965

If newer Longhorn version consume more resources than that, then the test is considered as failed

**If possible** monitor the API server requests similar to the method in the report https://github.com/longhorn/longhorn/blob/master/scalability/reference-setup-performance-scalability-and-sizing-guidelines/public-cloud/medium-node-spec.md#longhorn-control-plane-performance

**Verify** that the API request rate remains low.

**Reference** How to set up a Grafana Testing Environment on Rancher
https://github.com/longhorn/longhorn/issues/6205#issuecomment-2264430975

## Test Multiple Simultaneous Failovers.
**Given** Longhorn cluster with 3 worker nodes.

**With** the same deployments as in `Test Resource Usage` (but perhaps only 20-30 of them), and fast failover enabled,
    
**Then** pick a node and restart it.  

**Verify** the share-managers on that node are recreated one of the remaining nodes.  
    - Every RWX volume with share-manager pods on the failed node are relocated to another node.  I/O can resume on its own after the shortened grace period.  
    - RWX volumes with share-manager pods not on the failed node should continue to operate without any disruption.

