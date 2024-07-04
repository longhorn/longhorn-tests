---
title: Node Disk Support
---

Longhorn now enhances filesystem operations, storage performance, and compatibility by supporting the addition and management of various disk types on nodes, including `AIO`, `NVMe`, and `VirtIO`.

## Related issues

- https://github.com/longhorn/longhorn/issues/7672

## Precondition

- https://longhorn.io/docs/1.7.0/v2-data-engine/quick-start/#prerequisites

## Test the detection of `NVMe` disk

**When** Create a LH clusters using AWS EC2 `c5d.2xlarge` instance with a `NVMe` disk
**And** Check available block devices on a system by `lsblk` or `fdisk -l`
```bash
# lsblk
NAME         MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS
loop0          7:0    0  55.7M  1 loop /snap/core18/2812
loop1          7:1    0  25.2M  1 loop /snap/amazon-ssm-agent/7983
loop2          7:2    0  38.7M  1 loop /snap/snapd/21465
loop3          7:3    0    20G  0 loop 
nvme1n1      259:0    0 186.3G  0 disk 
nvme0n1      259:1    0   100G  0 disk 
├─nvme0n1p1  259:2    0    99G  0 part /
├─nvme0n1p14 259:3    0     4M  0 part 
├─nvme0n1p15 259:4    0   106M  0 part /boot/efi
└─nvme0n1p16 259:5    0   913M  0 part /boot
```
**And** Enable `v2 data engine`
**And** Get the BDF of the disk by `ls -al /sys/block`. 
```bsah
# ls -al /sys/block/
lrwxrwxrwx  1 root root 0 Jul  1 07:07 loop7 -> ../devices/virtual/block/loop7
lrwxrwxrwx  1 root root 0 Jul  1 07:07 nvme0n1 -> ../devices/pci0000:00/0000:00:04.0/nvme/nvme0/nvme0n1
lrwxrwxrwx  1 root root 0 Jul  1 07:07 nvme1n1 -> ../devices/pci0000:00/0000:00:1f.0/nvme/nvme1/nvme1n1
```
**Then** Add the disk to `node.spec.disks`
```yaml
    disk-9:
      allowScheduling: true
      diskDriver: auto
      diskType: block
      evictionRequested: false
      path: 0000:00:1f.0
      storageReserved: 0
      tags: []
```
**And** Check the `node.status.diskStatus`. The disk is detected without any error, and the `diskDriver` is `nvme`.
```yaml
      disk-9:
        conditions:
        - lastProbeTime: ""
          lastTransitionTime: "2024-07-02T09:00:32Z"
          message: Disk disk-9(0000:00:1f.0) on node ryao-master-w3-2e5975a5-88vmf
            is ready
          reason: ""
          status: "True"
          type: Ready
        - lastProbeTime: ""
          lastTransitionTime: "2024-07-02T09:00:32Z"
          message: Disk disk-9(0000:00:1f.0) on node ryao-master-w3-2e5975a5-88vmf
            is schedulable
          reason: ""
          status: "True"
          type: Schedulable
        diskDriver: nvme
        diskName: disk-3n1
        diskPath: 0000:00:1f.0
        diskType: block
        diskUUID: eae57130-dacb-4868-92b8-58d74b1382f8
        filesystemType: ""
        instanceManagerName: instance-manager-70555e5a4cb268c931ccebb4751e78a7
        scheduledReplica: {}
        storageAvailable: 199124582400
        storageMaximum: 199216857088
        storageScheduled: 0
```

## Test the detection of `VirtIO` disk

