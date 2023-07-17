import logging

from node import Nodes
from node_exec import NodeExec
from utils import config_utils, common_utils
from engine.engine import Engine
from replica import Replica
from volume import Volume

class common_keywords:

    node_operation_instance = None
    node_exec_instance = None
    engine_instance = None
    replica_instance = None
    volume_instance = None

    @classmethod
    def set_test_suite_environment(cls):
        logging.info('setting test suite environment')
        config_utils.Config()
        return

    @classmethod
    def set_test_environment(cls, test_name):
        logging.info('setting test case environment')
        Nodes.refresh_node_list()

        namespace = test_name.lower().replace(' ', '-')
        cls.node_exec_instance = NodeExec(namespace)
        cls.engine_instance = Engine()
        cls.replica_instance = Replica(cls.node_exec_instance)
        cls.volume_instance = Volume(cls.node_exec_instance)

        cloud_provider = config_utils.Config.get("CLOUD_PROVIDER")
        cls.node_operation_instance = Nodes(cloud_provider)._instance

    def generate_support_bundle(self, case_name):
        logging.info(f"generating support bundle for {case_name}")
        common_utils.generate_support_bundle(case_name)

    def check_workload_state(self, current_states, expect_state):
        if current_states == None:
            return

        logging.info(f"checking the workload state {current_states} is same as {expect_state}")
        for state in current_states:
            assert current_states[state] == expect_state, f'{current_states[state]} != {expect_state}'

        logging.info("passed the workload state chcking")

    @classmethod
    def cleanup_resources(cls):
        logging.info('cleaning up resources')
        cls.node_exec_instance.cleanup()
        cls.node_operation_instance.power_on_node_instance()
        cls.replica_instance.delete_replica()
        cls.engine_instance.delete_engine()
        cls.volume_instance.delete()