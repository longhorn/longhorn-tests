---
title: Test File Sync Cancellation
---

## Related issue

https://github.com/longhorn/longhorn/issues/2416

## Test step
1. For test convenience, manually launch the backing image manager pods:
```
apiVersion: apps/v1
kind: DaemonSet
metadata:
  labels:
    app: backing-image-manager
  name: backing-image-manager
  namespace: longhorn-system
spec:
  selector:
    matchLabels:
      app: backing-image-manager
  template:
    metadata:
      labels:
        app: backing-image-manager
    spec:
      containers:
      - name: backing-image-manager
        image: longhornio/backing-image-manager:master
        imagePullPolicy: Always
        securityContext:
          privileged: true
        command:
        - backing-image-manager
        - --debug
        - daemon
        - --listen
        - 0.0.0.0:8000
        readinessProbe:
          tcpSocket:
            port: 8000
        volumeMounts:
        - name: disk-path
          mountPath: /data
      volumes:
      - name: disk-path
        hostPath:
          path: /var/lib/longhorn/
      serviceAccountName: longhorn-service-account
```
2. Download a backing image in the first pod:
```
# alias bm="backing-image-manager backing-image"
# bm pull --name bi-test --uuid uuid-bi-test --download-url https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img
# bm ls
```
3. In the 2nd pod, limit the bandwidth first so that the downloading won't be done within several seconds
```
tc qdisc del dev eth0 root
tc qdisc add dev eth0 root tbf rate 500kbit latency 0.1ms burst 1000kbit
```
4. Then start to get the backing image file from the 1st BIM pod
```
# alias bm="backing-image-manager backing-image"
# bm sync --name bi-test --uuid uuid-bi-test --download-url https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img --size 208601088 --from-host <the IP of 1st BIM pod> --to-host <the IP of 2nd BIM pod>
# bm ls
```
5. During the syncing, directly deleting the downloading backing image in the 2nd pod
```
# bm delete bi-test
```
6. Wait 1 minute and check the log of the 2nd pod. Make sure there is no download/sync (failure) related logs after the deletion. Then restarting sync without deletion, the backing image can be downloaded successfully.