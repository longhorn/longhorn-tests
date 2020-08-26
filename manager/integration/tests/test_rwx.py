import pytest
from common import (generate_random_data, VOLUME_RWTEST_SIZE,
                    delete_and_wait_pvc, create_storage_class,
                    create_and_wait_statefulset, write_pod_volume_data,
                    get_core_api_client, get_longhorn_api_client,
                    delete_and_wait_deployment, check_pvc_existence,
                    wait_for_volume_delete, wait_deployment_replica_ready,
                    get_apps_api_client, delete_storage_class,
                    timeout, get_volume_name, create_and_wait_pod,
                    create_pvc_spec, cleanup_client,
                    create_and_wait_deployment, wait_statefulset,
                    DEFAULT_STATEFULSET_TIMEOUT, DEFAULT_STATEFULSET_INTERVAL,
                    write_pod_volume_random_data, DATA_SIZE_IN_MB_3,
                    get_pod_data_md5sum)
from common import core_api, statefulset, pvc, pod, make_deployment_with_pvc  # NOQA
from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import Configuration
from kubernetes.stream import stream
import time
from multiprocessing import Pool

NFS_STORAGECLASS_NAME = 'longhorn-nfs-test'
STREAM_EXEC_TIMEOUT = 60
NFS_TEST_DATA = generate_random_data(VOLUME_RWTEST_SIZE)


@pytest.fixture(scope="module", autouse="True")
def deployment_nfs(request):
    deployment_nfs_manifest = {
       "kind": "Deployment",
       "apiVersion": "apps/v1",
       "metadata": {
          "name": "longhorn-nfs-provisioner",
          "namespace": "longhorn-system"
       },
       "spec": {
          "selector": {
             "matchLabels": {
                "app": "longhorn-nfs-provisioner"
             }
          },
          "replicas": 1,
          "strategy": {
             "type": "Recreate"
          },
          "template": {
             "metadata": {
                "labels": {
                   "app": "longhorn-nfs-provisioner"
                }
             },
             "spec": {
                "serviceAccount": "longhorn-nfs-provisioner",
                "containers": [
                   {
                      "name": "longhorn-nfs-provisioner",
                      "image": "quay.io/kubernetes_incubator/nfs-provisioner:latest",  # NOQA
                      "ports": [
                         {
                            "name": "nfs",
                            "containerPort": 2049
                         },
                         {
                            "name": "nfs-udp",
                            "containerPort": 2049,
                            "protocol": "UDP"
                         },
                         {
                            "name": "nlockmgr",
                            "containerPort": 32803
                         },
                         {
                            "name": "nlockmgr-udp",
                            "containerPort": 32803,
                            "protocol": "UDP"
                         },
                         {
                            "name": "mountd",
                            "containerPort": 20048
                         },
                         {
                            "name": "mountd-udp",
                            "containerPort": 20048,
                            "protocol": "UDP"
                         },
                         {
                            "name": "rquotad",
                            "containerPort": 875
                         },
                         {
                            "name": "rquotad-udp",
                            "containerPort": 875,
                            "protocol": "UDP"
                         },
                         {
                            "name": "rpcbind",
                            "containerPort": 111
                         },
                         {
                            "name": "rpcbind-udp",
                            "containerPort": 111,
                            "protocol": "UDP"
                         },
                         {
                            "name": "statd",
                            "containerPort": 662
                         },
                         {
                            "name": "statd-udp",
                            "containerPort": 662,
                            "protocol": "UDP"
                         }
                      ],
                      "securityContext": {
                         "capabilities": {
                            "add": [
                               "DAC_READ_SEARCH",
                               "SYS_RESOURCE"
                            ]
                         }
                      },
                      "args": [
                         "-provisioner=nfs.longhorn.io",
                         "-device-based-fsids=false"
                      ],
                      "env": [
                         {
                            "name": "POD_IP",
                            "valueFrom": {
                               "fieldRef": {
                                  "fieldPath": "status.podIP"
                               }
                            }
                         },
                         {
                            "name": "SERVICE_NAME",
                            "value": "longhorn-nfs-provisioner"
                         },
                         {
                            "name": "POD_NAMESPACE",
                            "valueFrom": {
                               "fieldRef": {
                                  "fieldPath": "metadata.namespace"
                               }
                            }
                         }
                      ],
                      "imagePullPolicy": "IfNotPresent",
                      "readinessProbe": {
                         "exec": {
                            "command": [
                               "ls",
                               "/export"
                            ]
                         },
                         "initialDelaySeconds": 5,
                         "periodSeconds": 5
                      },
                      "livenessProbe": {
                         "exec": {
                            "command": [
                               "ls",
                               "/export"
                            ]
                         },
                         "initialDelaySeconds": 5,
                         "periodSeconds": 5
                      },
                      "volumeMounts": [
                         {
                            "name": "export-volume",
                            "mountPath": "/export"
                         }
                      ]
                   }
                ],
                "volumes": [
                   {
                      "name": "export-volume",
                      "persistentVolumeClaim": {
                         "claimName": "longhorn-nfs-provisioner"
                      }
                   }
                ],
                "terminationGracePeriodSeconds": 30,
                "tolerations": [
                   {
                      "effect": "NoExecute",
                      "key": "node.kubernetes.io/not-ready",
                      "operator": "Exists",
                      "tolerationSeconds": 60
                   },
                   {
                      "effect": "NoExecute",
                      "key": "node.kubernetes.io/unreachable",
                      "operator": "Exists",
                      "tolerationSeconds": 60
                   }
                ]
             }
          }
       }
    }

    def finalizer():
        api = get_apps_api_client()
        delete_and_wait_deployment(api, 'longhorn-nfs-provisioner',
                                   namespace='longhorn-system')

    request.addfinalizer(finalizer)

    return deployment_nfs_manifest


