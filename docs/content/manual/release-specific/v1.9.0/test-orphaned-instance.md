---
title: Test Orphaned Instance Handling
---

## Related issue
https://github.com/longhorn/longhorn/issues/6764

## Test Orphan Auto Cleanup Settings Replacement

**Given** A cluster with Longhorn v1.8.x ready

**And** Enable orphaned replica data auto deletion
```bash
$ kubectl -n longhorn-system edit settings.longhorn.io orphan-auto-deletion
```
And set the value to `true`

**When** Upgrade to Longhorn v1.9.0

**Then** The new setting `orphan-resource-auto-deletion` is initialized with replica data enabled
```bash
$ kubectl -n longhorn-system get settings.longhorn.io orphan-resource-auto-deletion -o jsonpath='{.value}'

replicaData
```

**And** The old setting `orphan-auto-deletion` is removed
```bash
$ kubectl -n longhorn-system get settings.longhorn.io orphan-auto-deletion

Error from server (NotFound): settings.longhorn.io "orphan-auto-deletion" not found
```


## Test Orphaned Instance Detection

**Given** A cluster with Longhorn v1.9.0 ready

**And** The orphan auto deletion is disabled for all kinds of orphans
```bash
$ kubectl -n longhorn-system get settings.longhorn.io orphan-resource-auto-deletion

NAME                            VALUE   AGE
orphan-resource-auto-deletion           2d1h
```
The value should be empty.

**When** Create an orphaned engine instance
1. Shell into an instance manager pod
2. Create an engine process using any available engine binary
   ```bash
   $ instance-manager process create \
       --name orphan-engine-01-e-0 \
       --binary /engine-binaries/longhornio-longhorn-engine-v1.8.1/longhorn \
       -- \
         --engine-instance-name orphan-engine-01-e-0 \
         controller orphan-engine-01-e-0 \
         --frontend tgt-blockdev \
         --disableRevCounter \
         --size 10485760 \
         --current-size 10485760
   ```
3. Confirm the instance is listed in instance manager CR's `status.instanceEgnines`. State does not matter.

**And** Create an orphaned replica instance
1. Shell into an instance manager pod
2. Create a replica process using any available engine binary
   ```bash
   $ mkdir -p /host/var/lib/longhorn/replicas/orphan-replica-01-r-0
   $ instance-manager process create \
       --name orphan-replica-01-r-0 \
       --binary /engine-binaries/longhornio-longhorn-engine-v1.8.1/longhorn \
       -- \
         --volume-name orphan-test-01 \
         replica \
         /host/var/lib/longhorn/replicas/orphan-replica-01-r-0
   ```
3. Confirm the instance is listed in instance manager CR's `status.instanceReplicas`. State does not matter.

**Then** The `engine-instance` and `replica-instance` orphan CRs are created
```bash
$ kubectl -n longhorn-system get orphan -l "longhorn.io/orphan-type in (engine-instance,replica-instance)"

NAME                                                                      TYPE               NODE
orphan-d09e9176343f60b2aad39683b1781fd1d9bb29e3e986e36bc9f65d43d91db764   replica-instance   libvirt-ubuntu-k3s-worker1
orphan-e3b484438aab83100726528c226b09990e9a0b2d0730f2f3489d14242175f9ca   engine-instance    libvirt-ubuntu-k3s-worker1
```

**And** The spec of engine orphan CR matches the engine instance
```bash
$ kubectl -n longhorn-system describe orphan orphan-e3b484438aab83100726528c226b09990e9a0b2d0730f2f3489d14242175f9ca

Name:         orphan-e3b484438aab83100726528c226b09990e9a0b2d0730f2f3489d14242175f9ca
Kind:         Orphan
Spec:
  Data Engine:  v1
  Node ID:      <instance node ID>
  Orphan Type:  engine-instance
  Parameters:
    Instance Manager:  <instance manager ID>
    Instance Name:     orphan-engine-01-e-0
...
```

- `Name`: `orphan-<sha256>`
- `Spec.OrphanType`: `engine-instance`
- `Spec.NodeID`: instance's node ID
- `Spec.DataEngine`: instance's engine type, `v1` or `v2`
- `Spec.Parameters.InstanceName`: instance's name
- `Spec.Parameters.InstanceManager`: instance manager ID

**And** The spec of replica orphan CR matches the replica instance
```bash
$ kubectl -n longhorn-system describe orphan orphan-d09e9176343f60b2aad39683b1781fd1d9bb29e3e986e36bc9f65d43d91db764

Name:         orphan-d09e9176343f60b2aad39683b1781fd1d9bb29e3e986e36bc9f65d43d91db764
Spec:
  Data Engine:  v1
  Node ID:      <instance node ID>
  Orphan Type:  replica-instance
  Parameters:
    Instance Manager:  <instance manager ID>
    Instance Name:     orphan-replica-01-r-0
...
```

