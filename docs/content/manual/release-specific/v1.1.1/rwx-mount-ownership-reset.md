---
title: Test RWX share-mount ownership reset
---

## Related issue
https://github.com/longhorn/longhorn/issues/2357

## Test RWX share-mount ownership

**Given** Setup one of cluster node to use host FQDN.
```
root@ip-172-30-0-139:/home/ubuntu# cat /etc/hosts
127.0.0.1 localhost
54.255.224.72 ip-172-30-0-139.lan ip-172-30-0-139

root@ip-172-30-0-139:/home/ubuntu# hostname
ip-172-30-0-139

root@ip-172-30-0-139:/home/ubuntu# hostname -f
ip-172-30-0-139.lan
```

*And* `Domain = localdomain` is commented out in `/etc/idmapd.conf` on cluster hosts.
This is to ensure `localdomain` is not enforce to sync between server and client.
Ref: https://github.com/longhorn/website/pull/279
```
root@ip-172-30-0-139:~# cat /etc/idmapd.conf 
[General]

Verbosity = 0
Pipefs-Directory = /run/rpc_pipefs
# set your own domain here, if it differs from FQDN minus hostname
# Domain = localdomain

[Mapping]

Nobody-User = nobody
Nobody-Group = nogroup
```

*And* pod with rwx pvc deployed to the node with host FQDN.
Here need to update `nodeSelector.kubernetes.io/hostname` below to match
the node name.
```
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: longhorn-volv-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: longhorn
  resources:
    requests:
      storage: 2Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: volume-test
  namespace: default
spec:
  securityContext:
    runAsUser: 0
    runAsGroup: 0
  restartPolicy: Always
  containers:
  - name: volume-test
    image: busybox
    imagePullPolicy: IfNotPresent
    command: [ "sh", "-c", "while :; do date > /data/date.txt; sleep 10; done"]
    volumeMounts:
    - name: volv
      mountPath: /data
  nodeSelector:
    kubernetes.io/hostname: ip-172-30-0-139
  volumes:
  - name: volv
    persistentVolumeClaim:
      claimName: longhorn-volv-pvc
```

**When** check file and directory permission of mounted path.
```
root@ip-172-30-0-139:/home/ubuntu# kubectl exec -it volume-test -- ls -l /data
```

**Then** should not see ownership changed to nobody.
```
-rw-r--r--    1 root     root            29 Apr  6 14:07 date.txt
drwx------    2 root     root         16384 Apr  6 14:06 lost+found
```
