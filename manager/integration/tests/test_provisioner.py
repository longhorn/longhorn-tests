import pytest
import common

from common import client, core_api, node_default_tags, pod, pvc, storage_class  # NOQA
from common import DEFAULT_VOLUME_SIZE, Gi, VOLUME_RWTEST_SIZE
from common import create_and_wait_pod, create_pvc_spec, delete_and_wait_pod
from common import generate_random_data, get_storage_api_client
from common import get_volume_name, read_volume_data, size_to_string
from common import write_pod_volume_data, check_volume_replicas
from common import SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY

DEFAULT_STORAGECLASS_NAME = "longhorn-provisioner"


def create_storage(api, sc_manifest, pvc_manifest):
    # type: (dict, dict)
    """Create a StorageClass and PersistentVolumeClaim for testing."""
    s_api = get_storage_api_client()
    s_api.create_storage_class(
        body=sc_manifest
    )

    api.create_namespaced_persistent_volume_claim(
        body=pvc_manifest,
        namespace='default')

@pytest.mark.coretest   # NOQA
def test_provisioner_mount(client, core_api, storage_class, pvc, pod):  # NOQA
    """
    Test that a StorageClass provisioned volume can be created, mounted,
    unmounted, and deleted properly on the Kubernetes cluster.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.

    1. Create a StorageClass, PVC and Pod
    2. Verify the pod is up and volume parameters.
    """

    # Prepare pod and volume specs.
    pod_name = 'provisioner-mount-test'
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [
        create_pvc_spec(pvc['metadata']['name'])
    ]
    pvc['spec']['storageClassName'] = DEFAULT_STORAGECLASS_NAME
    storage_class['metadata']['name'] = DEFAULT_STORAGECLASS_NAME
    volume_size = DEFAULT_VOLUME_SIZE * Gi

    create_storage(core_api, storage_class, pvc)
    create_and_wait_pod(core_api, pod)
    pvc_volume_name = get_volume_name(core_api, pvc['metadata']['name'])

    # Confirm that the volume has all the correct parameters we gave it.
    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes.data[0].name == pvc_volume_name
    assert volumes.data[0].size == str(volume_size)
    assert volumes.data[0].numberOfReplicas == \
        int(storage_class['parameters']['numberOfReplicas'])
    assert volumes.data[0].state == "attached"


def test_provisioner_params(client, core_api, storage_class, pvc, pod):  # NOQA
    """
    Test that substituting different StorageClass parameters is reflected in
    the resulting PersistentVolumeClaim.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.

    1. Create a StorageClass with replica 2 (instead of 3) etc.
    2. Create PVC and Pod using it.
    3. Verify the volume's parameter matches the Storage Class.
    """

    # Prepare pod and volume specs.
    pod_name = 'provisioner-params-test'
    volume_size = 2 * Gi
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [
        create_pvc_spec(pvc['metadata']['name'])
    ]
    pvc['spec']['resources']['requests']['storage'] = \
        size_to_string(volume_size)
    pvc['spec']['storageClassName'] = DEFAULT_STORAGECLASS_NAME
    storage_class['metadata']['name'] = DEFAULT_STORAGECLASS_NAME
    storage_class['parameters'] = {
        'numberOfReplicas': '2',
        'staleReplicaTimeout': '20'
    }

    create_storage(core_api, storage_class, pvc)
    create_and_wait_pod(core_api, pod)
    pvc_volume_name = get_volume_name(core_api, pvc['metadata']['name'])

    # Confirm that the volume has all the correct parameters we gave it.
    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes.data[0].name == pvc_volume_name
    assert volumes.data[0].size == str(volume_size)
    assert volumes.data[0].numberOfReplicas == \
        int(storage_class['parameters']['numberOfReplicas'])
    assert volumes.data[0].state == "attached"


def test_provisioner_io(client, core_api, storage_class, pvc, pod):  # NOQA
    """
    Test that input and output on a StorageClass provisioned
    PersistentVolumeClaim works as expected.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.

    1. Create a StorageClass, PVC and Pod.
    2. Wait for pod to be up.
    3. Write data to the pod
    4. Delete the original pod and create a new one using the same PVC
    5. Read the data from the new pod, verify the data.
    """

    # Prepare pod and volume specs.
    pod_name = 'provisioner-io-test'
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [
        create_pvc_spec(pvc['metadata']['name'])
    ]
    pvc['spec']['storageClassName'] = DEFAULT_STORAGECLASS_NAME
    storage_class['metadata']['name'] = DEFAULT_STORAGECLASS_NAME
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    create_storage(core_api, storage_class, pvc)
    create_and_wait_pod(core_api, pod)
    pvc_volume_name = get_volume_name(core_api, pvc['metadata']['name'])
    write_pod_volume_data(core_api, pod_name, test_data)
    delete_and_wait_pod(core_api, pod_name)

    common.wait_for_volume_detached(client, pvc_volume_name)

    pod_name = 'provisioner-io-test-2'
    pod['metadata']['name'] = pod_name
    create_and_wait_pod(core_api, pod)
    resp = read_volume_data(core_api, pod_name)

    assert resp == test_data


def test_provisioner_tags(client, core_api, node_default_tags, storage_class, pvc, pod):  # NOQA
    """
    Test that a StorageClass can properly provision a volume with requested
    Tags.

    Test prerequisite:
      - set Replica Node Level Soft Anti-Affinity enabled

    1. Use `node_default_tags` to add default tags to nodes.
    2. Create a StorageClass with disk and node tag set.
    3. Create PVC and Pod.
    4. Verify the volume has the correct parameters and tags.
    """

    replica_node_soft_anti_affinity_setting = \
        client.by_id_setting(SETTING_REPLICA_NODE_SOFT_ANTI_AFFINITY)
    client.update(replica_node_soft_anti_affinity_setting, value="true")

    # Prepare pod and volume specs.
    pod_name = 'provisioner-tags-test'
    tag_spec = {
        "disk": ["ssd", "nvme"],
        "expected": 1,
        "node": ["storage", "main"]
    }

    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [
        create_pvc_spec(pvc['metadata']['name'])
    ]
    pvc['spec']['storageClassName'] = DEFAULT_STORAGECLASS_NAME
    storage_class['metadata']['name'] = DEFAULT_STORAGECLASS_NAME
    storage_class['parameters']['diskSelector'] = 'ssd,nvme'
    storage_class['parameters']['nodeSelector'] = 'storage,main'
    volume_size = DEFAULT_VOLUME_SIZE * Gi

    create_storage(core_api, storage_class, pvc)
    create_and_wait_pod(core_api, pod)
    pvc_volume_name = get_volume_name(core_api, pvc['metadata']['name'])

    # Confirm that the volume has all the correct parameters we gave it.
    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes.data[0].name == pvc_volume_name
    assert volumes.data[0].size == str(volume_size)
    assert volumes.data[0].numberOfReplicas == \
        int(storage_class['parameters']['numberOfReplicas'])
    assert volumes.data[0].state == "attached"
    check_volume_replicas(volumes.data[0], tag_spec, node_default_tags)


@pytest.mark.skip(reason="TODO")
def test_provisioner_fs_format():
    """
    Context: https://github.com/longhorn/longhorn/issues/4642
    This is to test the FS format options are configured as mentioned in
    the storage class.

    1. Deploy a new storage class 'longhorn-test' with mkfsParams param.
    2. Deploy a PVC and POD with the above storage class.
    3. A Longhorn volume should get created, verify the Inode size and
       block size. They should be same as the mkfsParams parameter.

    """