**When** Create a LH clusters using `QEMU` vm machines with two `VirtiIO` disk.
**And** Check available block devices on a system by `lsblk` or `fdisk -l`
```bash
# lsblk 
vda                 252:0    0    50G  0 disk 
├─vda1              252:1    0     1M  0 part 
├─vda2              252:2    0     2G  0 part /boot
└─vda3              252:3    0    48G  0 part 
  └─ubuntu--vg-ubuntu--lv
                    253:0    0    48G  0 lvm  /var/lib/kubelet/pods/e864c8e7-c552-4082-9788-158e0937625d/volume-subpaths/admin-kubeconfig/proxy/0
                                              /var/lib/kubelet/pods/e864c8e7-c552-4082-9788-158e0937625d/  volume-subpaths/user-kubeconfig/helm/1
                                              /
vdb                 252:16   0    20G  0 disk
```

**And** Enable `v2 data engine`
**And** Get the BDF of the disk by `ls -al /sys/block`. 
```bsah
lrwxrwxrwx  1 root root 0 Jun 28  2024 vda -> ../devices/pci0000:00/0000:00:02.4/0000:05:00.0/virtio3/block/vda
lrwxrwxrwx  1 root root 0 Jun 28  2024 vdb -> ../devices/pci0000:00/0000:00:02.5/0000:06:00.0/virtio4/block/vdb
```
**Then** Add the disk to `node.spec.disks`
```yaml
    disk-2:
      allowScheduling: true
      diskDriver: auto
      diskType: block
      evictionRequested: false
      path: 0000:06:00.0
      storageReserved: 0
      tags: []
```
**And** Check the `node.status.diskStatus`. The disk is detected without any error, and the `diskDriver` is `virtio-blk`.
```yaml
    disk-2:
      conditions:
      - lastProbeTime: ""
        lastTransitionTime: "2024-07-02T10:30:10Z"
        message: Disk disk-2(0000:06:00.0) on node w2 is ready
        reason: ""
        status: "True"
        type: Ready
      - lastProbeTime: ""
        lastTransitionTime: "2024-07-02T10:30:10Z"
        message: Disk disk-2(0000:06:00.0) on node w2 is schedulable
        reason: ""
        status: "True"
        type: Schedulable
      diskDriver: virtio-blk
      diskName: disk-2
      diskPath: "0000:06:00.0"
      diskType: block
      diskUUID: 2ff33ec9-040a-4888-bb10-e777eeaa45d6
      filesystemType: ""
      instanceManagerName: instance-manager-90ba8efa65287c9ab398d99db79cd6de
      scheduledReplica:
        vol-0-r-ae05dad3: 2147483648
      storageAvailable: 21181235200
      storageMaximum: 21389901824
      storageScheduled: 2147483648
```

## Test disk driver `aio`

**When** [Add block-type Disks in Longhorn Nodes](https://longhorn.io/docs/1.7.0/v2-data-engine/quick-start/#add-block-type-disks-in-longhorn-nodes).
**Then** Add the disk to `node.spec.disks`
```yaml
    disk-8:
      allowScheduling: true
      diskDriver: auto
      diskType: /dev/loop3
      evictionRequested: false
      path: 0000:06:00.0
      storageReserved: 0
      tags: []
```
**And** Check the `node.status.diskStatus`. The disk is detected without any error, and the `diskDriver` is `aio`.
```yaml
     disk-8:
        conditions:
        - lastProbeTime: ""
          lastTransitionTime: "2024-07-02T08:55:32Z"
          message: Disk disk-8(/dev/loop3) on node ryao-master-w3-2e5975a5-88vmf is
            ready
          reason: ""
          status: "True"
          type: Ready
        - lastProbeTime: ""
          lastTransitionTime: "2024-07-02T08:55:32Z"
          message: Disk disk-8(/dev/loop3) on node ryao-master-w3-2e5975a5-88vmf is
            schedulable
          reason: ""
          status: "True"
          type: Schedulable
        diskDriver: aio
        diskName: disk-8
        diskPath: /dev/loop3
        diskType: block
        diskUUID: 1e995e68-512b-4e16-9c39-9b7323587bcf
        filesystemType: ""
        instanceManagerName: instance-manager-70555e5a4cb268c931ccebb4751e78a7
        scheduledReplica: {}
        storageAvailable: 21286092800
        storageMaximum: 21389901824
        storageScheduled: 0
```