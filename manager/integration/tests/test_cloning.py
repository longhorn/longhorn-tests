import pytest

@pytest.mark.skip(reason="TODO") # NOQA
@pytest.mark.cloning  # NOQA
def test_cloning_without_backing_image():  # NOQA
    """
    1. Create a PVC:
        ```yaml
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
          name: source-pvc
        spec:
          storageClassName: longhorn
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi
        ```
    2. Specify the `source-pvc` in a pod yaml and start the pod
    3. Wait for the pod to be running, write some data to the mount
       path of the volume
    4. Clone a volume by creating the PVC:
        ```yaml
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
          name: cloned-pvc
        spec:
          storageClassName: longhorn
          dataSource:
            name: source-pvc
            kind: PersistentVolumeClaim
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi
        ```
    5. Specify the `cloned-pvc` in a cloned pod yaml and deploy the cloned pod
    6. Wait for the `CloneStatus.State` in `cloned-pvc` to be `completed`
    7. In 3-min retry loop, wait for the cloned pod to be running
    8. Verify the data in `cloned-pvc` is the same as in `source-pvc`
    9. In 2-min retry loop, verify the volume of the `clone-pvc` eventually
       becomes healthy
    10. Cleanup the cloned pod, `cloned-pvc`. Wait for the cleaning to finish
    11. Scale down the source pod so the `source-pvc` is detached.
    12. Wait for the `source-pvc` to be in detached state
    13. Clone a volume by creating the PVC:
        ```yaml
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
          name: cloned-pvc
        spec:
          storageClassName: longhorn
          dataSource:
            name: source-pvc
            kind: PersistentVolumeClaim
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi
        ```
    14. Specify the `cloned-pvc` in a cloned pod yaml and deploy the cloned
        pod
    15. Wait for `source-pvc` to be attached
    16. Wait for a new snapshot created in `source-pvc` volume created
    17. Wait for the `CloneStatus.State` in `cloned-pvc` to be `completed`
    18. Wait for `source-pvc` to be detached
    19. In 3-min retry loop, wait for the cloned pod to be running
    20. Verify the data in `cloned-pvc` is the same as in `source-pvc`
    21. In 2-min retry loop, verify the volume of the `clone-pvc` eventually
        becomes healthy
    22. Cleanup the test
    """


@pytest.mark.skip(reason="TODO") # NOQA
@pytest.mark.cloning  # NOQA
def test_cloning_with_backing_image():  # NOQA
    """
    1. Deploy a storage class that has backing image parameter
      ```yaml
      kind: StorageClass
      apiVersion: storage.k8s.io/v1
      metadata:
        name: longhorn-bi-parrot
      provisioner: driver.longhorn.io
      allowVolumeExpansion: true
      parameters:
        numberOfReplicas: "3"
        staleReplicaTimeout: "2880" # 48 hours in minutes
        backingImage: "bi-parrot"
        backingImageURL: "https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2" # NOQA
      ```
    2. Repeat the `test_cloning_without_backing_image()` test with
       `source-pvc` and `cloned-pvc` use `longhorn-bi-parrot` instead of
       `longhorn` storageclass
    3. Clean up the test
    """

@pytest.mark.skip(reason="TODO") # NOQA
@pytest.mark.cloning  # NOQA
def test_cloning_interrupted():  # NOQA
    """
    1. Create a PVC:
        ```yaml
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
          name: source-pvc
        spec:
          storageClassName: longhorn
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi
        ```
    2. Specify the `source-pvc` in a pod yaml and start the pod
    3. Wait for the pod to be running, write 1GB of data to the mount
       path of the volume
    4. Clone a volume by creating the PVC:
        ```yaml
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
          name: cloned-pvc
        spec:
          storageClassName: longhorn
          dataSource:
            name: source-pvc
            kind: PersistentVolumeClaim
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi
        ```
    5. Specify the `cloned-pvc` in a cloned pod yaml and deploy the cloned pod
    6. Wait for the `CloneStatus.State` in `cloned-pvc` to be `initiated`
    7. Kill all replicas process of the `source-pvc`
    8. Wait for the `CloneStatus.State` in `cloned-pvc` to be `failed`
    9. In 2-min retry loop, verify cloned pod cannot start
    10. Clean up cloned pod and `clone-pvc`
    11. Redeploy `cloned-pvc` and clone pod
    12. In 3-min retry loop, verify cloned pod become running
    13. `cloned-pvc` has the same data as `source-pvc`
    14. Cleanup the test
    """