@pytest.fixture(scope="module", autouse="True")
def nfs_pvc(request):
    pvc_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': 'longhorn-nfs-provisioner',
            'namespace': 'longhorn-system'
        },
        'spec': {
            'storageClassName': 'longhorn',
            'accessModes': [
                'ReadWriteOnce'
            ],
            'resources': {
                'requests': {
                    'storage': '10G'
                }
            }
        }
    }

    def finalizer():
        api = k8sclient.CoreV1Api()
        client = get_longhorn_api_client()
        volumes = client.list_volume()

        if not check_pvc_existence(api, pvc_manifest['metadata']['name'],
                                   namespace='longhorn-system'):
            return

        volume_name = ''
        for v in volumes:
            if v.kubernetesStatus.pvcName == 'longhorn-nfs-provisioner':
                volume_name = v.name
                client.delete(v)
                break
        wait_for_volume_delete(client, volume_name)

        core_api_client = get_core_api_client()
        delete_and_wait_pvc(core_api_client, pvc_manifest['metadata']['name'])

    request.addfinalizer(finalizer)

    return pvc_manifest


@pytest.fixture(scope="module", autouse="True")
def nfs_storage_class(request):
    sc_manifest = {
        'apiVersion': 'storage.k8s.io/v1',
        'kind': 'StorageClass',
        'metadata': {
            'name': NFS_STORAGECLASS_NAME
        },
        'provisioner': 'nfs.longhorn.io',
        'mountOptions': [
            'vers=4.1',
            'noresvport'
        ]
    }

    def finalizer():
        delete_storage_class(NFS_STORAGECLASS_NAME)

    request.addfinalizer(finalizer)

    return sc_manifest


@pytest.fixture(scope="module", autouse="True")  # NOQA
def core_api_module(request):
    """
    Create a new CoreV1API instance.
    Returns:
        A new CoreV1API Instance.
    """
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    core_api = k8sclient.CoreV1Api()  # NOQA

    cleanup_client()

    return core_api


@pytest.fixture(scope="module", autouse="True")
def apps_api_module(request):
    """
    Create a new AppsV1API instance.
    Returns:
        A new AppsV1API Instance.
    """
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    apps_api = k8sclient.AppsV1Api()

    return apps_api


@pytest.fixture(scope="module", autouse="True")
def longhorn_nfs_provisioner_setup(core_api_module, apps_api_module, nfs_pvc,
                                   nfs_storage_class, deployment_nfs):
    """
    Deploy longhorn-nfs-provisioner pod and volume
    """

    create_storage_class(nfs_storage_class)
    core_api_module.create_namespaced_persistent_volume_claim(
        body=nfs_pvc, namespace='longhorn-system')
    apps_api_module.create_namespaced_deployment(namespace='longhorn-system',
                                                 body=deployment_nfs)
    wait_deployment_replica_ready(apps_api_module, 'longhorn-nfs-provisioner',
                                  1, namespace='longhorn-system')
    # This is to make sure nfs server is started.
    time.sleep(25)


def read_nfs_provisioner_data(api, command, pod_name, namespace):
    """
    Retrieve data from a Pod's volume.

    Args:
        api: An instance of CoreV1API.
        pod_name: The name of the Pod.
        command: The command to execute in the pod.
        namespace: The namespace where the pod exists.

    Returns:
        The data contained within the volume.
    """
    exec_command = [
        '/bin/sh',
        '-c',
        command
    ]
    with timeout(seconds=STREAM_EXEC_TIMEOUT,
                 error_message='Timeout on executing stream read'):
        return stream(
            api.connect_get_namespaced_pod_exec, pod_name, namespace,
            command=exec_command, stderr=True, stdin=False, stdout=True,
            tty=False)


