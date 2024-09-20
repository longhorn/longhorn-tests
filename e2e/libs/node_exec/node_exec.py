import os
import time

from kubernetes import client
from kubernetes.stream import stream

from node_exec.constant import DEFAULT_POD_INTERVAL
from node_exec.constant import DEFAULT_POD_TIMEOUT
from node_exec.constant import HOST_ROOTFS

from utility.utility import logging
from utility.utility import delete_pod, get_pod


class NodeExec:

    def __init__(self, node_name):
        self.node_name = node_name
        self.core_api = client.CoreV1Api()
        self.cleanup()
        self.pod = self.launch_pod()

    def cleanup(self):
        if get_pod(self.node_name):
            logging(f"Cleaning up pod {self.node_name}")
            delete_pod(self.node_name)

    def issue_cmd(self, cmd):
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
        logging(f"Issued command: {cmd} on {self.node_name} with result {res}")
        return res

    def launch_pod(self):
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
                    "key": "node-role.kubernetes.io/master",
                    "operator": "Equal",
                    "value": "true",
                    "effect": "NoSchedule"
                },
                {
                    "key": "node-role.kubernetes.io/master",
                    "operator": "Equal",
                    "value": "true",
                    "effect": "NoExecute"
                },
                {
                    "key": "node-role.kubernetes.io/control-plane",
                    "operator": "Equal",
                    "value": "true",
                    "effect": "NoSchedule"
                },
                {
                    "key": "node-role.kubernetes.io/control-plane",
                    "operator": "Equal",
                    "value": "true",
                    "effect": "NoExecute"
                }],
                'containers': [{
                    'image': 'ubuntu:16.04',
                    'imagePullPolicy': 'IfNotPresent',
                    'securityContext': {
                        'privileged': True
                    },
                    'name': 'node-exec',
                    "args": [
                        "tail", "-f", "/dev/null"
                    ],
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
