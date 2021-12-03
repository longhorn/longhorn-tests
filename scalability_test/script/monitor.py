from datetime import datetime
import dateutil.parser
import json
import matplotlib.pyplot as plt
from kubernetes import client

STS_PREFIX = "sts-"
MONITOR_DATA_FILE_NAME = "monitor_data.txt"

# annotate the point at which the pod starting time is bigger than the maximum allowed value 
MAX_POD_STARTING_TIME_POINT = "max_pod_starting_time_point" 
MAX_POD_CRASHING_POINT = "max_pod_crashing_point" 

class Monitor:
    def __init__(self, core_api_v1, custom_objects_api, updating_interval, node_capacities, preload, sts_count, max_pod_starting_time, max_pod_crashing_count, file_name = MONITOR_DATA_FILE_NAME):
        self.core_api_v1 = core_api_v1
        self.custom_objects_api = custom_objects_api
        self.updating_interval = updating_interval
        self.max_pod_starting_time = max_pod_starting_time
        self.max_pod_crashing_count = max_pod_crashing_count
        self.sts_count = sts_count
        
        self.node_capacities = node_capacities
        
        if preload:
            self.load_data_from_disk(file_name)
        else:
            self.timestamps = []
            self.time_diffs = []
            self.running_pod_metric = []
            self.cpu_metrics = dict() # node_name to cpu_utilization
            self.ram_metrics = dict() # node_name to used_ram
            self.annotating_points = dict()
            self.pods_with_valid_starting_time = dict()
            self.pods_with_invalid_starting_time = dict()

        self.fig, self.axes = plt.subplots(3, 1)
        self.fig.set_size_inches(16, 10)
        self.fig.suptitle('Scale Test')
        notes = """
        Number of StatefulSet: {sts_count} | Max pod starting time: {max_pod_starting_time} seconds | Max pod crashing count: {max_pod_crashing_count}
        (1) The point at which the maximum pod starting time is over the limit 
        (2) The point at which the pod crashing count is over the limit
        """.format(sts_count=self.sts_count, max_pod_starting_time= self.max_pod_starting_time, max_pod_crashing_count=self.max_pod_crashing_count)
        self.fig.text(0.05, 0, notes, va='bottom', ha='left')

    def update_data(self):
        # get running pod count
        pod_list = []
        node_list = []
        try:
            pod_list = self.core_api_v1.list_namespaced_pod("default")
        # TODO: change to catch any exeption and count the number of api exceptions 
        except client.ApiException as e:
            print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)
            print("Skipping this update")
            return

        try:
            node_list = self.custom_objects_api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
        # TODO: change to catch any exeption and count the number of api exceptions
        except client.ApiException as e:
            print("Exception when calling custom_objects_api->list_cluster_custom_object: %s\n" % e)
            print("Will set node metrics to 0")

        now = datetime.now()
        self.timestamps.append(now)
        diff = now-self.timestamps[0]
        self.time_diffs.append(diff.total_seconds())

        
        running_pod_count, pod_with_valid_starting_time_count, crashing_pod_count = self.count_pod_numbers(pod_list)
        
        # update the internal metrics
        self.running_pod_metric.append(running_pod_count)
        if pod_with_valid_starting_time_count < running_pod_count and MAX_POD_STARTING_TIME_POINT not in self.annotating_points:
            self.annotating_points[MAX_POD_STARTING_TIME_POINT] = {
                "xy": (diff.total_seconds(), 
                pod_with_valid_starting_time_count), "desciption": "(1) "+str(pod_with_valid_starting_time_count)+" pods",
                "color": "tab:orange"}
        if crashing_pod_count > self.max_pod_crashing_count and MAX_POD_CRASHING_POINT not in self.annotating_points:
            self.annotating_points[MAX_POD_CRASHING_POINT] = {
                "xy": (diff.total_seconds(), 
                pod_with_valid_starting_time_count), "desciption": "(2) "+str(pod_with_valid_starting_time_count)+" pods",
                "color": "tab:red"}

        for node in node_list['items']:
            node_name = node['metadata']['name']
            if node_name not in self.node_capacities:
                continue
        
            used_cpu_string = node['usage']['cpu']  # an example of cpu_string: 2738210319n
            used_ram_string = node['usage']['memory'] # an example of ram_string: 1889548Ki
            cpu_percent = 100*int(used_cpu_string[:-1])/self.node_capacities[node_name]["cpu"]
            ram_percent = 100*int(used_ram_string[:-2])/self.node_capacities[node_name]["ram"]

            cpu_metric = self.cpu_metrics.get(node_name, [])
            ram_metric = self.ram_metrics.get(node_name, [])
            cpu_metric.append(cpu_percent)
            ram_metric.append(ram_percent)
            self.cpu_metrics[node_name] = cpu_metric
            self.ram_metrics[node_name] = ram_metric

        # update node metrics with value 0 if the infomation is missing in the above update    
        for metric in self.cpu_metrics.values():
            if len(metric) < len(self.time_diffs):
                cpu_metric.extend([0]*(len(self.time_diffs)-len(metric)))
        for metric in self.ram_metrics.values():
            if len(metric) < len(self.time_diffs):
                cpu_metric.extend([0]*(len(self.time_diffs)-len(metric)))

        self.save_data_to_disk()

    def count_pod_numbers(self, pod_list):
        running_pod_count = 0
        pod_with_valid_starting_time_count = 0
        crashing_pod_count = 0
        for pod in pod_list.items:
            if STS_PREFIX not in pod.metadata.name:
                continue

            if (pod and pod.status and pod.status.container_statuses and len(pod.status.container_statuses) > 0 and 
                pod.status.container_statuses[0] and pod.status.container_statuses[0].ready):
                running_pod_count += 1
                if pod.metadata.name in self.pods_with_valid_starting_time:
                    pod_with_valid_starting_time_count += 1
                elif pod.status.container_statuses[0].state and pod.status.container_statuses[0].state.running:
                    created_at = pod.metadata.creation_timestamp
                    started_at = pod.status.container_statuses[0].state and pod.status.container_statuses[0].state.running.started_at
                    diff = started_at - created_at
                    staring_time = diff.total_seconds()
                    if staring_time <= self.max_pod_starting_time:
                        pod_with_valid_starting_time_count += 1
                        self.pods_with_valid_starting_time[pod.metadata.name] = True
                    else:
                        self.pods_with_invalid_starting_time[pod.metadata.name] = True
            # TODO: find a more accurate way to detect crashing
            if (pod and pod.status and pod.status.container_statuses and len(pod.status.container_statuses) > 0 and 
                pod.status.container_statuses[0] and pod.status.container_statuses[0].restart_count > 0):
                crashing_pod_count += 1

        return running_pod_count, pod_with_valid_starting_time_count, crashing_pod_count

    def save_data_to_disk(self):
        # persist the data to disk
        timestamps_isoformat = []
        for ts in self.timestamps:
            timestamps_isoformat.append(ts.isoformat())

        out_str = json.dumps({"timestamps_isoformat": timestamps_isoformat,
        "time_diffs": self.time_diffs,
        "running_pod_metric": self.running_pod_metric,
        "cpu_metrics": self.cpu_metrics,
        "ram_metrics": self.ram_metrics,
        "annotating_points": self.annotating_points,
        "sts_count": self.sts_count,
        "max_pod_starting_time": self.max_pod_starting_time,
        "max_pod_crashing_count": self.max_pod_crashing_count,
        "pods_with_valid_starting_time": self.pods_with_valid_starting_time,
        "pods_with_invalid_starting_time": self.pods_with_invalid_starting_time,
        })

        with open(MONITOR_DATA_FILE_NAME, 'w') as writer:
            writer.write(out_str)

    def load_data_from_disk(self, file_name):
        with open(file_name, 'r') as reader:
            in_str = reader.read()
            decoded_input = json.loads(in_str)
            self.time_diffs = decoded_input["time_diffs"]
            self.running_pod_metric = decoded_input["running_pod_metric"]
            self.cpu_metrics = decoded_input["cpu_metrics"]
            self.ram_metrics = decoded_input["ram_metrics"]
            self.annotating_points = decoded_input["annotating_points"]
            self.sts_count = decoded_input["sts_count"]
            self.max_pod_starting_time = decoded_input["max_pod_starting_time"]
            self.max_pod_crashing_count = decoded_input["max_pod_crashing_count"]
            self.pods_with_valid_starting_time = decoded_input.get("pods_with_valid_starting_time", dict())
            self.pods_with_invalid_starting_time = decoded_input.get("pods_with_invalid_starting_time", dict())
            timestamps_isoformat = decoded_input["timestamps_isoformat"]
            self.timestamps = []
            for ts_isoformat in timestamps_isoformat:
                self.timestamps.append(dateutil.parser.parse(ts_isoformat))
            


    def clear_axes(self):
        for ax in self.axes:
            ax.clear()

    def draw(self):
        ax1, ax2, ax3 = self.axes

        ax1.plot(self.time_diffs, self.running_pod_metric) 
        ax1.set_ylabel('Number of running pods')

        for point in self.annotating_points.values():
            ax1.annotate(point["desciption"],
                xy= point["xy"], xycoords='data',
                xytext=(0, 20), textcoords='offset points',
                arrowprops=dict(facecolor=point["color"], shrink=0.05),
                horizontalalignment='center', verticalalignment='center')

        for node_name in sorted(self.cpu_metrics.keys()):
            ax2.plot(self.time_diffs, self.cpu_metrics[node_name], label = node_name)
        ax2.set_ylabel('CPU usage in percents')
        # ax2.legend(loc="upper left")

        for node_name in sorted(self.ram_metrics.keys()):
            ax3.plot(self.time_diffs, self.ram_metrics[node_name], label = node_name)
        ax3.set_ylabel('RAM usage in percents')
        ax3.set_xlabel('Time in seconds')

    def run(self):
        print("running monitoring loop ...")
        while True:
            self.clear_axes()
            self.update_data()
            self.draw()
            # check the stopping condition and tell the user to check the file for the graph.
            plt.pause(self.updating_interval)

def draw_from_data_file(file_name = MONITOR_DATA_FILE_NAME):
    m = Monitor(None, None, None, None, True, 0, 0, 0, file_name)
    m.draw()
    plt.show()
            