def write_data_into_pod(pod_name):
    core_api = get_core_api_client()  # NOQA
    write_pod_volume_random_data(core_api, pod_name, "/data/test",
                                 DATA_SIZE_IN_MB_3)


def test_rwx_with_statefulset_multi_pods(core_api, nfs_storage_class, statefulset):  # NOQA
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

    nfs_provisioner_pod = k8sclient.CoreV1Api().list_pod_for_all_namespaces(
        label_selector="app=longhorn-nfs-provisioner", watch=False)
    nfs_provisioner_pod_name = nfs_provisioner_pod.items[0].metadata.name

    statefulset_name = 'statefulset-rwx-multi-pods-test'
    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = NFS_STORAGECLASS_NAME

    create_and_wait_statefulset(statefulset)

    command = "ls /export | grep -i 'pvc' | wc -l"

    dir_num = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')

    assert dir_num == '2'

    md5sum_pod = []
    for i in range(2):
        test_pod_name = statefulset_name + '-' + str(i)
        test_data = generate_random_data(VOLUME_RWTEST_SIZE)
        write_pod_volume_data(core_api, test_pod_name, test_data)
        md5sum_pod.append(test_data)

    for i in range(2):
        pvc_name = \
            statefulset['spec']['volumeClaimTemplates'][0]['metadata']['name']\
            + '-' + statefulset_name + '-' + str(i)
        volume_name = get_volume_name(core_api, pvc_name)
        command = 'cat /export' + '/' + volume_name + '/' + 'test'
        pod_data = read_nfs_provisioner_data(
            core_api, command, nfs_provisioner_pod_name, 'longhorn-system')

        assert pod_data == md5sum_pod[i]


def test_rwx_multi_statefulset_with_same_pvc(core_api, nfs_storage_class, statefulset, pod):  # NOQA
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
    nfs_provisioner_pod = k8sclient.CoreV1Api().list_pod_for_all_namespaces(
        label_selector="app=longhorn-nfs-provisioner", watch=False)
    nfs_provisioner_pod_name = nfs_provisioner_pod.items[0].metadata.name

    statefulset_name = 'statefulset-rwx-same-pvc-test'
    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = NFS_STORAGECLASS_NAME
    statefulset['spec']['replicas'] = 1

    create_and_wait_statefulset(statefulset)

    command = "ls /export | grep -i 'pvc' | wc -l"

    dir_num = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')

    assert dir_num == '1'

    test_pod_name = statefulset_name + '-0'
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, test_pod_name, test_data, filename='test1')

    pvc_name = \
        statefulset['spec']['volumeClaimTemplates'][0]['metadata']['name'] \
        + '-' + statefulset_name + '-0'
    volume_name = get_volume_name(core_api, pvc_name)

    pod_2_name = 'pod2-rwx-same-pvc-test'
    pod['metadata']['name'] = pod_2_name
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)

    command = 'cat /data/test1'
    pod_data_2 = read_nfs_provisioner_data(
        core_api, command, pod_2_name, 'default')

    assert test_data == pod_data_2

    test_data_2 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_2_name, test_data_2, filename='test2')

    command = 'cat /export' + '/' + volume_name + '/' + 'test1'
    nfs_pod_data_1 = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')
    assert test_data == nfs_pod_data_1

    command = 'cat /export' + '/' + volume_name + '/' + 'test2'
    nfs_pod_data_2 = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')

    assert test_data_2 == nfs_pod_data_2


def test_rwx_parallel_writing(core_api, nfs_storage_class, statefulset, pvc, pod):  # NOQA
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
    nfs_provisioner_pod = k8sclient.CoreV1Api().list_pod_for_all_namespaces(
        label_selector="app=longhorn-nfs-provisioner", watch=False)
    nfs_provisioner_pod_name = nfs_provisioner_pod.items[0].metadata.name

    statefulset_name = 'statefulset-parallel-write-test'
    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = NFS_STORAGECLASS_NAME
    statefulset['spec']['replicas'] = 1

    create_and_wait_statefulset(statefulset)

    statefuleset_pod_name = statefulset_name + '-0'
    statefuleset_pvc_name = \
        statefulset['spec']['volumeClaimTemplates'][0]['metadata']['name'] \
        + '-' + statefulset_name + '-0'
    statefulset_volume_name = get_volume_name(core_api, statefuleset_pvc_name)

    pvc_name = 'pvc-parallel-write-test'
    pvc['metadata']['name'] = pvc_name
    pvc['spec']['storageClassName'] = NFS_STORAGECLASS_NAME
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    pod_name = 'pod-parallel-write-test'
    pod['metadata']['name'] = pod_name
    pod['spec']['volumes'] = [create_pvc_spec(pvc_name)]
    create_and_wait_pod(core_api, pod)
    pod_volume_name = get_volume_name(core_api, pvc_name)

    with Pool(2) as p:
        p.map(write_data_into_pod, [pod_name, statefuleset_pod_name])

    md5sum1 = get_pod_data_md5sum(core_api, statefuleset_pod_name, 'data/test')
    md5sum2 = get_pod_data_md5sum(core_api, pod_name, 'data/test')

    command = 'md5sum /export' + '/' + statefulset_volume_name + '/' + 'test' \
              + " | awk '{print $1}'"
    nfs_pod_data = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')

    assert md5sum1 == nfs_pod_data

    command = 'md5sum /export' + '/' + pod_volume_name + '/' + 'test' \
              + " | awk '{print $1}'"
    nfs_pod_data = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')

    assert md5sum2 == nfs_pod_data


