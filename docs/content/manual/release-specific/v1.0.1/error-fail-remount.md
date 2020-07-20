---
title: Return an error when fail to remount a volume
---
### Case 1: Volume with a corrupted filesystem try to remount
Steps to reproduce bug:

1. Create a volume of size 1GB, say `terminate-immediatly` volume.
2. Create PV/PVC from the volume `terminate-immediatly`
3. Create a deployment of 1 pod with image `ubuntu:xenial` and the PVC `terminate-immediatly` in default namespace
4. Find the node on which the pod is scheduled to. Let's say the node is `Node-1`
5. ssh into `Node-1`
6. destroy the filesystem of `terminate-immediatly` by running command  `dd if=/dev/zero of=/dev/longhorn/terminate-immediatly`
7. Find and kill the engine instance manager in `Node-X`. Longhorn manager will notice that the instance manager is down and try to bring up a new instance manager e for `Node-X`.
8. After bringing up the instance manager e, Longhorn manager will try to remount the volume `terminate-immediatly`. The remounting should fail bc we already destroyed the filesystem of the volume.
9. We should see this log message
```
[longhorn-manager-xv5th] time="2020-06-23T18:13:15Z" level=info msg="Event(v1.ObjectReference{Kind:\"Volume\", Namespace:\"longhorn-system\", Name:\"terminate-immediatly\", UID:\"de6ae587-fc7c-40bd-b513-47175ddddf97\", APIVersion:\"longhorn.io/v1beta1\", ResourceVersion:\"4088981\", FieldPath:\"\"}): type: 'Warning' reason: 'Remount' cannot proceed to remount terminate-immediatly on phan-cluster-v3-worker1: cannot get the filesystem type by using the command blkid /dev/longhorn/terminate-immediatly | sed 's/.*TYPE=//g'"
```

### Case 2: Volume with no filesystem try to remount

1. Create a volume of size 1GB, say `terminate-immediatly` volume.
2. Attach volume `terminate-immediatly` to a node, say `Node-1`
3. Find and kill the engine instance manager in `Node-1`. Longhorn manager will notice that the instance manager is down and try to bring up a new instance manager e for `Node-1`.
4. After bringing up the instance manager e, Longhorn manager will try to remount the volume `terminate-immediatly`. The remounting should fail bc the volume does not have a filesystem.
5. We should see that Longhorn reattached but skip the remount the volume `terminate-immediatly`
6. Verify the volume can be detached.
