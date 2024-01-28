import time

from workload.pod import create_pod
from workload.pod import delete_pod
from workload.pod import new_pod_manifest
from workload.constant import IMAGE_UBUNTU

from utility.utility import subprocess_exec_cmd

def delete_node(node_name):
    exec_cmd = ["kubectl", "delete", "node", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def drain_node(node_name):
    exec_cmd = ["kubectl", "drain", node_name, "--ignore-daemonsets", "--delete-emptydir-data"]
    res = subprocess_exec_cmd(exec_cmd)

def force_drain_node(node_name):
    exec_cmd = ["kubectl", "drain", node_name, "--force", "--ignore-daemonsets", "--delete-emptydir-data"]
    res = subprocess_exec_cmd(exec_cmd)

def cordon_node(node_name):
    exec_cmd = ["kubectl", "cordon", node_name]
    res = subprocess_exec_cmd(exec_cmd)

def uncordon_node(node_name):
    exec_cmd = ["kubectl", "uncordon", node_name]
    res = subprocess_exec_cmd(exec_cmd)
