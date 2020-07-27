import pytest
'''
Fixture required for this module to clean up longhorn-nfs-provisioner related
resources.
'''


@pytest.mark.skip(reason="TODO")
def test_rwx_with_statefulset_multi_pods():
    """
    Test writing of data in same volume from 2 pods

    1. Create PodSecurityPolicy for longhorn-nfs-provisioner as sample yaml
       https://raw.githubusercontent.com/longhorn/longhorn/master/examples
       /rwx/01-security.yaml

    2. Create serviceAccount, service, longhorn-nfs-provisioner deployment,
       PVC and StorageClass as sample yaml https://raw.githubusercontent.com/
       longhorn/longhorn/master/examples/rwx/02-longhorn-nfs-provisioner.yaml

    3. Wait for longhorn-nfs-provisioner deployment to come up healthy.
    4. Verify the volume named as the PV attached to longhorn-nfs-provisioner
       `volume.ready == True`
    5. Create a StatefulSet of 2 pods with VolumeClaimTemplate and
       longhorn-nfs class in default namespace.
    6. Wait for both pods to come up running.
    7. Verify two folders get created with PV names in longhorn-nfs-provisioner
       volume.
    8. Write data in both pods and compute md5sum.
    9. Compare md5sum of the data in longhorn-nfs-provisioner volume
    """
    pass


@pytest.mark.skip(reason="TODO")
def test_rwx_multi_statefulset_with_same_pvc():
    """
    Test writing of data with multiple pods using same PVC

    1. Create PodSecurityPolicy for longhorn-nfs-provisioner as sample yaml
       https://raw.githubusercontent.com/longhorn/longhorn/master/examples
       /rwx/01-security.yaml

    2. Create serviceAccount, service, longhorn-nfs-provisioner deployment,
       PVC and StorageClass as sample yaml https://raw.githubusercontent.com/
       longhorn/longhorn/master/examples/rwx/02-longhorn-nfs-provisioner.yaml

    3. Wait for longhorn-nfs-provisioner deployment to come up healthy.
    4. Verify the volume named as the PV attached to longhorn-nfs-provisioner
       `volume.ready == True`
    5. Create a StatefulSet of 1 pod with VolumeClaimTemplate and
       longhorn-nfs class in default namespace.
    6. Wait for StatefulSet to come up healthy.
    7. Write data and compute md5sum.
    8. Create another statefulSet with same pvc which got created with first
       statefulSet.
    9. Wait for statefulSet to come up healthy.
    10. Check the data md5sum.
    11. Write more data and compute md5sum
    12. Check the data md5sum in longhorn-nfs-provisioner volume
    """
    pass


@pytest.mark.skip(reason="TODO")
def test_rwx_parallel_writing():
    """
    Test parallel writing of data

    1. Create PodSecurityPolicy for longhorn-nfs-provisioner as sample yaml
       https://raw.githubusercontent.com/longhorn/longhorn/master/examples
       /rwx/01-security.yaml

    2. Create serviceAccount, service, longhorn-nfs-provisioner deployment,
       PVC and StorageClass as sample yaml https://raw.githubusercontent.com/
       longhorn/longhorn/master/examples/rwx/02-longhorn-nfs-provisioner.yaml

    3. Wait for longhorn-nfs-provisioner deployment to come up healthy.
    4. Verify the volume named as the PV attached to longhorn-nfs-provisioner
       `volume.ready == True`
    5. Create a StatefulSet of 1 pod with VolumeClaimTemplate and
       longhorn-nfs class in default namespace.
    6. Wait for StatefulSet to come up healthy.
    7. Create another statefulSet with same pvc which got created with first
       statefulSet.
    8. Wait for statefulSet to come up healthy.
    9. Start writing 800 MB data in first statefulSet `file 1` and start
       writing 500 MB data in second statefulSet `file 2`.
    10. Compute md5sum.
    11. Check the data md5sum in longhorn-nfs-provisioner volume
    """
    pass


