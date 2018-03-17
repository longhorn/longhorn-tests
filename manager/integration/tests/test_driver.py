#!/usr/sbin/python

import time

from common import clients, volume_name  # NOQA
from common import wait_for_volume_delete, wait_for_volume_state

from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.stream import stream
from kubernetes.client import Configuration

Gi = (1 * 1024 * 1024 * 1024)

WAIT_POD_RETRY_COUNTS = 100
WAIT_POD_RETRY_INTERVAL = 1


def create_pod(api, pod_name, volume):
    pod_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': pod_name
        },
        'spec': {
            'containers': [{
                'image': 'busybox',
                'imagePullPolicy': 'IfNotPresent',
                'name': 'sleep',
                "args": [
                    "/bin/sh",
                    "-c",
                    "while true;do date;sleep 5; done"
                ],
                "volumeMounts": [{
                    "name": volume['name'],
                    "mountPath": "/data"
                }],
            }],
            'volumes': [{
                'name': volume['name'],
                'flexVolume': {
                    'driver': 'rancher.io/longhorn',
                    'fsType': 'ext4',
                    'options': {
                        'size': volume['size'],
                        'numberOfReplicas': volume['numberOfReplicas'],
                        'staleReplicaTimeout': volume['staleReplicaTimeout'],
                        'fromBackup': ''
                    }
                }
            }]
        }
    }
    api.create_namespaced_pod(
        body=pod_manifest,
        namespace='default')


def wait_pod_ready(api, pod_name):
    for i in range(WAIT_POD_RETRY_COUNTS):
        pod = api.read_namespaced_pod(
            name=pod_name,
            namespace='default')
        if pod.status.phase != 'Pending':
            break
        time.sleep(WAIT_POD_RETRY_INTERVAL)
    assert pod.status.phase == 'Running'


def delete_pod(api, pod_name):
    api.delete_namespaced_pod(
        name=pod_name,
        namespace='default', body=k8sclient.V1DeleteOptions())


def test_volume_mount(clients, volume_name): # NOQA
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    api = k8sclient.CoreV1Api()

    for _, client in clients.iteritems():
        break
    pod_name = 'volume-driver-mount-test'
    volume_size = 3 * Gi
    volume = {
        'name': volume_name, 'size': str(volume_size >> 30) + 'Gi',
        'numberOfReplicas': '2', 'staleReplicaTimeout': '20'}

    create_pod(api, pod_name, volume)
    wait_pod_ready(api, pod_name)

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == volume["name"]
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == int(volume["numberOfReplicas"])
    assert volumes[0]["state"] == "healthy"

    delete_pod(api, pod_name)
    v = wait_for_volume_state(client, volume["name"], "detached")
    client.delete(v)
    wait_for_volume_delete(client, volume["name"])


def test_volume_io(clients, volume_name):  # NOQA
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    k8sconfig.load_incluster_config()
    api = k8sclient.CoreV1Api()

    for _, client in clients.iteritems():
        break
    pod_name = 'volume-driver-io-test'
    volume_size = 3 * Gi
    volume = {
        'name': volume_name, 'size': str(volume_size >> 30) + 'Gi',
        'numberOfReplicas': '2', 'staleReplicaTimeout': '20'}

    create_pod(api, pod_name, volume)
    wait_pod_ready(api, pod_name)

    test_content = "longhorn"
    write_command = [
        '/bin/sh',
        '-c',
        'echo -ne ' + test_content + ' > /data/test; sync']

    stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=write_command,
        stderr=True, stdin=False,
        stdout=True, tty=False)
    delete_pod(api, pod_name)

    wait_for_volume_state(client, volume["name"], "detached")

    pod_name = 'volume-driver-io-test-2'
    create_pod(api, pod_name, volume)
    wait_pod_ready(api, pod_name)

    read_command = [
        '/bin/sh',
        '-c',
        'cat /data/test']
    resp = stream(
        api.connect_get_namespaced_pod_exec, pod_name, 'default',
        command=read_command,
        stderr=True, stdin=False,
        stdout=True, tty=False)
    assert resp == test_content
    delete_pod(api, pod_name)
    v = wait_for_volume_state(client, volume["name"], "detached")
    client.delete(v)
    wait_for_volume_delete(client, volume["name"])
