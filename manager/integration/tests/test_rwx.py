from common import create_and_wait_statefulset, wait_for_volume_detached
from common import generate_random_data, get_volume_name
from common import VOLUME_RWTEST_SIZE, write_pod_volume_data
from common import check_pod_existence, LONGHORN_NAMESPACE
from common import exec_command_in_pod, get_pod_data_md5sum
from common import create_and_wait_pod, read_volume_data
from common import get_apps_api_client, wait_statefulset
from common import create_and_wait_deployment, delete_and_wait_pod
from common import delete_and_wait_deployment
from common import delete_and_wait_pvc
from common import prepare_pod_with_data_in_mb, DATA_SIZE_IN_MB_1
from common import create_snapshot, wait_for_backup_completion
from common import find_backup, Gi, volume_name, csi_pv, pod_make  # NOQA
from common import wait_for_volume_creation, DATA_SIZE_IN_MB_3
from common import create_pv_for_volume, create_pvc_for_volume
from common import DEFAULT_STATEFULSET_TIMEOUT, DEFAULT_STATEFULSET_INTERVAL
from common import wait_for_pod_remount
from common import get_core_api_client, write_pod_volume_random_data
from common import create_pvc_spec, make_deployment_with_pvc  # NOQA
from common import core_api, statefulset, pvc, pod, client  # NOQA
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import EXPANDED_VOLUME_SIZE
from common import expand_and_wait_for_pvc, wait_for_volume_expansion
from common import wait_deployment_replica_ready, wait_for_volume_healthy
from common import crypto_secret, storage_class  # NOQA
from common import create_crypto_secret, create_storage_class
from backupstore import set_random_backupstore # NOQA
from multiprocessing import Pool

import time
import pytest


def write_data_into_pod(pod_name_and_data_path):
    pod_info = pod_name_and_data_path.split(':')
    core_api = get_core_api_client()  # NOQA
    write_pod_volume_random_data(core_api, pod_info[0], pod_info[1],
                                 DATA_SIZE_IN_MB_3)


def test_rwx_with_statefulset_multi_pods(core_api, statefulset):  # NOQA
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

    statefulset_name = 'statefulset-rwx-multi-pods-test'
    share_manager_name = []
    volumes_name = []

    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = 'longhorn'
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['accessModes'] \
        = ['ReadWriteMany']

    create_and_wait_statefulset(statefulset)

    for i in range(2):
        pvc_name = \
            statefulset['spec']['volumeClaimTemplates'][0]['metadata']['name']\
            + '-' + statefulset_name + '-' + str(i)
        pv_name = get_volume_name(core_api, pvc_name)

        assert pv_name is not None

        volumes_name.append(pv_name)
        share_manager_name.append('share-manager-' + pv_name)

        check_pod_existence(core_api, share_manager_name[i],
                            namespace=LONGHORN_NAMESPACE)

    command = "ls /export | grep -i 'pvc' | wc -l"

    assert exec_command_in_pod(
        core_api, command, share_manager_name[0], LONGHORN_NAMESPACE) == '1'
    assert exec_command_in_pod(
        core_api, command, share_manager_name[1], LONGHORN_NAMESPACE) == '1'

    md5sum_pod = []
    for i in range(2):
        test_pod_name = statefulset_name + '-' + str(i)
        test_data = generate_random_data(VOLUME_RWTEST_SIZE)
        write_pod_volume_data(core_api, test_pod_name, test_data)
        md5sum_pod.append(test_data)

    for i in range(2):
        command = 'cat /export' + '/' + volumes_name[i] + '/' + 'test'
        pod_data = exec_command_in_pod(
            core_api, command, share_manager_name[i], LONGHORN_NAMESPACE)

        assert pod_data == md5sum_pod[i]


