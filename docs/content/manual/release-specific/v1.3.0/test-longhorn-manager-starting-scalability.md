---
title: Test longhorn manager pod starting scalability
---

### Test step
1. Deploy a cluster with multiple nodes. e.g., 20 worker nodes.
2. Launch an old Longhorn version without the fix PR. e.g., Longhorn version v1.2.3.
3. Create and attach multiple volumes on different nodes. e.g.,:
    ```yaml
    apiVersion: longhorn.io/v1beta2
    kind: BackingImage
    metadata:
      name: bi-test1
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    kind: StorageClass
    apiVersion: storage.k8s.io/v1
    metadata:
      name: longhorn-test1
    provisioner: driver.longhorn.io
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    volumeBindingMode: Immediate
    parameters:
      numberOfReplicas: "3"
      staleReplicaTimeout: "2880"
      fromBackup: ""
      fsType: "ext4"
      backingImage: "bi-test1"
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: nginx
      labels:
        app: nginx
    spec:
      ports:
        - port: 80
          name: web
      selector:
        app: nginx
      type: NodePort
    ---
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: bi-scalability-test
      namespace: default
    spec:
      selector:
        matchLabels:
          app: nginx
      serviceName: "nginx"
      replicas: 20
      podManagementPolicy: Parallel
      template:
        metadata:
          labels:
            app: nginx
        spec:
          restartPolicy: Always
          terminationGracePeriodSeconds: 10
          containers:
            - name: nginx
              image: k8s.gcr.io/nginx-slim:0.8
              ports:
                - containerPort: 80
                  name: web
              volumeMounts:
                - name: www1
                  mountPath: /usr/share/nginx/html
                - name: www2
                  mountPath: /usr/share/nginx/html2
                - name: www3
                  mountPath: /usr/share/nginx/html3
                - name: www4
                  mountPath: /usr/share/nginx/html4
                - name: www5
                  mountPath: /usr/share/nginx/html5
                - name: www6
                  mountPath: /usr/share/nginx/html6
                - name: www7
                  mountPath: /usr/share/nginx/html7
                - name: www8
                  mountPath: /usr/share/nginx/html8
                - name: www9
                  mountPath: /usr/share/nginx/html9
                - name: www10
                  mountPath: /usr/share/nginx/html10
      volumeClaimTemplates:
        - metadata:
            name: www1
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www2
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www3
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www4
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www5
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www6
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www7
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www8
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www9
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
        - metadata:
            name: www10
          spec:
            accessModes: [ "ReadWriteOnce" ]
            storageClassName: "longhorn-test1"
            resources:
              requests:
                storage: 32Mi
    ```
4. Delete DaemonSet `longhorn-manager` and wait for all pods cleanup.
5. Recreate DaemonSet `longhorn-manager` and record the time elapsed when all pods become running and ready. This should take a long time.
6. Upgrade Longhorn to another version that does not contain the fix (the old upgrade path). Then record the time elapsed when all pods become running and ready. This should take a long time as well.
7. Upgrade Longhorn to the version that contains the fix (the new upgrade path) and record the time. This should take a relatively short time.
8. Delete DaemonSet `longhorn-manager` and wait for all pods cleanup.
9. Recreate DaemonSet `longhorn-manager` and record the time. This should take a relatively short time, too.

---
GitHub Issue: https://github.com/longhorn/longhorn/issues/3087