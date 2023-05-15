import pytest

from common import client, core_api, pvc, pod  # NOQA
from common import create_and_wait_pod, create_pvc_spec
from common import get_pvc_manifest, delete_and_wait_pod, get_core_api_client
from common import write_pod_volume_random_data, get_pod_data_md5sum
from common import DATA_SIZE_IN_MB_2, wait_for_volume_healthy, get_volume_name
from common import wait_for_volume_clone_status, VOLUME_FIELD_STATE
from common import VOLUME_FIELD_CLONE_COMPLETED, wait_for_pvc_phase
from common import get_self_host_id, write_volume_random_data
from common import wait_for_volume_detached, check_volume_data
from common import crash_replica_processes
from common import delete_and_wait_pvc, wait_for_volume_attached
from common import generate_random_suffix, wait_for_volume_endpoint
from common import wait_for_snapshot_count, DATA_SIZE_IN_MB_3
from common import get_clone_volume_name
from common import create_storage_class, storage_class  # NOQA
from common import wait_for_volume_degraded
from common import wait_for_volume_status


# Kept some fixtures specifically for volume cloning module to avoid cleaning
# the test resources manually. Fixtures should take care of cleanup.
@pytest.fixture
def clone_pvc(request):
    return get_pvc_manifest(request)


@pytest.fixture
def clone_pod(request):
    pod_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': 'test-pod'
        },
        'spec': {
            'containers': [{
                'image': 'busybox:1.34.0',
                'imagePullPolicy': 'IfNotPresent',
                'name': 'sleep',
                "args": [
                    "/bin/sh",
                    "-c",
                    "while true;do date;sleep 5; done"
                ],
                "volumeMounts": [{
                    'name': 'pod-data',
                    'mountPath': '/data'
                }],
            }],
            'volumes': []
        }
    }

    def finalizer():
        api = get_core_api_client()
        delete_and_wait_pod(api, pod_manifest['metadata']['name'])

    request.addfinalizer(finalizer)

    return pod_manifest