def test_rwx_multi_statefulset_with_same_pvc(core_api, pvc, statefulset, pod):  # NOQA
    """
    Test writing of data into a volume from multiple pods using same PVC

    1. Create a volume with 'accessMode' rwx.
    2. Create a PV and a PVC with access mode 'readwritemany' and attach to the
       volume.
    3. Deploy a StatefulSet of 2 pods with the existing PVC above created.
    4. Wait for both pods to come up.
    5. Create a pod with the existing PVC above created.
    6. Wait for StatefulSet to come up healthy.
    7. Write data all three pods and compute md5sum.
    8. Check the data md5sum in the share manager pod.
    """
    pvc_name = 'pvc-multi-pods-test'
    statefulset_name = 'statefulset-rwx-same-pvc-test'
    pod_name = 'pod-rwx-same-pvc-test'

    pvc['metadata']['name'] = pvc_name
    pvc['spec']['storageClassName'] = 'longhorn'
    pvc['spec']['accessModes'] = ['ReadWriteMany']

    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['template']['spec']['volumes'] = \
        [create_pvc_spec(pvc_name)]
    del statefulset['spec']['volumeClaimTemplates']

    create_and_wait_statefulset(statefulset)

    pv_name = get_volume_name(core_api, pvc_name)
    share_manager_name = 'share-manager-' + pv_name

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, statefulset_name + '-0',
                          test_data, filename='test1')
    assert test_data == read_volume_data(core_api, statefulset_name + '-1',
                                         filename='test1')

    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    assert test_data == read_volume_data(core_api, pod_name, filename='test1')

    test_data_2 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data_2, filename='test2')

    command1 = 'cat /export' + '/' + pv_name + '/' + 'test1'
    command2 = 'cat /export' + '/' + pv_name + '/' + 'test2'

    assert test_data == exec_command_in_pod(
        core_api, command1, share_manager_name, LONGHORN_NAMESPACE)
    assert test_data_2 == exec_command_in_pod(
        core_api, command2, share_manager_name, LONGHORN_NAMESPACE)


def test_rwx_parallel_writing(core_api, statefulset, pod):  # NOQA
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

    statefulset_name = 'statefulset-rwx-parallel-writing-test'

    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['replicas'] = 1
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = 'longhorn'
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['accessModes'] \
        = ['ReadWriteMany']

    create_and_wait_statefulset(statefulset)
    statefulset_pod_name = statefulset_name + '-0'

    pvc_name = \
        statefulset['spec']['volumeClaimTemplates'][0]['metadata']['name'] \
        + '-' + statefulset_name + '-0'
    pv_name = get_volume_name(core_api, pvc_name)
    share_manager_name = 'share-manager-' + pv_name

    pod_name = 'pod-parallel-write-test'
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    with Pool(2) as p:
        p.map(write_data_into_pod, [statefulset_pod_name + ':/data/test1',
                                    pod_name + ':/data/test2'])

    md5sum1 = get_pod_data_md5sum(core_api, statefulset_pod_name, 'data/test1')
    md5sum2 = get_pod_data_md5sum(core_api, pod_name, 'data/test2')

    command1 = 'md5sum /export' + '/' + pv_name + '/' + 'test1' + \
               " | awk '{print $1}'"
    share_manager_data1 = exec_command_in_pod(core_api, command1,
                                              share_manager_name,
                                              LONGHORN_NAMESPACE)
    assert md5sum1 == share_manager_data1

    command2 = 'md5sum /export' + '/' + pv_name + '/' + 'test2' + \
               " | awk '{print $1}'"
    share_manager_data2 = exec_command_in_pod(core_api, command2,
                                              share_manager_name,
                                              LONGHORN_NAMESPACE)
    assert md5sum2 == share_manager_data2