- `Name`: `orphan-<sha256>`
- `Spec.OrphanType`: `replica-instance`
- `Spec.NodeID`: instance's node ID
- `Spec.DataEngine`: instance's engine type, `v1` or `v2`
- `Spec.Parameters.InstanceName`: instance's name
- `Spec.Parameters.InstanceManager`: instance manager ID

**When** Delete the instance orphans
```bash
$ kubectl -n longhorn-system delete orphan -l "longhorn.io/orphan-type in (engine-instance,replica-instance)"

orphan.longhorn.io "orphan-d09e9176343f60b2aad39683b1781fd1d9bb29e3e986e36bc9f65d43d91db764" deleted
orphan.longhorn.io "orphan-e3b484438aab83100726528c226b09990e9a0b2d0730f2f3489d14242175f9ca" deleted
```

**Then** The instances are cleanup from the instance manager
```bash
$ kubectl -n longhorn-system describe instancemanager <instance manager ID>
```
And the orphaned instances are removed from `Status.InstanceEngines` and `Status.InstanceReplicas`.


## Test Orphaned Instance Auto Detection

**Given** A cluster with Longhorn v1.9.0 ready

**And** The orphan auto deletion is disabled for all kinds of orphans
```bash
$ kubectl -n longhorn-system get settings.longhorn.io orphan-resource-auto-deletion

NAME                            VALUE   AGE
orphan-resource-auto-deletion           2d1h
```
The value should be empty.

**And** Create an orphaned engine and replica instance
1. Shell into an instance manager pod
2. Create engine and replica processes using any available engine binary
   ```bash
   $ instance-manager process create \
       --name orphan-engine-01-e-0 \
       --binary /engine-binaries/longhornio-longhorn-engine-v1.8.1/longhorn \
       -- \
         --engine-instance-name orphan-engine-01-e-0 \
         controller orphan-engine-01-e-0 \
         --frontend tgt-blockdev \
         --disableRevCounter \
         --size 10485760 \
         --current-size 10485760

   $ mkdir -p /host/var/lib/longhorn/replicas/orphan-replica-01-r-0
   $ instance-manager process create \
       --name orphan-replica-01-r-0 \
       --binary /engine-binaries/longhornio-longhorn-engine-v1.8.1/longhorn \
       -- \
         --volume-name orphan-test-01 \
         replica \
         /host/var/lib/longhorn/replicas/orphan-replica-01-r-0
   ```
   
**And** The `engine-instance` and `replica-instance` orphan CRs are created
```bash
$ kubectl -n longhorn-system get orphan -l "longhorn.io/orphan-type in (engine-instance,replica-instance)"

NAME                                                                      TYPE               NODE
orphan-d09e9176343f60b2aad39683b1781fd1d9bb29e3e986e36bc9f65d43d91db764   replica-instance   libvirt-ubuntu-k3s-worker1
orphan-e3b484438aab83100726528c226b09990e9a0b2d0730f2f3489d14242175f9ca   engine-instance    libvirt-ubuntu-k3s-worker1
```

**When** Enable orphan auto deletion for engine and replica instances
```bash
$ kubectl -n longhorn-system edit settings.longhorn.io orphan-resource-auto-deletion
```
Set the value to `engineInstance;replicaInstance`

**Then** The orphans should be deleted in 90 seconds
```bash
$ kubectl -n longhorn-system get orphan

No resources found in longhorn-system namespace.
```

**When** Create orphan instances again on any node
1. Shell into an instance manager pod
2. Create engine and replica processes using any available engine binary
   ```bash
   $ instance-manager process create \
       --name orphan-engine-01-e-0 \
       --binary /engine-binaries/longhornio-longhorn-engine-v1.8.1/longhorn \
       -- \
         --engine-instance-name orphan-engine-01-e-0 \
         controller orphan-engine-01-e-0 \
         --frontend tgt-blockdev \
         --disableRevCounter \
         --size 10485760 \
         --current-size 10485760

   $ mkdir -p /host/var/lib/longhorn/replicas/orphan-replica-01-r-0
   $ instance-manager process create \
       --name orphan-replica-01-r-0 \
       --binary /engine-binaries/longhornio-longhorn-engine-v1.8.1/longhorn \
       -- \
         --volume-name orphan-test-01 \
         replica \
         /host/var/lib/longhorn/replicas/orphan-replica-01-r-0
   ```

**Then** The orphaned instances should be deleted automatically in 90 seconds
```bash
$ kubectl -n longhorn-system describe instancemanager <instance manager ID>
```
And the orphaned instances are removed from `Status.InstanceEngines` and `Status.InstanceReplicas`.

