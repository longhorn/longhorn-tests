import pytest


@pytest.mark.skip(reason='TODO')
def test_rwx_with_statefulset_multi_pods():  # NOQA
    """
    Test creation of share manager pod and rwx volumes from 2 pods.

    1. Create a StatefulSet of 2 pods with VolumeClaimTemplate where accessMode
       is 'RWX'.
    2. Wait for both pods to come up running.
    3. Verify there are two share manager pods created in the longhorn
       namespace and they have the directory with the PV name in the
       path `/export`
    4. Write data in both pods and compute md5sum.
    5. Compare md5sum of the data with the data written the share manager.
    """


@pytest.mark.skip(reason='TODO')
def test_rwx_multi_statefulset_with_same_pvc():  # NOQA
    """
    Test writing of data into a volume from multiple pods using same PVC

    1. Create a volume with 'accessMode' rwx.
    2. Create a PV and a PVC with access mode 'readwritemany' and attach to the
       volume.
    3. Deploy a StatefulSet of 2 pods with the existing PVC above created.
    4. Wait for both pods to come up.
    5. Create a StatefulSet of 2 pods with VolumeClaimTemplate and
    6. Wait for StatefulSet to come up healthy.
    7. Write data and compute md5sum.
    8. Create another statefulSet with same pvc which got created with first
       statefulSet.
    9. Wait for statefulSet to come up healthy.
    10. Check the data md5sum.
    11. Write more data and compute md5sum.
    12. Check the data md5sum in the share manager pod.
    """


@pytest.mark.skip(reason='TODO')
def test_rwx_parallel_writing():  # NOQA
    """
    Test parallel writing of data

    1. Create a StatefulSet of 1 pod with VolumeClaimTemplate where accessMode
       is 'RWX'.
    2. Wait for StatefulSet to come up healthy.
    3. Create another statefulSet with same pvc which got created with first
       statefulSet.
    4. Wait for statefulSet to come up healthy.
    5. Start writing 800 MB data in first statefulSet `file 1` and start
       writing 500 MB data in second statefulSet `file 2`.
    6. Compute md5sum.
    7. Check the data md5sum in share manager pod volume
    """


@pytest.mark.skip(reason='TODO')
def test_rwx_statefulset_scale_down_up():  # NOQA
    """
    Test Scaling up and down of pods attached to rwx volume.

    1. Create a StatefulSet of 2 pods with VolumeClaimTemplate where accessMode
       is 'RWX'.
    2. Wait for StatefulSet pods to come up healthy.
    3. Write data and compute md5sum in the both pods.
    4. Delete the pods.
    5. Wait for the pods to be terminated.
    6. Verify the share manager pods are no longer available and the volume is
       detached.
    6. Recreate the pods
    7. Wait for new pods to come up.
    8. Check the data md5sum in new pods.
    """


@pytest.mark.skip(reason="TODO")
def test_rwx_delete_share_manager_pod():  # NOQA
    """
    Test moving of Share manager pod from one node to another.

    1. Create a StatefulSet of 1 pod with VolumeClaimTemplate where accessMode
       is 'RWX'.
    2. Wait for StatefulSet to come up healthy.
    3. Write data and compute md5sum.
    4. Delete the share manager pod.
    5. Wait for a new pod to be created and volume getting attached.
    6. Check the data md5sum in statefulSet
    7. Write more data to it and compute md5sum.
    8. Check the data md5sum in share manager volume
    """


@pytest.mark.skip(reason='TODO')
def test_rwx_deployment_with_multi_pods():  # NOQA
    """
    Test deployment of 2 pods with same PVC.

    1. Create a volume with 'accessMode' rwx.
    2. Create a PV and a PVC with access mode 'readwritemany' and attach to the
       volume.
    3. Create a deployment of 2 pods with PVC created
    4. Wait for 2 pods to come up healthy.
    5. Write data in both pods and compute md5sum.
    6. Check the data md5sum in the share manager pod.
    """


@pytest.mark.skip(reason='TODO')
def test_restore_rwo_volume_to_rwx():  # NOQA
    """
    Test restoring a rwo to a rwx volume.

    1. Create a volume with 'accessMode' rwo.
    2. Create a PV and a PVC with access mode 'readwriteonce' and attach to the
       volume.
    3. Create a pod and attach to the PVC.
    4. Write some data into the pod and compute md5sum.
    5. Take a backup of the volume.
    6. Restore the backup with 'accessMode' rwx.
    7. Create PV and PVC and attach to 2 pods.
    8. Verify the data.
    """