def test_rwx_statefulset_scale_down_up(core_api, statefulset):  # NOQA
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

    statefulset_name = 'statefulset-rwx-scale-down-up-test'
    share_manager_name = []

    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = 'longhorn'
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['accessModes'] \
        = ['ReadWriteMany']

    create_and_wait_statefulset(statefulset)

    for i in range(2):
        pvc_name = \
            statefulset['spec']['volumeClaimTemplates'][0]['metadata']['name']\
            + '-' + statefulset_name + '-' + str(i)
        pv_name = get_volume_name(core_api, pvc_name)

        assert pv_name is not None

        share_manager_name.append('share-manager-' + pv_name)

        check_pod_existence(core_api, share_manager_name[i],
                            namespace=LONGHORN_NAMESPACE)

    md5sum_pod = []
    for i in range(2):
        test_pod_name = statefulset_name + '-' + str(i)
        test_data = generate_random_data(VOLUME_RWTEST_SIZE)
        write_pod_volume_data(core_api, test_pod_name, test_data)
        md5sum_pod.append(test_data)

    statefulset['spec']['replicas'] = replicas = 0
    apps_api = get_apps_api_client()
    apps_api.patch_namespaced_stateful_set(
        name=statefulset_name,
        namespace='default',
        body={
            'spec': {
                'replicas': replicas
            }
        })
    for i in range(DEFAULT_STATEFULSET_TIMEOUT):
        s_set = apps_api.read_namespaced_stateful_set(
            name=statefulset['metadata']['name'],
            namespace='default')
        # s_set is none if statefulset is not yet created
        if s_set is not None and s_set.status.ready_replicas == replicas or \
                (replicas == 0 and not s_set.status.ready_replicas):
            break
        time.sleep(DEFAULT_STATEFULSET_INTERVAL)

    found = True
    for i in range(RETRY_COUNTS):
        pods = core_api.list_namespaced_pod(namespace=LONGHORN_NAMESPACE)
        pod_names = []
        for item in pods.items:
            pod_names.append(item.metadata.name)
        if share_manager_name[0] not in pod_names and  \
                share_manager_name[1] not in pod_names:
            found = False
            break
        time.sleep(RETRY_INTERVAL)

    assert not found

    statefulset['spec']['replicas'] = replicas = 2
    apps_api = get_apps_api_client()
    apps_api.patch_namespaced_stateful_set(
        name=statefulset_name,
        namespace='default',
        body={
            'spec': {
                'replicas': replicas
            }
        })
    wait_statefulset(statefulset)

    for i in range(2):
        test_pod_name = statefulset_name + '-' + str(i)
        command = 'cat /data/test'
        pod_data = exec_command_in_pod(core_api, command, test_pod_name,
                                       'default')

        assert pod_data == md5sum_pod[i]


def test_rwx_delete_share_manager_pod(core_api, statefulset):  # NOQA
    """
    Test moving of Share manager pod from one node to another.

    1. Create a StatefulSet of 1 pod with VolumeClaimTemplate where accessMode
       is 'RWX'.
    2. Wait for StatefulSet to come up healthy.
    3. Write data and compute md5sum.
    4. Delete the share manager pod.
    5. The workload pod should still be functioning
       and the volume should remain attached.
    6. Check the data md5sum in statefulSet.
    7. Write more data to it and compute md5sum.
    8. Check the data md5sum in share manager volume.
    """

    statefulset_name = 'statefulset-delete-share-manager-pods-test'

    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['replicas'] = 1
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = 'longhorn'
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['accessModes'] \
        = ['ReadWriteMany']

    create_and_wait_statefulset(statefulset)

    pod_name = statefulset_name + '-' + '0'
    pvc_name = \
        statefulset['spec']['volumeClaimTemplates'][0]['metadata']['name'] \
        + '-' + statefulset_name + '-0'
    pv_name = get_volume_name(core_api, pvc_name)
    share_manager_name = 'share-manager-' + pv_name

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data, filename='test1')

    delete_and_wait_pod(core_api, share_manager_name,
                        namespace=LONGHORN_NAMESPACE)

    wait_for_pod_remount(core_api, pod_name)

    test_data_2 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data_2, filename='test2')

    command1 = 'cat /export/' + pv_name + '/test1'
    share_manager_data_1 = exec_command_in_pod(
        core_api, command1, share_manager_name, LONGHORN_NAMESPACE)
    assert test_data == share_manager_data_1

    command2 = 'cat /export/' + pv_name + '/test2'
    share_manager_data_2 = exec_command_in_pod(
        core_api, command2, share_manager_name, LONGHORN_NAMESPACE)
    assert test_data_2 == share_manager_data_2