**And** No `engine-instance` or `replica-instance` orphan CR exists
```bash
$ kubectl -n longhorn-system get orphan -l "longhorn.io/orphan-type in (engine-instance,replica-instance)"

No resources found in longhorn-system namespace.
```



## Test Orphan Deletion When Evicting Node

**Given** A cluster with Longhorn v1.9.0 ready

**And** The orphan auto deletion is disabled for all kinds of orphans
```bash
$ kubectl -n longhorn-system get settings.longhorn.io orphan-resource-auto-deletion

NAME                            VALUE   AGE
orphan-resource-auto-deletion           2d1h
```
The value should be empty.

**And** Create an orphaned engine instance
1. Shell into an instance manager pod
2. Create an engine process using any available engine binary
   ```bash
   $ instance-manager process create \
       --name orphan-engine-01-e-0 \
       --binary /engine-binaries/longhornio-longhorn-engine-v1.8.1/longhorn \
       -- \
         --engine-instance-name orphan-engine-01-e-0 \
         controller orphan-engine-01-e-0 \
         --frontend tgt-blockdev \
         --disableRevCounter \
         --size 10485760 \
         --current-size 10485760
   ```
3. Confirm the instance is listed in instance manager CR's `status.instanceEngines`. State does not matter.

**When** Evict the orphaned engine's node
```bash
$ kubectl -n longhorn-system edit lhn <node>
```
- Disable `spec.allowScheduling`
- Enable `spec.evictionRequested`

**And** Orphaned engine should be deleted in 90 seconds
```bash
$ kubectl -n longhorn-system get orphan -l "longhornnode=<node>"

No resources found in longhorn-system namespace.
```

**Finally** Cancel node eviction
```bash
$ kubectl -n longhorn-system edit lhn <node>
```
- Enable `spec.allowScheduling`
- Disable `spec.evictionRequested`


## Test Orphan Instance CR Is Tracking Node Status

**Given** A 3-node cluster, includes one control-plane and two worker nodes

**And** Longhorn v1.9.0 is installed and ready

**And** The orphan auto deletion is disabled for all kinds of orphans
```bash
$ kubectl -n longhorn-system get settings.longhorn.io orphan-resource-auto-deletion

NAME                            VALUE   AGE
orphan-resource-auto-deletion           2d1h
```
The value should be empty

**And** Create a workload with a volume
```bash
kubectl apply -f - <<YAML
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: longhorn-6764-single-replica
provisioner: driver.longhorn.io
parameters:
  dataEngine: v1
  numberOfReplicas: "2"
  dataLocality: "best-effort"
  staleReplicaTimeout: "2800"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: longhorn-6764-single-replica
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 5Mi
  storageClassName: longhorn-6764-single-replica
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-workload
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx-state-rwo
  template:
    metadata:
      labels:
        app: nginx-state-rwo
    spec:
      restartPolicy: Always
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: node-role.kubernetes.io/control-plane
                operator: DoesNotExist
      terminationGracePeriodSeconds: 10
      containers:
      - name: nginx-state-rwo
        image: nginx:stable
        ports:
        - containerPort: 80
          name: web-state-rwo
        volumeMounts:
        - name: www
          mountPath: /usr/share/nginx/html
      volumes:
        - name: www
          persistentVolumeClaim:
            claimName: longhorn-6764-single-replica
YAML
```

**And** Wait for volume ready
- The worker node of the engine is annotated as node A in the following steps.
- Another worker node is annotated as node B in the following steps.

**And** Suspend node A to simulate network outage

**And** Wait for volume resume
- The engine should be running on node B
  ```bash
  $ kubectl -n longhorn-system get engine
  
  NAME                                           DATA ENGINE   STATE     NODE
  pvc-8bde632f-8a67-44d9-8286-b5de62ad6b8c-e-0   v1            running   <node B>
  ```

**And** Resume node A to simulate network recover

**And** The engine instance on node A is orphaned
```bash
$ kubectl -n longhorn-system get orphan -l "longhornnode=<node A>"

NAME                                                                      TYPE              NODE
orphan-e3b484438aab83100726528c226b09990e9a0b2d0730f2f3489d14242175f9ca   engine-instance   <node A>
```

**When** Reschedule the engine back to node A
```bash
$ kubectl -n longhorn-system edit <engine ID>
```
And set the `spec.nodeID` to node A. This may leave an orphan on node B.

**Then** The orphan CR of this engine instance on node A is deleted in 90 seconds
```bash
$ kubectl -n longhorn-system get orphan -l "longhornnode=<node A>"

No resources found in longhorn-system namespace.
```

**Finally** Resume all nodes, and delete the workload, the volume, any rest orphan CRs, and the storage class
