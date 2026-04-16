import os
import time

from kubernetes import client
from kubernetes.stream import stream

from node_exec.constant import DEFAULT_POD_INTERVAL
from node_exec.constant import DEFAULT_POD_TIMEOUT
from node_exec.constant import HOST_ROOTFS
from node_exec.constant import FIO_IMAGE, DEFAULT_IMAGE

from utility.utility import logging
from utility.utility import delete_pod, get_pod
from utility.utility import get_retry_count_and_interval


class NodeExec:

    def __init__(self, node_name):
        self.node_name = node_name
        self.core_api = client.CoreV1Api()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def cleanup(self):
        if get_pod(self.node_name):
            logging(f"Cleaning up pod {self.node_name}")
            delete_pod(self.node_name)

    def issue_cmd(self, cmd):

        self.cleanup()

        if self._needs_fio(cmd):
            self.pod = self.launch_pod(FIO_IMAGE)
        else:
            self.pod = self.launch_pod()

        logging(f"Issuing command on {self.node_name}: {cmd}")

        if isinstance(cmd, list):
            exec_command = cmd
        else:
            ns_mnt = os.path.join(HOST_ROOTFS, "proc/1/ns/mnt")
            ns_net = os.path.join(HOST_ROOTFS, "proc/1/ns/net")
            exec_command = [
                'nsenter',
                f'--mount={ns_mnt}',
                f'--net={ns_net}',
                '--', 'sh', '-c', cmd
            ]
        for i in range(self.retry_count):
            try:
                res = stream(
                    self.core_api.connect_get_namespaced_pod_exec,
                    self.pod.metadata.name,
                    'default',
                    command=exec_command,
                    stderr=True,
                    stdin=False,
                    stdout=True,
                    tty=False
                )
                logging(f"Issued command: {cmd} on {self.node_name} with result:\n{res}")
                return res
            except Exception as e:
                logging(f"Failed to issue command: {cmd} on {self.node_name} with error: {e}")
                time.sleep(self.retry_interval)
        assert False, f"Failed to issue command: {cmd} on {self.node_name}"

    def _needs_fio(self, cmd):
        if isinstance(cmd, list):
            return any('fio' in str(part) for part in cmd)
        return 'fio' in str(cmd)

    def launch_pod(self, image_name=None):
        pod_manifest = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': self.node_name
            },
            'spec': {
                'affinity': {
                    'nodeAffinity': {
                        'requiredDuringSchedulingIgnoredDuringExecution': {
                            'nodeSelectorTerms': [{
                                'matchExpressions': [{
                                    'key': 'kubernetes.io/hostname',
                                    'operator': 'In',
                                    'values': [
                                        self.node_name
                                    ]
                                }]
                            }]
                        }
                    }
                },
                "tolerations": [{
                    "key": "node-role.kubernetes.io/control-plane",
                    "operator": "Exists",
                    "effect": "NoSchedule"
                },
                {
                    "key": "node-role.kubernetes.io/control-plane",
                    "operator": "Exists",
                    "effect": "NoExecute"
                },
                # For a rke2 cluster on HAL, the control-plane node is tainted with:
                # node-role.kubernetes.io/etcd:NoExecute
                # node-role.kubernetes.io/control-plane:NoSchedule
                {
                    "key": "node-role.kubernetes.io/etcd",
                    "operator": "Exists",
                    "effect": "NoSchedule"
                },
                {
                    "key": "node-role.kubernetes.io/etcd",
                    "operator": "Exists",
                    "effect": "NoExecute"
                },
                # Allow to schedule on cordoned node to execute command on its host.
                {
                    "key": "node.kubernetes.io/unschedulable",
                    "operator": "Exists",
                    "effect": "NoSchedule"
                }],
                'containers': [{
                    'image': image_name if image_name else DEFAULT_IMAGE,
                    'imagePullPolicy': 'IfNotPresent',
                    'securityContext': {
                        'privileged': True
                    },
                    'name': 'node-exec',
                    'command': ['/bin/bash'],
                    'args': ["-c", "tail -f /dev/null"],
                    "volumeMounts": [{
                        'name': 'rootfs',
                        'mountPath': HOST_ROOTFS
                    }, {
                        'name': 'bus',
                        'mountPath': '/var/run'
                    }, {
                        'name': 'rancher',
                        'mountPath': '/var/lib/rancher'
                    }],
                }],
                'volumes': [{
                    'name': 'rootfs',
                    'hostPath': {
                        'path': '/'
                    }
                }, {
                    'name': 'bus',
                    'hostPath': {
                        'path': '/var/run'
                    }
                }, {
                    'name': 'rancher',
                    'hostPath': {
                        'path': '/var/lib/rancher'
                    }
                }]
            }
        }
        pod = self.core_api.create_namespaced_pod(
            body=pod_manifest,
            namespace='default'
        )
        for i in range(DEFAULT_POD_TIMEOUT):
            pod = self.core_api.read_namespaced_pod(
                    name=self.node_name,
                    namespace='default'
                  )
            if pod is not None and pod.status.phase == 'Running':
                break
            time.sleep(DEFAULT_POD_INTERVAL)
        return pod
