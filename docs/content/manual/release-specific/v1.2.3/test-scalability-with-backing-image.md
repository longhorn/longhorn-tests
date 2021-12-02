---
title: Test scalability with backing image 
---

### Test step
1. Deploy a cluster with 3 worker nodes. The recommended nodes is 4v cores CPU + 8G memory at least.
2. Deploy Longhorn.
3. Launch 10 backing images with the following YAML:
    ```yaml
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test1
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test2
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test3
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test4
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test5
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test6
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test7
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test8
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test9
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ---
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test10
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ```
4. Use the following YAML to launch some workloads with 250 volumes. Each volume uses 1 backing image and contains 3 replicas.
    ```yaml
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
    kind: StorageClass
    apiVersion: storage.k8s.io/v1
    metadata:
       name: longhorn-test2
    provisioner: driver.longhorn.io
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    volumeBindingMode: Immediate
    parameters:
       numberOfReplicas: "3"
       staleReplicaTimeout: "2880"
       fromBackup: ""
       fsType: "ext4"
       backingImage: "bi-test2"
    ---
    kind: StorageClass
    apiVersion: storage.k8s.io/v1
    metadata:
       name: longhorn-test3
    provisioner: driver.longhorn.io
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    volumeBindingMode: Immediate
    parameters:
       numberOfReplicas: "3"
       staleReplicaTimeout: "2880"
       fromBackup: ""
       fsType: "ext4"
       backingImage: "bi-test3"
    ---
    kind: StorageClass
    apiVersion: storage.k8s.io/v1
    metadata:
       name: longhorn-test4
    provisioner: driver.longhorn.io
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    volumeBindingMode: Immediate
    parameters:
       numberOfReplicas: "3"
       staleReplicaTimeout: "2880"
       fromBackup: ""
       fsType: "ext4"
       backingImage: "bi-test4"
    ---
    kind: StorageClass
    apiVersion: storage.k8s.io/v1
    metadata:
       name: longhorn-test5
    provisioner: driver.longhorn.io
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    volumeBindingMode: Immediate
    parameters:
       numberOfReplicas: "3"
       staleReplicaTimeout: "2880"
       fromBackup: ""
       fsType: "ext4"
       backingImage: "bi-test5"
    ```
    ```yaml
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
      replicas: 25
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
          storageClassName: "longhorn-test2"
          resources:
            requests:
              storage: 32Mi
      - metadata:
          name: www8
        spec:
          accessModes: [ "ReadWriteOnce" ]
          storageClassName: "longhorn-test3"
          resources:
            requests:
              storage: 32Mi
      - metadata:
          name: www9
        spec:
          accessModes: [ "ReadWriteOnce" ]
          storageClassName: "longhorn-test4"
          resources:
            requests:
              storage: 32Mi
      - metadata:
          name: www10
        spec:
          accessModes: [ "ReadWriteOnce" ]
          storageClassName: "longhorn-test5"
          resources:
            requests:
              storage: 32Mi
    ```
    
   Notice:  
     - Each replica/pod of this StatefulSet contains 10 volumes. You just adjust the volume count by scaling this StatefulSet.
     - Launching this StatefulSet will take a long time.
     - Only 5 of the 10 backing images are used by volumes above. The reason is that unused backing images will lead to replica controller enqueuing before the fix, which contribute to replica controller work queue jam.
       **Theoretically, QAs would create more unused backing images to verify that.**
5. Wait for all pods up and running.
6. Create and attach a volume via UI. This should **not** take a long time. In contrast, creating or deleting a volume under a similar env in v1.2.2 or lower versions will get stuck. 