def test_rwx_deployment_with_multi_pods(core_api, pvc, make_deployment_with_pvc):  # NOQA
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

    pvc_name = 'pvc-deployment-multi-pods-test'
    pvc['metadata']['name'] = pvc_name
    pvc['spec']['storageClassName'] = 'longhorn'
    pvc['spec']['accessModes'] = ['ReadWriteMany']

    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    deployment = make_deployment_with_pvc(
        'deployment-multi-pods-test', pvc_name, replicas=2)
    apps_api = get_apps_api_client()
    create_and_wait_deployment(apps_api, deployment)

    pv_name = get_volume_name(core_api, pvc_name)
    share_manager_name = 'share-manager-' + pv_name
    deployment_label_selector = "name=" + \
                                deployment["metadata"]["labels"]["name"]

    deployment_pod_list = \
        core_api.list_namespaced_pod(namespace="default",
                                     label_selector=deployment_label_selector)

    assert deployment_pod_list.items.__len__() == 2

    pod_name_1 = deployment_pod_list.items[0].metadata.name
    test_data_1 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name_1, test_data_1, filename='test1')

    pod_name_2 = deployment_pod_list.items[1].metadata.name
    command = 'cat /data/test1'
    pod_data_2 = exec_command_in_pod(core_api, command, pod_name_2, 'default')

    assert test_data_1 == pod_data_2

    test_data_2 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name_2, test_data_2, filename='test2')

    command = 'cat /export' + '/' + pv_name + '/' + 'test1'
    share_manager_data_1 = exec_command_in_pod(
        core_api, command, share_manager_name, LONGHORN_NAMESPACE)
    assert test_data_1 == share_manager_data_1

    command = 'cat /export' + '/' + pv_name + '/' + 'test2'
    share_manager_data_2 = exec_command_in_pod(
        core_api, command, share_manager_name, LONGHORN_NAMESPACE)

    assert test_data_2 == share_manager_data_2


def test_restore_rwo_volume_to_rwx(set_random_backupstore, client, core_api, volume_name, pvc, csi_pv, pod_make, make_deployment_with_pvc):  # NOQA
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

    data_path = "/data/test"
    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api, csi_pv, pvc,
                                    pod_make,
                                    volume_name,
                                    data_size_in_mb=DATA_SIZE_IN_MB_1,
                                    data_path=data_path)

    snap = create_snapshot(client, volume_name)
    volume = client.by_id_volume(volume_name)
    volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, volume_name, snap.name)
    bv, b1 = find_backup(client, volume_name, snap.name)

    restore_volume_name = 'restored-rwx-volume'
    restore_pv_name = restore_volume_name + "-pv"
    restore_pvc_name = restore_volume_name + "-pvc"

    client.create_volume(name=restore_volume_name, size=str(1 * Gi),
                         numberOfReplicas=3, fromBackup=b1.url,
                         accessMode='rwx')
    wait_for_volume_creation(client, restore_volume_name)
    restore_volume = wait_for_volume_detached(client, restore_volume_name)
    create_pv_for_volume(client, core_api, restore_volume, restore_pv_name)
    create_pvc_for_volume(client, core_api, restore_volume, restore_pvc_name)
    deployment = make_deployment_with_pvc(
        'deployment-multi-pods-test', restore_pvc_name, replicas=2)
    apps_api = get_apps_api_client()
    create_and_wait_deployment(apps_api, deployment)

    deployment_label_selector = \
        "name=" + deployment["metadata"]["labels"]["name"]

    deployment_pod_list = \
        core_api.list_namespaced_pod(namespace="default",
                                     label_selector=deployment_label_selector)

    pod_name_1 = deployment_pod_list.items[0].metadata.name
    pod_name_2 = deployment_pod_list.items[1].metadata.name

    md5sum_pod1 = get_pod_data_md5sum(core_api, pod_name_1, data_path)
    md5sum_pod2 = get_pod_data_md5sum(core_api, pod_name_2, data_path)

    assert md5sum == md5sum_pod1 == md5sum_pod2


