import time
import logging

from volume import Volume
from utility import Utility, globalVars
from node import Nodes, Operations
from node_exec import NodeExec
from kubernetes.client.rest import ApiException

class steps:

    ROBOT_LIBRARY_SCOPE = 'TEST'

    def __init__(self):
        return

    def set_test_suite_environment(self):
        logging.info('setting test suite environment')
        globalVars.initialize_variables()
        Utility.init_k8s_api_client()
        return

    def set_test_environment(self, test_name):
        logging.info('setting test case environment')
        Nodes.refresh_node_list()

        self.namespace = test_name.lower().replace(' ', '-')
        self.node_exec = NodeExec(self.namespace)
        self.volume = Volume(self.node_exec)

        cloud_provider = globalVars.variables["CLOUD_PROVIDER"]
        logging.info(f'getting the cloud provider: {cloud_provider}')
        self.node_operation = Operations(cloud_provider)

    def create_volume(self, size, replica_count, volume_type='RWO'):
        volume_name = Utility.generate_volume_name()
        if volume_name == "":
            raise Exception("failed to generate volume name")

        logging.info(f'creating {size} Gb {volume_type} volume {volume_name} with {replica_count} replicas')
        self.volume.create(volume_name, size, replica_count, volume_type)
        return volume_name

    def attach_volume(self, volume_name, node_index=0):
        node_name = Nodes.get_name_by_index(int(node_index))
        if volume_name == "":
            raise Exception(f"failed: volume_name: {volume_name} is empty")
        logging.info(f'attaching the volume {volume_name} to the node {node_name}')

        self.volume.attach(volume_name, node_name)
        return node_name

    def get_non_volume_attached_node(self, attached_node_name):
        logging.info('getting node without volume attached')
        nodes = Nodes.all_nodes
        for node in nodes:
            node_name = node['name']
            if node_name != attached_node_name:
                logging.info(f' volume attached node:{node_name}')
                return node_name
        logging.info('cannot find the node without volume attached')

    def write_volume_random_data(self, volume_name, size_in_mb):
        logging.info(f'writing {size_in_mb} mb data into volume {volume_name} mount point')
        return self.volume.write_random_data(volume_name, size_in_mb)

    def get_volume_end_point(self, volume_name):
        logging.info(f'gettting volume {volume_name} end point')
        return self.volume.get_endpoint(volume_name)

    def check_data(self, volume_name, checksum):
        print(f"checking volume {volume_name} data with checksum {checksum}")
        self.volume.check_data(volume_name, checksum)

    def delete_replica(self, volume_name, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f"deleting volume {volume_name}'s replica on the node {node_name}")
        self.volume.delete_replica(volume_name, node_name)

    def wait_for_replica_rebuilding_start(self, volume_name, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f"waiting the {volume_name} replica on node {node_name} rebuilding start")
        self.volume.wait_for_replica_rebuilding_start(volume_name, node_name)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f"waiting the {volume_name} replica on node {node_name} rebuilding complete")
        self.volume.wait_for_replica_rebuilding_complete(volume_name, node_name)

    def cleanup_resources(self):
        logging.info('cleaning up resources')
        self.node_exec.cleanup()
        self.node_operation.cleanup()
        self.volume.clean_up()

    def power_off_node(self, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f"powering off the node {node_name}")
        self.node_operation.power_off_node(node_name=node_name)

    def power_on_node(self, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f"powering on the node {node_name}")
        self.node_operation.power_on_node(node_name=node_name)

    def get_node_state(self, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f"getting the node {node_name} state")
        return Nodes.get_node_state(node_name)

    def get_node_replica_count(self, node_index, volume_name):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f'getting the volume {volume_name} replica count on the node {node_name}')
        response = self.volume.get_replica(volume_name, node_name)
        replicas = response['items']
        logging.debug(f'replicas: {replicas}')
        return len(replicas)

    def get_volume_state(self, volume_name):
        logging.info(f"getting the volume {volume_name} state")
        return self.volume.get_volume_state(volume_name)

    def get_engine_state(self, volume_name, node_name):
        logging.info(f"getting the volume {volume_name} engine on the node {node_name} state")

        resp = self.volume.get_engine(volume_name, node_name)
        if resp == "" or resp is None:
            raise Exception(f"failed to get the volume {volume_name} engine")

        engines = resp["items"]
        if len(engines) == 0:
            logging.warning(f"cannot get the volume {volume_name} engines")
            return

        engines_states = {}
        for engine in engines:
            engine_name = engine["metadata"]["name"]
            engine_state = engine['status']['currentState']
            logging.debug(f"engine {engine_name} state {engine_state}")
            engines_states[engine_name] = engine_state
        return engines_states

    def get_replica_state(self, volume_name, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f"getting the volume {volume_name} replica on the node {node_name} state")

        resp = self.volume.get_replica(volume_name, node_name)
        if resp == "":
            raise Exception(f"failed to get the volume {volume_name} replicas")

        replicas = resp["items"]
        if len(replicas) == 0:
            logging.warning(f"cannot get the volume {volume_name} replicas")
            return

        replicas_states = {}
        for replica in replicas:
            replica_name = replica["metadata"]["name"]
            replica_state = replica['status']['currentState']
            logging.debug(f"replica {replica_name} state {replica_state}")
            replicas_states[replica_name] = replica_state
        return replicas_states

    def check_workload_state(self, current_states, expect_state):
        logging.info(f"checking the workload state {current_states} is same as {expect_state}")
        for state in current_states:
            if current_states[state] != expect_state:
                raise Exception(f'name: {state}: {current_states[state]} != {expect_state}')
        logging.info("passed the workload state chcking")

    def wait_with_time_interval(self, time_interval):
        logging.info(f"sleeping {time_interval} seconds")
        time.sleep(int(time_interval))

    def get_cluster_node_index(self, volume_name, expected_replica_count):
        logging.info(f"getting the whole cluster nodes index")
        cluster_nodes = []
        cluster_nodes.extend(self.get_with_replica_node(volume_name, expected_replica_count))
        cluster_nodes.extend(self.get_no_replica_node(volume_name, expected_replica_count))
        logging.debug(f"cluster nodes: {cluster_nodes}")
        return cluster_nodes

    def get_no_replica_node(self, volume_name, expected_replica_count):
        logging.info(f"getting the nodes without any replicas")
        nodes = Nodes.all_nodes
        current_replica_count = 0
        count = 1
        while expected_replica_count != current_replica_count and count <= 180:
            replicas = self.volume.get_replica(volume_name,"")
            current_replica_count = len(replicas)
            count += 1

        # get the node without replica on it
        no_replica_nodes = []
        no_replica_nodes_name = []
        for node in nodes:
            node_name = node['name']
            replica = self.volume.get_replica(volume_name, node_name)
            if len(replica["items"]) == 0:
                no_replica_nodes.append(Nodes.get_index_by_name(node_name))
                no_replica_nodes_name.append(node_name)

        logging.debug(f'without replica nodes: {no_replica_nodes_name}')
        return no_replica_nodes

    def get_with_replica_node(self, volume_name, expected_replica_count):
        logging.info(f"getting the nodes have replicas")
        nodes = Nodes.all_nodes
        current_replica_count = 0
        count = 1
        while expected_replica_count != current_replica_count and count <= 180:
            replicas = self.volume.get_replica(volume_name,"")
            current_replica_count = len(replicas["items"])
            count += 1

        time.sleep(30)

        with_replica_nodes = []
        with_replica_nodes_name = []
        for node in nodes:
            node_name = node['name']
            replica = self.volume.get_replica(volume_name, node_name)
            if len(replica["items"]) != 0:
                with_replica_nodes.append(Nodes.get_index_by_name(node_name))
                with_replica_nodes_name.append(node_name)

        if len(with_replica_nodes) == 0:
            raise Exception("can not find node with replica")

        logging.debug(f'with replica nodes: {with_replica_nodes_name}')
        return with_replica_nodes

    def generate_support_bundle(self, case_name):
        logging.info(f"generating support bundle for {case_name}")
        Utility.generate_support_bundle(case_name)

    def reboot_node(self, node_index):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f"rebooting the node {node_name}")
        self.node_operation.reboot_node(node_name)

    def restart_kubelet(self, node_index, interval_time):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f'restart kubelet on the node {node_name}')
        self.node_operation.restart_kubelet(node_name, interval_time)

    def update_setting_custom_resource(self, setting_name, setting_value):
        logging.info(f"update the setting {setting_name} value as {setting_value}")
        client = globalVars.K8S_CR_API_CLIENT
        try:
            api_response = client.patch_namespaced_custom_object(
                                group="longhorn.io",
                                version="v1beta2",
                                namespace="longhorn-system",
                                plural="settings",
                                name=setting_name,
                                body={ "value": setting_value }
                            )
            logging.debug(f'update result: {api_response}')
        except ApiException as e:
            Exception("Exception: %s\n" % e)

    def during_data_writing_interrupt_network(self, node_index, time_interval, volume_name):
        node_name = Nodes.get_name_by_index(int(node_index))
        if node_name == "":
            raise Exception(f"failed to get node name with index {node_index}")

        logging.info(f'interrupting the node {node_name} network for {time_interval} seconds')
        volume_end_point = self.get_volume_end_point(volume_name)
        self.node_operation.writing_data_interrupt_network_concurrent(node_name, time_interval, volume_end_point)
