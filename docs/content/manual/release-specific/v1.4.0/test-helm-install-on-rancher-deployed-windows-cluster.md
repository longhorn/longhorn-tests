---
title: Test helm on Rancher deployed Windows Cluster
---

## Related issue
https://github.com/longhorn/longhorn/issues/4246

## Test Install

**Given** Rancher cluster.

*And* 3 new instances for the Windows cluster following [Architecture Requirements](https://rancher.com/docs/rancher/v2.6/en/cluster-provisioning/rke-clusters/windows-clusters/#architecture-requirements).

*And* docker installed on the 3 Windows cluster instances.

*And* [Disabled Private IP Address Checks](https://rancher.com/docs/rancher/v2.6/en/cluster-provisioning/rke-clusters/windows-clusters/host-gateway-requirements/#disabling-private-ip-address-checks) for the 3 Windows cluster instances.

*And* Created new `Custom` Windows cluster with Rancher.
> Select `Flannel` for `Network Provider` \
  Enable `Windows Support`

*And* Added the 3 nodes to the Rancher Windows cluster.
> [Add Linux Master Node](https://rancher.com/docs/rancher/v2.6/en/cluster-provisioning/rke-clusters/windows-clusters/#add-linux-master-node)\
  [Add Linux Worker Node](https://rancher.com/docs/rancher/v2.6/en/cluster-provisioning/rke-clusters/windows-clusters/#add-linux-master-node)\
  [Add Windows Worker Node](https://rancher.com/docs/rancher/v2.6/en/cluster-provisioning/rke-clusters/windows-clusters/#add-a-windows-worker-node)

**When** helm install longhorn with `global.cattle.windowsCluster.enabled=true`.
```bash
kubectl create namespace longhorn-system && \
helm install longhorn ./chart/ --namespace longhorn-system \
  --set global.cattle.windowsCluster.enabled=true
```

**Then** All longhorn components should only run on the Linux worker node.

*And* All longhorn component should be `Running`.

## Test Basic Operation

**Given** Rancher deployed Windows cluster.

*And* Longhorn deployed and running.

*And* `Replica Node Level Soft Anti-Affinity` enabled.

*And* Snapshot recurring job in default group.
```yaml
apiVersion: longhorn.io/v1beta2
kind: RecurringJob
metadata:
  name: sample
  namespace: longhorn-system
spec:
  concurrency: 1
  cron: '* * * * *'
  groups:
  - default
  labels: {}
  name: sample
  retain: 1
  task: snapshot
```

**When** Create Pod with PVC.
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: longhorn-volv-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: volume-test
  namespace: default
spec:
  nodeSelector:
    kubernetes.io/os: "linux"
    node-role.kubernetes.io/worker: "true"
  restartPolicy: Always
  tolerations:
    - effect: NoSchedule
      key: cattle.io/os
      operator: Equal
      value: linux
  containers:
  - name: volume-test
    image: nginx:stable-alpine
    imagePullPolicy: IfNotPresent
    livenessProbe:
      exec:
        command:
          - ls
          - /data/lost+found
      initialDelaySeconds: 5
      periodSeconds: 5
    volumeMounts:
    - name: volv
      mountPath: /data
    ports:
    - containerPort: 80
  volumes:
  - name: volv
    persistentVolumeClaim:
      claimName: longhorn-volv-pvc
```

*And* Write some data to the Pod.
```bash
kubectl exec -it volume-test -- /bin/sh -c "echo foo > /data/bar && cat /data/bar"
```

**Then** Volume snapshot should get created after the recurring job scheduled time.

## Test Uninstall

**Given** Rancher deployed Windows cluster.

*And* Longhorn deployed and running.

**When** Helm uninstall longhorn.
```bash
helm uninstall longhorn --namespace longhorn-system
```

**Then** Longhorn should uninstall successfully.