@pytest.mark.cloning  # NOQA
def test_cloning_basic(client, core_api, pvc, pod, clone_pvc, clone_pod, storage_class_name='longhorn'):  # NOQA
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
              storage: 3Gi
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
              storage: 3Gi
        ```
    5. Wait for the `CloneStatus.State` in `cloned-pvc` to be `completed`
    6. Clone volume should get detached after cloning completion, wait for it.
    7. Specify the `cloned-pvc` in a cloned pod yaml and deploy the cloned pod
    8. In 3-min retry loop, wait for the cloned pod to be running
    9. Verify the data in `cloned-pvc` is the same as in `source-pvc`
    10. In 2-min retry loop, verify the volume of the `clone-pvc` eventually
       becomes healthy
    """
    # Step-1
    source_pvc_name = 'source-pvc' + generate_random_suffix()
    pvc['metadata']['name'] = source_pvc_name
    pvc['spec']['storageClassName'] = storage_class_name
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')
    wait_for_pvc_phase(core_api, source_pvc_name, "Bound")

    # Step-2
    pod_name = 'source-pod' + generate_random_suffix()
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [create_pvc_spec(source_pvc_name)]
    create_and_wait_pod(core_api, pod)

    # Step-3
    write_pod_volume_random_data(core_api, pod_name,
                                 '/data/test', DATA_SIZE_IN_MB_2)
    source_data = get_pod_data_md5sum(core_api, pod_name, '/data/test')

    # Step-4
    clone_pvc_name = 'clone-pvc' + generate_random_suffix()
    clone_pvc['metadata']['name'] = clone_pvc_name
    clone_pvc['spec']['storageClassName'] = storage_class_name
    clone_pvc['spec']['dataSource'] = {
        'name': source_pvc_name,
        'kind': 'PersistentVolumeClaim'
    }
    core_api.create_namespaced_persistent_volume_claim(
        body=clone_pvc, namespace='default')
    wait_for_pvc_phase(core_api, clone_pvc_name, "Bound")

    # Step-5
    clone_volume_name = get_volume_name(core_api, clone_pvc_name)
    wait_for_volume_clone_status(client, clone_volume_name, VOLUME_FIELD_STATE,
                                 VOLUME_FIELD_CLONE_COMPLETED)

    # Step-6
    wait_for_volume_detached(client, clone_volume_name)

    # Step-7,8
    clone_pod_name = 'clone-pod' + generate_random_suffix()
    clone_pod['metadata']['name'] = clone_pod_name
    clone_pod['spec']['volumes'] = [create_pvc_spec(clone_pvc_name)]
    create_and_wait_pod(core_api, clone_pod)
    clone_data = get_pod_data_md5sum(core_api, clone_pod_name, '/data/test')

    # Step-9
    assert source_data == clone_data

    # Step-10
    wait_for_volume_healthy(client, clone_volume_name)


@pytest.mark.cloning
def test_cloning_with_detached_source_volume(client, core_api, pvc, clone_pvc):  # NOQA
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
        2. Wait for volume to be created and attach it to a node.
        3. Write some data to the mount path of the volume
        4. Detach the volume and wait for the volume to be in detached state.
        5. Clone a volume by creating the PVC:
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
        6. Wait for `source-pvc` to be attached
        7. Wait for the `CloneStatus.State` in `cloned-pvc` to be `completed`
        8. Wait for `source-pvc` to be detached
        9. Attach the cloned volume to a node
        10. Verify the data in `cloned-pvc` is the same as in `source-pvc`.
        11. In 2-min retry loop, verify the volume of the `clone-pvc`
            eventually becomes healthy.
        12. Verify snapshot created in `source-pvc` volume because of the clone
    """
    # Step-1
    source_pvc_name = 'source-pvc' + generate_random_suffix()
    pvc['metadata']['name'] = source_pvc_name
    pvc['spec']['storageClassName'] = 'longhorn'
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')
    wait_for_pvc_phase(core_api, source_pvc_name, "Bound")

    # Step-2
    source_volume_name = get_volume_name(core_api, source_pvc_name)
    lht_host_id = get_self_host_id()
    source_volume = client.by_id_volume(source_volume_name)
    source_volume.attach(hostId=lht_host_id)
    source_volume = wait_for_volume_healthy(client, source_volume_name)

    # Step-3
    data = write_volume_random_data(source_volume)

    # Steps-4
    source_volume.detach(hostId=lht_host_id)
    wait_for_volume_detached(client, source_volume_name)

    # Step-5
    clone_pvc_name = 'clone-pvc' + generate_random_suffix()
    clone_pvc['metadata']['name'] = clone_pvc_name
    clone_pvc['spec']['storageClassName'] = 'longhorn'
    clone_pvc['spec']['dataSource'] = {
        'name': source_pvc_name,
        'kind': 'PersistentVolumeClaim'
    }
    core_api.create_namespaced_persistent_volume_claim(
        body=clone_pvc, namespace='default')
    wait_for_pvc_phase(core_api, clone_pvc_name, "Bound")

    # Step-6
    source_volume = wait_for_volume_attached(client, source_volume_name)

    # Step-7
    clone_volume_name = get_volume_name(core_api, clone_pvc_name)
    wait_for_volume_clone_status(client, clone_volume_name, VOLUME_FIELD_STATE,
                                 VOLUME_FIELD_CLONE_COMPLETED)
    wait_for_volume_detached(client, clone_volume_name)

    # Step-8
    wait_for_volume_detached(client, source_volume_name)

    # Step-9
    clone_volume = client.by_id_volume(clone_volume_name)
    clone_volume.attach(hostId=lht_host_id)
    wait_for_volume_attached(client, clone_volume_name)
    clone_volume = wait_for_volume_endpoint(client, clone_volume_name)

    # Step-10
    check_volume_data(clone_volume, data)

    # Step-11
    wait_for_volume_healthy(client, clone_volume_name)

    # Step-12
    source_volume = client.by_id_volume(source_volume_name)
    source_volume.attach(hostId=lht_host_id)
    source_volume = wait_for_volume_attached(client, source_volume_name)
    wait_for_snapshot_count(source_volume, 2)


@pytest.mark.cloning  # NOQA
def test_cloning_with_backing_image(client, core_api, pvc, pod, clone_pvc, clone_pod, storage_class):  # NOQA
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
        backingImageDataSourceType: "download"
        backing_image_data_source_parameters = (
          '{"url": "https://backing-image-example.s3-region.amazonaws.com/'
          'test-backing-image"}'
        )
      ```
    2. Repeat the `test_cloning_without_backing_image()` test with
       `source-pvc` and `cloned-pvc` use `longhorn-bi-parrot` instead of
       `longhorn` storageclass
    3. Clean up the test
    """

    # Create storage class with backing image
    backing_img_storage_class_name = 'longhorn-bi-parrot'
    storage_class['metadata']['name'] = backing_img_storage_class_name
    storage_class['parameters']['backingImage'] = 'bi-parrot'
    storage_class['parameters']['backingImageDataSourceType'] = 'download'
    storage_class['parameters']['backingImageDataSourceParameters'] = (
        '{"url": "https://longhorn-backing-image.s3-us-west-1.amazonaws.com/'
        'parrot.qcow2"}')
    storage_class['reclaimPolicy'] = 'Delete'

    create_storage_class(storage_class)
    test_cloning_basic(client, core_api, pvc, pod, clone_pvc, clone_pod,
                       storage_class_name=backing_img_storage_class_name)


@pytest.mark.cloning  # NOQA
def test_cloning_interrupted(client, core_api, pvc, pod, clone_pvc, clone_pod):  # NOQA
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
              storage: 3Gi
        ```
    2. Specify the `source-pvc` in a pod yaml and start the pod
    3. Wait for the pod to be running, write 500MB of data to the mount
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
              storage: 3Gi
        ```
    5. Wait for the `CloneStatus.State` in `cloned-pvc` to be `initiated`
    6. Kill all replicas process of the `source-pvc`
    7. Wait for the `CloneStatus.State` in `cloned-pvc` to be `failed`
    8. Clean up `clone-pvc`
    9. Redeploy `cloned-pvc` and clone pod
    10. In 3-min retry loop, verify cloned pod become running
    11. `cloned-pvc` has the same data as `source-pvc`
    12. In 2-min retry loop, verify the volume of the `clone-pvc`
        eventually becomes healthy.
    """
    # Step-1
    source_pvc_name = 'source-pvc' + generate_random_suffix()
    pvc['metadata']['name'] = source_pvc_name
    pvc['spec']['storageClassName'] = 'longhorn'
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')
    wait_for_pvc_phase(core_api, source_pvc_name, "Bound")

    # Step-2
    pod_name = 'source-pod' + generate_random_suffix()
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [create_pvc_spec(source_pvc_name)]
    create_and_wait_pod(core_api, pod)

    # Step-3
    write_pod_volume_random_data(core_api, pod_name,
                                 '/data/test', DATA_SIZE_IN_MB_3)
    source_data = get_pod_data_md5sum(core_api, pod_name, '/data/test')

    source_volume_name = get_volume_name(core_api, source_pvc_name)

    # Step-4
    clone_pvc_name = 'clone-pvc' + generate_random_suffix()
    clone_pvc['metadata']['name'] = clone_pvc_name
    clone_pvc['spec']['storageClassName'] = 'longhorn'
    clone_pvc['spec']['dataSource'] = {
        'name': source_pvc_name,
        'kind': 'PersistentVolumeClaim'
    }
    core_api.create_namespaced_persistent_volume_claim(
        body=clone_pvc, namespace='default')

    # Step-5
    clone_volume_name = get_clone_volume_name(client, source_volume_name)
    wait_for_volume_clone_status(client, clone_volume_name, VOLUME_FIELD_STATE,
                                 'initiated')

    # Step-6
    wait_for_volume_degraded(client, clone_volume_name)
    crash_replica_processes(client, core_api, source_volume_name)

    # Step-7
    # This is a workaround, since in some case it's hard to
    # catch faulted volume status
    wait_for_volume_status(client, source_volume_name,
                           VOLUME_FIELD_STATE,
                           'attaching')
    wait_for_volume_clone_status(client, clone_volume_name, VOLUME_FIELD_STATE,
                                 'failed')

    # Step-8
    delete_and_wait_pvc(core_api, clone_pvc_name)

    # Step-9
    clone_pvc_name = 'clone-pvc-2' + generate_random_suffix()
    clone_pvc['metadata']['name'] = clone_pvc_name
    clone_pvc['spec']['storageClassName'] = 'longhorn'
    clone_pvc['spec']['dataSource'] = {
        'name': source_pvc_name,
        'kind': 'PersistentVolumeClaim'
    }
    core_api.create_namespaced_persistent_volume_claim(
        body=clone_pvc, namespace='default')
    wait_for_pvc_phase(core_api, clone_pvc_name, "Bound")

    # Step-9
    clone_pod_name = 'clone-pod' + generate_random_suffix()
    clone_pod['metadata']['name'] = clone_pod_name
    clone_pod['spec']['volumes'] = [create_pvc_spec(clone_pvc_name)]
    create_and_wait_pod(core_api, clone_pod)

    # Step-10
    clone_volume_name = get_volume_name(core_api, clone_pvc_name)
    wait_for_volume_clone_status(client, clone_volume_name, VOLUME_FIELD_STATE,
                                 VOLUME_FIELD_CLONE_COMPLETED)

    # Step-11
    clone_data = get_pod_data_md5sum(core_api, clone_pod_name, '/data/test')
    assert source_data == clone_data

    # Step-12
    wait_for_volume_healthy(client, clone_volume_name)
