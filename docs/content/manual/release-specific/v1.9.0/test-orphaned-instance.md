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

**And** Create orphaned engine and replica instances
1. Create a volume
2. Attach the volume to a node
3. There is an engine running on given node
    ```bash
    $ kubectl -n longhorn-system get engine -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME         DATA ENGINE   STATE     NODE                         INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-e-0   v1            running   libvirt-ubuntu-k3s-worker1   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
4. There is a replica running on given node
    ```bash
    $ kubectl -n longhorn-system get replica -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME                DATA ENGINE   STATE     NODE                         DISK                                   INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-r-e7106826   v1            running   libvirt-ubuntu-k3s-worker1   a6338052-9852-4c59-b878-bfc4db32b00e   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
5. Suspend the node to simulate the temporary network outage
6. Wait for the node unavailable
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   False   true              True          26h
    ```
7. Detach and delete the volume
8. Resume the node to simulate the network resume
9. Wait for the node ready
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   True    true              True          26h
    ```

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

**And** Create orphaned engine and replica instances
1. Create a volume
2. Attach the volume to a node
3. There is an engine running on given node
    ```bash
    $ kubectl -n longhorn-system get engine -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME         DATA ENGINE   STATE     NODE                         INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-e-0   v1            running   libvirt-ubuntu-k3s-worker1   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
4. There is a replica running on given node
    ```bash
    $ kubectl -n longhorn-system get replica -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME                DATA ENGINE   STATE     NODE                         DISK                                   INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-r-e7106826   v1            running   libvirt-ubuntu-k3s-worker1   a6338052-9852-4c59-b878-bfc4db32b00e   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
5. Suspend the node to simulate the temporary network outage
6. Wait for the node unavailable
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   False   true              True          26h
    ```
7. Detach and delete the volume
8. Resume the node to simulate the network resume
9. Wait for the node ready
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   True    true              True          26h
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
Set the value to `instance`

**Then** The orphans should be deleted in 90 seconds
```bash
$ kubectl -n longhorn-system get orphan

No resources found in longhorn-system namespace.
```

**When** Create orphaned engine and replica instances again
1. Create a volume
2. Attach the volume to a node
3. There is an engine running on given node
    ```bash
    $ kubectl -n longhorn-system get engine -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME         DATA ENGINE   STATE     NODE                         INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-e-0   v1            running   libvirt-ubuntu-k3s-worker1   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
4. There is a replica running on given node
    ```bash
    $ kubectl -n longhorn-system get replica -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME                DATA ENGINE   STATE     NODE                         DISK                                   INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-r-e7106826   v1            running   libvirt-ubuntu-k3s-worker1   a6338052-9852-4c59-b878-bfc4db32b00e   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
5. Suspend the node to simulate the temporary network outage
6. Wait for the node unavailable
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   False   true              True          26h
    ```
7. Detach and delete the volume
8. Resume the node to simulate the network resume
9. Wait for the node ready
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   True    true              True          26h
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

**And** Create orphaned engine and replica instances again
1. Create a volume
2. Attach the volume to a node
3. There is an engine running on given node
    ```bash
    $ kubectl -n longhorn-system get engine -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME         DATA ENGINE   STATE     NODE                         INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-e-0   v1            running   libvirt-ubuntu-k3s-worker1   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
4. There is a replica running on given node
    ```bash
    $ kubectl -n longhorn-system get replica -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME                DATA ENGINE   STATE     NODE                         DISK                                   INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-r-e7106826   v1            running   libvirt-ubuntu-k3s-worker1   a6338052-9852-4c59-b878-bfc4db32b00e   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
5. Suspend the node to simulate the temporary network outage
6. Wait for the node unavailable
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   False   true              True          26h
    ```
7. Detach and delete the volume
8. Resume the node to simulate the network resume
9. Wait for the node ready
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   True    true              True          26h
    ```

**When** Evict the orphaned instances' node
```bash
$ kubectl -n longhorn-system edit lhn <node>
```
- Disable `spec.allowScheduling`
- Enable `spec.evictionRequested`

**And** Orphaned engine and replica should be deleted in 90 seconds
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

**Given** A cluster with Longhorn v1.9.0 ready

**And** The orphan auto deletion is disabled for all kinds of orphans
```bash
$ kubectl -n longhorn-system get settings.longhorn.io orphan-resource-auto-deletion

NAME                            VALUE   AGE
orphan-resource-auto-deletion           2d1h
```
The value should be empty.

**And** Create orphaned engine and replica instances again
1. Create a volume
2. Attach the volume to a node
3. There is an engine running on given node
    ```bash
    $ kubectl -n longhorn-system get engine -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME         DATA ENGINE   STATE     NODE                         INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-e-0   v1            running   libvirt-ubuntu-k3s-worker1   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
4. There is a replica running on given node
    ```bash
    $ kubectl -n longhorn-system get replica -l "longhornnode=libvirt-ubuntu-k3s-worker1"
    
    NAME                DATA ENGINE   STATE     NODE                         DISK                                   INSTANCEMANAGER                                     IMAGE                               AGE
    vol-01-r-e7106826   v1            running   libvirt-ubuntu-k3s-worker1   a6338052-9852-4c59-b878-bfc4db32b00e   instance-manager-b87f10b867cec1dca2b814f5e78bcc90   longhornio/longhorn-engine:v1.9.0   24m
    ```
5. Suspend the node to simulate the temporary network outage
6. Wait for the node unavailable
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   False   true              True          26h
    ```
7. Detach and delete the volume
8. Resume the node to simulate the network resume
9. Wait for the node ready
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   True    true              True          26h
    ```

**And** The `engine-instance` and `replica-instance` orphan CRs are created
```bash
$ kubectl -n longhorn-system get orphan -l "longhorn.io/orphan-type in (engine-instance,replica-instance)"

NAME                                                                      TYPE               NODE
orphan-d09e9176343f60b2aad39683b1781fd1d9bb29e3e986e36bc9f65d43d91db764   replica-instance   libvirt-ubuntu-k3s-worker1
orphan-e3b484438aab83100726528c226b09990e9a0b2d0730f2f3489d14242175f9ca   engine-instance    libvirt-ubuntu-k3s-worker1
```

**When** The orphaned instances' node disconnects from the cluster
1. Suspend the node to simulate the temporary network outage
2. Wait for the node unavailable
    ```bash
    $ kubectl -n longhorn-system get lhn libvirt-ubuntu-k3s-worker1
    
    NAME                         READY   ALLOWSCHEDULING   SCHEDULABLE   AGE
    libvirt-ubuntu-k3s-worker1   False   true              True          26h
    ```

**Then** All orphans are removed from the cluster
```bash
$ kubectl -n longhorn-system get orphan -l "longhorn.io/orphan-type in (engine-instance,replica-instance)"

No resources found in longhorn-system namespace.
```

**Finally** Resume all nodes, and delete the workload, the volume, and any rest orphan CRs