@pytest.mark.skip(reason="TODO")
def test_rwx_online_expansion(): # NOQA
    """
    Related issue :
    https://github.com/longhorn/longhorn/issues/2181
    https://github.com/longhorn/longhorn/issues/2484

    This test case does not cover the UI test mentioned in the related issue's
    test steps."

    Given
    - Create a rwx pvc using longhorn storage class of size 1 Gi.

    And
    - Attach it to a workload (deployment) and write some data.

    When
    - Expand the volume to 5 Gi

    Then
    - Expansion of volume is completed.
    - Share manager pod not restart

    And
    - 1.5 Gi of data is successfully written to the expanded volume.
    """
    pass


def test_rwx_offline_expansion(client, core_api, pvc, make_deployment_with_pvc): # NOQA
    """
    Related issue :
    https://github.com/longhorn/longhorn/issues/2181
    https://github.com/longhorn/longhorn/issues/2484

    This test case does not cover the UI test mentioned in the related issue's
    test steps."

    Given
    - Create a rwx pvc using longhorn storage class of size 1 Gi.

    And
    - Attach it to a workload (deployment) and write some data.
    - Scale down the workload, wait volume detached
    - Share manager pod will terminate automatically
    - Expand the volume to 4 Gi, wait exoansion complete

    When
    - Scale up workload

    Then
    - Share manager pod created
    - Volume healthy

    And
    - 1.5 Gi of data is successfully written to the expanded volume
    """
    pvc_name = 'pvc-deployment-rwx-expand-test'
    pvc['metadata']['name'] = pvc_name
    pvc['spec']['storageClassName'] = 'longhorn'
    pvc['spec']['accessModes'] = ['ReadWriteMany']
    pvc['spec']['resources']['requests']['storage'] = str(1 * Gi)

    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    deployment = make_deployment_with_pvc(
        'deployment-rwx-expand-test', pvc_name, replicas=1)
    apps_api = get_apps_api_client()
    create_and_wait_deployment(apps_api, deployment)

    pv_name = get_volume_name(core_api, pvc_name)
    deployment_label_selector = "name=" + \
                                deployment["metadata"]["labels"]["name"]

    deployment_pod_list = \
        core_api.list_namespaced_pod(namespace="default",
                                     label_selector=deployment_label_selector)

    pod_name = deployment_pod_list.items[0].metadata.name
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name, test_data, filename='test')

    deployment['spec']['replicas'] = 0
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment["metadata"]["name"])

    wait_for_volume_detached(client, pv_name)
    expand_and_wait_for_pvc(core_api, pvc, EXPANDED_VOLUME_SIZE*Gi)
    wait_for_volume_expansion(client, pv_name)
    wait_for_volume_detached(client, pv_name)

    deployment['spec']['replicas'] = 1
    apps_api.patch_namespaced_deployment(body=deployment,
                                         namespace='default',
                                         name=deployment["metadata"]["name"])
    wait_deployment_replica_ready(apps_api, deployment["metadata"]["name"], 1)
    wait_for_volume_healthy(client, pv_name)

    deployment_pod_list = \
        core_api.list_namespaced_pod(namespace="default",
                                     label_selector=deployment_label_selector)
    pod_name = deployment_pod_list.items[0].metadata.name

    # check data written before expansion
    resp = read_volume_data(core_api, pod_name, "test")
    assert resp == test_data

    data_size_in_mb = 1536
    write_pod_volume_random_data(core_api, pod_name, "/data/test2",
                                 data_size_in_mb)
    command = 'stat -c \"%s\" /data/test2'
    data_size_in_pod = exec_command_in_pod(core_api, command,
                                           pod_name,
                                           'default')
    assert int(data_size_in_pod)/1024/1024 == data_size_in_mb


