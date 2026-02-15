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

    def cleanup(self):
        if get_pod(self.node_name):
            logging(f"Cleaning up pod {self.node_name}")
            delete_pod(self.node_name)

    def issue_cmd(self, cmd):

        self.cleanup()
        self.pod = self.launch_pod()

        if self._needs_fio(cmd):
            fio_ready = False
            for i in range(120):
                try:
                    # Check if fio is available using bash
                    path_result = stream(
                        self.core_api.connect_get_namespaced_pod_exec,
                        self.pod.metadata.name,
                        'default',
                        command=['/bin/bash', '-c', 'which fio 2>&1'],
                        stderr=True, stdin=False, stdout=True, tty=False
                    )
                    
                    if path_result and path_result.strip() and '/fio' in path_result:
                        # Verify fio is executable
                        version_result = stream(
                            self.core_api.connect_get_namespaced_pod_exec,
                            self.pod.metadata.name,
                            'default',
                            command=['/bin/bash', '-c', 'fio --version 2>&1'],
                            stderr=True, stdin=False, stdout=True, tty=False
                        )
                        
                        if version_result and 'fio' in version_result.lower():
                            fio_ready = True
                            logging(f"fio is ready in node-exec pod on {self.node_name}")
                            break
                            
                except Exception as e:
                    if i % 10 == 0:
                        logging(f"Waiting for fio to be available... ({i}s)")
                    time.sleep(1)
                    continue
                    
                time.sleep(1)

            if not fio_ready:
                raise Exception(f"fio not available in node-exec pod on {self.node_name} after 120 seconds")

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
        logging(f"Issued command: {cmd} on {self.node_name} with result:\n{res}")
        return res

    def _needs_fio(self, cmd):
        if isinstance(cmd, list):
            return any('fio' in str(part) for part in cmd)
        return 'fio' in str(cmd)

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
                    "key": "node-role.kubernetes.io/control-plane",
                    "operator": "Exists",
                    "effect": "NoSchedule"
                },
                {
                    "key": "node-role.kubernetes.io/control-plane",
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
                    'image': 'ubuntu:22.04',
                    'imagePullPolicy': 'IfNotPresent',
                    'securityContext': {
                        'privileged': True
                    },
                    'name': 'node-exec',
                    'command': ['/bin/bash'],
                    'args': ['-c', 'set -e; apt-get update -qq && apt-get install -y -qq fio && tail -f /dev/null'],
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
