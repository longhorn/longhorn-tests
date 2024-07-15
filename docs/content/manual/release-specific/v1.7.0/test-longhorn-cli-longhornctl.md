---
title: Longhorn Commandline Interface (longhornctl)
---

## Related issues

- https://github.com/longhorn/longhorn/issues/7927

## Test install preflight

**Given** `longhornctl` binary.  
**And** `longhornctl` image.

**When** Execute `longhornctl install preflight`.
```shell
> ./bin/longhornctl -l debug --image="c3y1huang/research:longhornctl-407" install preflight
```

**Then** Command should succeed.
```log
INFO[2024-06-24T10:23:16+08:00] Completed preflight installer. Use 'longhornctl check preflight' to check the result.
```

## Test check preflight

**Given** `longhornctl` binary.  
**And** `longhornctl` image.

**When** Execute `longhornctl check preflight`.
```shell
> ./bin/longhornctl -l debug --image="c3y1huang/research:longhornctl-407" check preflight
```

**Then** Command should show result.
```log
INFO[2024-06-24T10:24:54+08:00] Retrieved preflight checker result:
ip-10-0-2-106:
  info:
  - Service iscsid is running
  - NFS4 is supported
  - Package nfs-client is installed
  - Package open-iscsi is installed
  - CPU instruction set sse4_2 is supported
  - HugePages is enabled
  - Module nvme_tcp is loaded
  - Module uio_pci_generic is loaded
ip-10-0-2-181:
  info:
  - Service iscsid is running
  - NFS4 is supported
  - Package nfs-client is installed
  - Package open-iscsi is installed
  - CPU instruction set sse4_2 is supported
  - HugePages is enabled
  - Module nvme_tcp is loaded
  - Module uio_pci_generic is loaded
ip-10-0-2-219:
  info:
  - Service iscsid is running
  - NFS4 is supported
  - Package nfs-client is installed
  - Package open-iscsi is installed
  - CPU instruction set sse4_2 is supported
  - HugePages is enabled
  - Module nvme_tcp is loaded
  - Module uio_pci_generic is loaded
```
**And** Command should succeed.
```log
INFO[2024-06-24T10:24:54+08:00] Completed preflight checker
```

## Test get replica

**Given** `longhornctl` binary.  
**And** `longhornctl` image.  
**And** A workload using Longhorn volume created.

**When** Execute `longhornctl get replica`.
```shell
> ./bin/longhornctl -l debug --image="c3y1huang/research:longhornctl-407" get replica
```

**Then** Command should show result of the replicas exist on host data directory.
```log
INFO[2024-06-24T10:30:00+08:00] Retrieved replica information:
 replicas:
    pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404-7e619574:
        - node: ip-10-0-2-219
          directory: /var/lib/longhorn/replicas/pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404-7e619574
          isInUse: true
          volumeName: pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404
          metadata:
            size: 10737418240
            head: volume-head-000.img
            dirty: true
            rebuilding: false
            error: ""
            parent: ""
            sectorsize: 512
            backingfilepath: ""
            backingfile: null
    pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404-0701e558:
        - node: ip-10-0-2-106
          directory: /var/lib/longhorn/replicas/pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404-0701e558
          isInUse: true
          volumeName: pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404
          metadata:
            size: 10737418240
            head: volume-head-000.img
            dirty: true
            rebuilding: false
            error: ""
            parent: ""
            sectorsize: 512
            backingfilepath: ""
            backingfile: null
    pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404-cf997f83:
        - node: ip-10-0-2-181
          directory: /var/lib/longhorn/replicas/pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404-cf997f83
          isInUse: true
          volumeName: pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404
          metadata:
            size: 10737418240
            head: volume-head-000.img
            dirty: true
            rebuilding: false
            error: ""
            parent: ""
            sectorsize: 512
            backingfilepath: ""
            backingfile: null
```
**And** Command should succeed.
```log
INFO[2024-06-24T10:24:54+08:00] Completed preflight checker
```

## Test Export And Unexport Replica

**Given** `longhornctl` binary.  
**And** `longhornctl` image.  
**And** A workload using Longhorn volume created.  
**And** Workload volume is detached.  
**And** Run `longhornctl get replica` and pick a replica name.

**When** Run `longhornctl export replica`.
```shell
> ./bin/longhornctl -l trace --image="c3y1huang/research:longhornctl-407" export replica --name pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404-cf997f83 --target-dir=/tmp/export 
```
**Then** Command should show result.
```log
INFO[2024-06-24T10:37:45+08:00] Exported replica:
 volumes:
    pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404:
        - replicas:
            - node: ip-10-0-2-181
              exportedDirectory: /tmp/export/pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404
```

**And** Command should succeed.
```log
INFO[2024-06-24T10:37:45+08:00] Completed replica exporter. Use 'longhornctl export replica stop' to stop exporting replica.
```

**And** Replia should be exported to the target directory on the cluster node.
```shell
ec2-user@ip-10-0-2-181:~> ls /tmp/export/pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404
lost+found
```

**When** Run `longhornctl export replica stop`.
```shell
> ./bin/longhornctl -l trace --image="c3y1huang/research:longhornctl-407" export replica --name pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404-cf997f83 --target-dir=/tmp/export stop
```

**Then** Command should succeed.
```log
INFO[2024-06-24T10:42:04+08:00] Successfully stopped exporting replica
```

**And** Replica should not exported to the target directory on the cluster node.
```shell
ec2-user@ip-10-0-2-181:~> ls /tmp/export/pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404
ls: cannot access '/tmp/export/pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404': No such file or directory
```


## Test trim volume

**Given** `longhornctl` binary.  
**And** `longhornctl` image.  
**And** A workload using Longhorn volume created.
```shell
> kubectl get pod
NAME     READY   STATUS    RESTARTS   AGE
demo-0   1/1     Running   0          2m5s

> kubectl -n longhorn-system get volume -o yaml | grep actual
    actualSize: 239325184
```
**And** Add some data to the workload volume.
```shell
> kubectl exec -it demo-0 -- sh -c "dd if=/dev/random of=/data/random bs=1M count=50"
50+0 records in
50+0 records out
52428800 bytes (50.0MB) copied, 0.263925 seconds, 189.4MB/s

> kubectl -n longhorn-system get volume -o yaml | grep actual
    actualSize: 291758080
```
**And** Delete the data created on the workload volume.
```shell
> kubectl exec -it demo-0 -- sh -c "rm /data/random"

> kubectl -n longhorn-system get volume -o yaml | grep actual
    actualSize: 291758080
```

**When** Run `longhornctl trim volume`.
```shell
> k -n longhorn-system get volume
NAME                                       DATA ENGINE   STATE      ROBUSTNESS   SCHEDULED   SIZE          NODE            AGE
pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404   v1            attached   healthy                  10737418240   ip-10-0-2-106   20m

> ./bin/longhornctl -l trace --image="c3y1huang/research:longhornctl-407" trim volume --name="pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404"
```

**Then** Command should succeed.
```log
INFO[2024-06-24T10:49:02+08:00] Completed volume trimmer                      volume=pvc-0c02aef8-3324-4ad9-95c7-0dcf2482e404
```
**And** Workload volume should be trimmed.
```shell
> kubectl -n longhorn-system get volume -o yaml | grep actual
    actualSize: 239255552
```