@pytest.mark.skip(reason="TODO")
def test_rwx_statefulset_scale_down_up():
    """
    Test Scaling up and down of pods attached to longhorn-nfs-provisioner
    volume.

    1. Create PodSecurityPolicy for longhorn-nfs-provisioner as sample yaml
       https://raw.githubusercontent.com/longhorn/longhorn/master/examples
       /rwx/01-security.yaml

    2. Create serviceAccount, service, longhorn-nfs-provisioner deployment,
       PVC and StorageClass as sample yaml https://raw.githubusercontent.com/
       longhorn/longhorn/master/examples/rwx/02-longhorn-nfs-provisioner.yaml

    3. Wait for longhorn-nfs-provisioner deployment to come up healthy.
    4. Verify the volume named as the PV attached to longhorn-nfs-provisioner
       `volume.ready == True`
    5. Create a StatefulSet of 2 pods with VolumeClaimTemplate and
       longhorn-nfs class in default namespace.
    6. Wait for StatefulSet pods to come up healthy.
    7. Write data and compute md5sum in both pods
    8. Delete pods.
    9. Wait for pods to terminate.
    10. Recreate the pods
    11. Wait for new pods to come up.
    12. Check the data md5sum in new pods
    """
    pass


@pytest.mark.skip(reason="TODO")
def test_rwx_offline_node_longhorn_nfs_provisioner():
    """
    Test moving of longhorn-nfs-provisioner pod from one node to another.

    1. Create PodSecurityPolicy for longhorn-nfs-provisioner as sample yaml
       https://raw.githubusercontent.com/longhorn/longhorn/master/examples
       /rwx/01-security.yaml

    2. Create serviceAccount, service, longhorn-nfs-provisioner deployment,
       PVC and StorageClass as sample yaml https://raw.githubusercontent.com/
       longhorn/longhorn/master/examples/rwx/02-longhorn-nfs-provisioner.yaml
       Make sure liveness probe is added in the deployment.

    3. Wait for longhorn-nfs-provisioner deployment to come up healthy.
    4. Verify the volume named as the PV attached to longhorn-nfs-provisioner
       `volume.ready == True`
    5. Create a StatefulSet of 1 pod with VolumeClaimTemplate and
       longhorn-nfs class in default namespace.
    6. Wait for StatefulSet to come up healthy.
    7. Write data and compute md5sum.
    8. Shutdown the node where longhorn-nfs-provisioner is running. The
       liveness probe will restart the pod on another node.
    9. Wait for a new pod to be created and volume getting attached.
    10. Check the data md5sum in statefulSet
    11. Write more data to it and compute md5sum.
    12. Check the data md5sum in longhorn-nfs-provisioner volume
    """
    pass


@pytest.mark.skip(reason="TODO")
def test_rwx_deployment_with_multi_pods():
    """
    Test deployment of 2 pods with same PVC.

    1. Create PodSecurityPolicy for longhorn-nfs-provisioner as sample yaml
       https://raw.githubusercontent.com/longhorn/longhorn/master/examples
       /rwx/01-security.yaml

    2. Create serviceAccount, service, longhorn-nfs-provisioner deployment,
       PVC and StorageClass as sample yaml https://raw.githubusercontent.com/
       longhorn/longhorn/master/examples/rwx/02-longhorn-nfs-provisioner.yaml
       Make sure liveness probe is added in the deployment.

    3. Wait for longhorn-nfs-provisioner deployment to come up healthy.
    4. Verify the volume named as the PV attached to longhorn-nfs-provisioner
       `volume.ready == True`
    5. Create a deployment of 2 pods with PVC created with longhorn-nfs class
    6. Wait for 2 pods to come up healthy.
    7. Write data in both pods and compute md5sum.
    8. Check the data md5sum in longhorn-nfs-provisioner volume
    """
    pass
