import time

from node import Node
from metrics.metrics import get_node_metrics, check_longhorn_metric
from metrics.metrics import get_longhorn_components_memory_cpu_usage
from metrics.metrics import check_longhorn_components_memory_cpu_usage
from utility.utility import get_retry_count_and_interval
from utility.utility import logging


class metrics_keywords:

    def __init__(self):
        self.node = Node()
        retry_count, retry_interval = get_retry_count_and_interval()

    def get_node_total_memory_in_mi(self, node_name):
        total_memory = self.node.get_node_total_memory(node_name)
        if "Ki" in total_memory:
            total_memory = int(total_memory.replace("Ki", ""))
            total_memory = total_memory / 1024
        elif "Mi" in total_memory:
            total_memory = int(total_memory.replace("Mi", ""))
        logging(f'Got node {node_name} total memory: {total_memory} Mi')
        return total_memory

    def get_node_memory_usage_in_mi(self, node_name):
        memory_usage = get_node_metrics(node_name, 'memory')
        if "Ki" in memory_usage:
            memory_usage = int(memory_usage.replace("Ki", ""))
            memory_usage = memory_usage / 1024
        elif "Mi" in memory_usage:
            memory_usage = int(memory_usage.replace("Mi", ""))
        logging(f'Got node {node_name} memory usage: {memory_usage} Mi')
        return memory_usage

    def get_node_memory_usage_in_percentage(self, node_name):
        memory_usage_in_mi = self.get_node_memory_usage_in_mi(node_name)
        total_memory_in_mi = self.get_node_total_memory_in_mi(node_name)
        memory_usage_in_percentage = memory_usage_in_mi / total_memory_in_mi * 100
        logging(f'Got node {node_name} memory usage: {memory_usage_in_percentage} %')
        return memory_usage_in_percentage

    def check_if_node_under_memory_pressure(self, node_name):
        logging(f"Checking if node {node_name} is under memory pressure")
        condition_status = self.node.get_node_condition(node_name, "MemoryPressure")
        if condition_status == "True":
            logging(f"Node {node_name} is under memory pressure")
            time.sleep(self.retry_count)
            assert False, f"Node {node_name} is under memory pressure"

    def check_longhorn_metric(self, metric_name, node_name=None, metric_label=None, expected_value=None):
        check_longhorn_metric(metric_name, node_name, metric_label, expected_value)

    def get_longhorn_components_memory_cpu_usage(self):
        get_longhorn_components_memory_cpu_usage()

    def check_longhorn_components_memory_cpu_usage(self):
        check_longhorn_components_memory_cpu_usage()