def test_rwx_statefulset_scale_down_up(core_api, nfs_storage_class, statefulset):  # NOQA
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
    nfs_provisioner_pod = k8sclient.CoreV1Api().list_pod_for_all_namespaces(
        label_selector="app=longhorn-nfs-provisioner", watch=False)
    nfs_provisioner_pod_name = nfs_provisioner_pod.items[0].metadata.name

    statefulset_name = 'statefulset-rwx-scale-down-up-test'
    statefulset['metadata']['name'] = \
        statefulset['spec']['selector']['matchLabels']['app'] = \
        statefulset['spec']['serviceName'] = \
        statefulset['spec']['template']['metadata']['labels']['app'] = \
        statefulset_name
    statefulset['spec']['volumeClaimTemplates'][0]['spec']['storageClassName']\
        = NFS_STORAGECLASS_NAME

    create_and_wait_statefulset(statefulset)

    command = "ls /export | grep -i 'pvc' | wc -l"

    dir_num = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')

    assert dir_num == '2'

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
        if s_set.status.ready_replicas == replicas or \
                (replicas == 0 and not s_set.status.ready_replicas):
            break
        time.sleep(DEFAULT_STATEFULSET_INTERVAL)

    dir_num = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')
    assert dir_num == '2'

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
        pod_data = read_nfs_provisioner_data(
            core_api, command, test_pod_name, 'default')

        assert pod_data == md5sum_pod[i]


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


def test_rwx_deployment_with_multi_pods(core_api, nfs_storage_class, pvc, make_deployment_with_pvc):  # NOQA
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
    nfs_provisioner_pod = k8sclient.CoreV1Api().list_pod_for_all_namespaces(
        label_selector="app=longhorn-nfs-provisioner", watch=False)
    nfs_provisioner_pod_name = nfs_provisioner_pod.items[0].metadata.name

    pvc_name = 'pvc-deployment-multi-pods-test'
    pvc['metadata']['name'] = pvc_name
    pvc['spec']['storageClassName'] = NFS_STORAGECLASS_NAME
    core_api.create_namespaced_persistent_volume_claim(
        body=pvc, namespace='default')

    deployment = make_deployment_with_pvc(
        'deployment-multi-pods-test', pvc_name, replicas=2)
    apps_api = get_apps_api_client()
    create_and_wait_deployment(apps_api, deployment)

    volume_name = get_volume_name(core_api, pvc_name)
    deployment_label_selector = \
        "name=" + deployment["metadata"]["labels"]["name"]

    deployment_pod_list = \
        core_api.list_namespaced_pod(namespace="default",
                                     label_selector=deployment_label_selector)

    assert deployment_pod_list.items.__len__() == 2

    pod_name_1 = deployment_pod_list.items[0].metadata.name
    test_data_1 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name_1, test_data_1, filename='test1')

    pod_name_2 = deployment_pod_list.items[1].metadata.name
    command = 'cat /data/test1'
    pod_data_2 = read_nfs_provisioner_data(
        core_api, command, pod_name_2, 'default')

    assert test_data_1 == pod_data_2

    test_data_2 = generate_random_data(VOLUME_RWTEST_SIZE)
    write_pod_volume_data(core_api, pod_name_2, test_data_2, filename='test2')

    command = 'cat /export' + '/' + volume_name + '/' + 'test1'
    nfs_pod_data_1 = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')
    assert test_data_1 == nfs_pod_data_1

    command = 'cat /export' + '/' + volume_name + '/' + 'test2'
    nfs_pod_data_2 = read_nfs_provisioner_data(
        core_api, command, nfs_provisioner_pod_name, 'longhorn-system')

    assert test_data_2 == nfs_pod_data_2