def test_encrypted_rwx_volume(core_api, statefulset, storage_class, crypto_secret, pvc, make_deployment_with_pvc):  # NOQA
    """
    Test creating encrypted rwx volume and use the secret in
    non longhorn-system namespace.

    1. Create crypto secret in non longhorn-system namespace.
    2. Create a storage class.
    3. Create a deployment with a PVC and the pods should be able to running.
    """

    namespace = 'default'
    # Create crypto secret
    secret = crypto_secret(namespace)
    create_crypto_secret(secret, namespace)

    # Create storage class
    storage_class['reclaimPolicy'] = 'Delete'
    storage_class['parameters']['csi.storage.k8s.io/provisioner-secret-name'] = 'longhorn-crypto'  # NOQA
    storage_class['parameters']['csi.storage.k8s.io/provisioner-secret-namespace'] = namespace  # NOQA
    storage_class['parameters']['csi.storage.k8s.io/node-publish-secret-name'] = 'longhorn-crypto'  # NOQA
    storage_class['parameters']['csi.storage.k8s.io/node-publish-secret-namespace'] = namespace  # NOQA
    storage_class['parameters']['csi.storage.k8s.io/node-stage-secret-name'] = 'longhorn-crypto'  # NOQA
    storage_class['parameters']['csi.storage.k8s.io/node-stage-secret-namespace'] = namespace  # NOQA
    create_storage_class(storage_class)

    # Create deployment with PVC
    pvc_name = 'pvc-deployment-with-encrypted-rwx-volume'
    pvc['metadata']['name'] = pvc_name
    pvc['spec']['storageClassName'] = storage_class['metadata']['name']
    pvc['spec']['accessModes'] = ['ReadWriteMany']

    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    deployment = make_deployment_with_pvc(
        'pvc-deployment-with-encrypted-rwx-volume', pvc_name, replicas=3)

    apps_api = get_apps_api_client()
    create_and_wait_deployment(apps_api, deployment)

    # Clean up deployment and volume
    delete_and_wait_deployment(apps_api, deployment["metadata"]["name"])
    delete_and_wait_pvc(core_api, pvc_name)


def test_rwx_volume_mount_options(core_api, storage_class, pvc, make_deployment_with_pvc):  # NOQA
    """
    Test creating rwx volume with custom mount options
    non longhorn-system namespace.

    1. Create a storage class with nfsOptions parameter.
    2. Create a deployment with a PVC and the pods should be able to run.
    3. Check the mounts on the deployment pods.
    """

    # Create storage class
    storage_class['reclaimPolicy'] = 'Delete'
    storage_class['parameters']['nfsOptions'] = 'vers=4.2,soft,noresvport,timeo=600,retrans=4'  # NOQA
    create_storage_class(storage_class)

    # Create deployment with PVC
    pvc_name = 'pvc-deployment-with-custom-mount-options-volume'
    pvc['metadata']['name'] = pvc_name
    pvc['spec']['storageClassName'] = storage_class['metadata']['name']
    pvc['spec']['accessModes'] = ['ReadWriteMany']

    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    deployment = make_deployment_with_pvc(
        'deployment-with-custom-mount-options-volume', pvc_name, replicas=2)

    apps_api = get_apps_api_client()
    create_and_wait_deployment(apps_api, deployment)

    # Check mount options on deployment pods
    deployment_label_selector = "name=" + \
                                deployment["metadata"]["labels"]["name"]

    deployment_pod_list = \
        core_api.list_namespaced_pod(namespace="default",
                                     label_selector=deployment_label_selector)

    assert deployment_pod_list.items.__len__() == 2

    pod_name_1 = deployment_pod_list.items[0].metadata.name
    pod_name_2 = deployment_pod_list.items[1].metadata.name

    command = "cat /proc/mounts | grep 'nfs'"
    mount_options_1 = exec_command_in_pod(core_api, command,
                                          pod_name_1,
                                          'default')
    mount_options_2 = exec_command_in_pod(core_api, command,
                                          pod_name_2,
                                          'default')

    # print(f'mount_options_1={mount_options_1}')
    # print(f'mount_options_2={mount_options_2}')

    assert "vers=4.2" in mount_options_1
    assert "vers=4.2" in mount_options_2

    # Clean up deployment and volume
    delete_and_wait_deployment(apps_api, deployment["metadata"]["name"])
    delete_and_wait_pvc(core_api, pvc_name)
