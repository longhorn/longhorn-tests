import time

from kubernetes import client
from kubernetes.stream import stream

from utility.utility import logging
from workload.pod import wait_delete_pod
from utility.utility import wait_delete_ns

from node_exec.constant import DEFAULT_POD_INTERVAL
from node_exec.constant import DEFAULT_POD_TIMEOUT


class NodeExec:

    _instance = None

    @staticmethod
    def get_instance():
        if NodeExec._instance is None:
            NodeExec()
        return NodeExec._instance

    def __init__(self):
        if NodeExec._instance is not None:
            raise Exception('only one NodeExec instance can exist')
        else:
            self.node_exec_pod = {}
            NodeExec._instance = self

    def set_namespace(self, namespace):
        self.core_api = client.CoreV1Api()
        self.namespace = namespace
        self.node_exec_pod = {}
        namespace_manifest = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': self.namespace
            }
        }
        self.core_api.create_namespace(
            body=namespace_manifest
        )
        logging(f"Created namespace {namespace}")

    def cleanup(self):
        for pod in self.node_exec_pod.values():
            logging(f"Cleaning up pod {pod.metadata.name} {pod.metadata.uid}")
            res = self.core_api.delete_namespaced_pod(
                name=pod.metadata.name,
                namespace=self.namespace,
                body=client.V1DeleteOptions()
            )
            wait_delete_pod(pod.metadata.name)
        self.core_api.delete_namespace(
            name=self.namespace
        )
        wait_delete_ns(self.namespace)
        self.node_exec_pod.clear()


    def issue_cmd(self, node_name, cmd):
        logging(f"Issuing command: {cmd} on {node_name}")
        pod = self.launch_pod(node_name)
        if isinstance(cmd, list):
            exec_command = cmd
        else:
            exec_command = [
                'nsenter',
                '--mount=/rootfs/proc/1/ns/mnt',
                '--net=/rootfs/proc/1/ns/net',
                '--',
                'sh',
                '-c',
                cmd
            ]
        res = stream(
            self.core_api.connect_get_namespaced_pod_exec,
            pod.metadata.name,
            self.namespace,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        logging(f"Issued command: {cmd} on {node_name} with result {res}")
        return res

    def launch_pod(self, node_name):
        if node_name in self.node_exec_pod:
            for i in range(DEFAULT_POD_TIMEOUT):
                pod = self.core_api.read_namespaced_pod(
                        name=node_name,
                        namespace=self.namespace
                      )
                if pod is not None and pod.status.phase == 'Running':
                    break
                time.sleep(DEFAULT_POD_INTERVAL)
            return pod
        else:
            pod_manifest = {
                'apiVersion': 'v1',
                'kind': 'Pod',
                'metadata': {
                    'name': node_name
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
                                            node_name
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
                            'mountPath': '/rootfs'
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
                namespace=self.namespace
            )
            for i in range(DEFAULT_POD_TIMEOUT):
                pod = self.core_api.read_namespaced_pod(
                        name=node_name,
                        namespace=self.namespace
                      )
                if pod is not None and pod.status.phase == 'Running':
                    break
                time.sleep(DEFAULT_POD_INTERVAL)
            self.node_exec_pod[node_name] = pod
            return pod