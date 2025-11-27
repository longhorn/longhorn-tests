import time

from node import Node
from node_exec import NodeExec

from utility.utility import convert_size_to_bytes
from utility.utility import init_k8s_api_client
from utility.utility import generate_name_with_suffix
from utility.utility import pod_exec
from utility.utility import logging
from utility.utility import subprocess_exec_cmd
from utility.utility import get_retry_count_and_interval
from utility.utility import set_longhorn_namespace
from utility.utility import get_longhorn_namespace


class common_keywords:

    def __init__(self):
        pass

    def init_k8s_api_client(self):
        init_k8s_api_client()

    def generate_name_with_suffix(self, kind, suffix):
        return generate_name_with_suffix(kind, suffix)

    def get_worker_nodes(self):
        return Node().list_node_names_by_role("worker")

    def get_control_plane_node(self):
        return Node().list_node_names_by_role("control-plane")[0]

    def set_longhorn_namespace(self, ns):
        set_longhorn_namespace(ns)

    def reset_longhorn_namespace(self):
        set_longhorn_namespace('longhorn-system')

    def get_longhorn_namespace(self):
        return get_longhorn_namespace()

    def get_node_by_index(self, node_id):
        return Node().get_node_by_index(node_id)

    def cleanup_node_exec(self):
        for node_name in Node().list_node_names_by_role("all"):
            NodeExec(node_name).cleanup()

    def convert_size_to_bytes(self, size, to_str=False):
        if to_str:
            return str(convert_size_to_bytes(size))
        return convert_size_to_bytes(size)

    def pod_exec(self, pod_name, namespace, cmd):
        return pod_exec(pod_name, namespace, cmd)

    def execute_command(self, cmd):
        subprocess_exec_cmd(cmd)

    def execute_command_and_expect_output(self, cmd, output):
        res = subprocess_exec_cmd(cmd)
        retry_count, _ = get_retry_count_and_interval()
        if output not in res:
            logging(f"Failed to find {output} in {cmd} result: {res}")
            time.sleep(retry_count)
            assert False, f"Failed to find {output} in {cmd} result: {res}"

    def execute_command_and_wait_for_output(self, cmd, output):
        retry_count, retry_interval = get_retry_count_and_interval()
        for i in range(retry_count):
            logging(f"Waiting for command {cmd} returning output {output} ... ({i})")
            try:
                res = subprocess_exec_cmd(cmd)
                if output in res:
                    return
            except Exception as e:
                logging(f"Execute command {cmd} and wait for output {output} error: {e}")
            time.sleep(retry_interval)
        assert False, f"Failed to wait for command {cmd} returning output {output}"

    def execute_command_and_not_expect_output(self, cmd, output):
        res = subprocess_exec_cmd(cmd)
        retry_count, _ = get_retry_count_and_interval()
        if output in res:
            logging(f"Unexpected {output} in {cmd} result: {res}")
            time.sleep(retry_count)
            assert False, f"Unexpected {output} in {cmd} result: {res}"
