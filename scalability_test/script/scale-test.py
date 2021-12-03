from os import times
from typing import Dict
from matplotlib.pyplot import get
import time
from re import S
import sys
import asyncio
import logging
from pathlib import Path
from asyncio.tasks import sleep
from kubernetes import client, config, watch
import monitor

NAMESPACE = "default"
TEMPLATE_FILE = "statefulset.yaml"
STS_PREFIX = "sts-"
IMAGE = "phanle1010/ubuntu:fio"
KUBE_CONFIG = None
KUBE_CONTEXT = None
MAX_POD_STARTING_TIME = 300 # in seconds
MAX_POD_CRASHING_COUNT = 0

def get_node_capacities():
    v1 = client.CoreV1Api()
    node_capacities = dict()
    ret = v1.list_node(watch=False)
    for i in ret.items:
        # example of i.status.capacity:
        #   capacity:
        #     cpu: '8'
        #     ephemeral-storage: 20263484Ki
        #     hugepages-1Gi: '0'
        #     hugepages-2Mi: '0'
        #     memory: 32412804Ki
        #     pods: '110'
        cpu = int(i.status.capacity["cpu"])*1000**3 # conver to nano cpu
        ram = int(i.status.capacity["memory"][:-2]) 
        node_capacities[i.metadata.name] = {"cpu": cpu, "ram": ram}

    return node_capacities    

def get_node_name_list():
    v1 = client.CoreV1Api()
    node_names = []
    ret = v1.list_node(watch=False)
    for i in ret.items:
        if i.metadata.labels.get("node-role.kubernetes.io/worker", False) or i.metadata.labels.get("node-role.longhorn.io/worker", False):
         node_names.append(i.metadata.name)
    return node_names    

def get_sts_objects(api):
    sts_list = api.list_namespaced_stateful_set("default")
    return [sts for sts in sts_list.items if STS_PREFIX in sts.metadata.name]

def create_sts_objects(node_names, workload_type):
    # @NODE_NAME@ - schedule each sts on a dedicated node
    # @STS_NAME@ - also used for the volume-name
    sts_objects = []
    for node_name in node_names:
        sts_objects.append(create_sts_spec(node_name, workload_type))
    return sts_objects

def create_sts_yaml(node_name):
    content = Path(TEMPLATE_FILE).read_text()
    content = content.replace("@NODE_NAME@", node_name)
    sts_name = STS_PREFIX + node_name
    content = content.replace("@STS_NAME@",  sts_name)
    file = Path("out/" + sts_name + ".yaml")
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)
    logging.info("created %s" % sts_name)

def get_workload_command(workload_type, sts_name):
    workloads = {
    "non_io": "while : ; do echo 'sleep 30s'; sleep 30; done",
    "io_1": "while : ; do fio --name=simulate-workload-io --ioengine=libaio --direct=1 --readwrite=randrw --bs=128k --size=3G --io_size=2G --filename=/mnt/"+sts_name+"/fio_test_file --iodepth=4 --rwmixread=75; sync; sleep 15; done",
    "io_2": "while : ; do fio --name=simulate-workload-io --ioengine=libaio --direct=1 --readwrite=randrw --bs=128k --size=3G --io_size=2G --filename=/mnt/"+sts_name+"/fio_test_file --iodepth=16 --rwmixread=75; sync; sleep 15; done",
    "io_3": "while : ; do fio --name=simulate-workload-io --ioengine=libaio --direct=1 --readwrite=randrw --bs=128k --size=3G --io_size=2G --filename=/mnt/"+sts_name+"/fio_test_file --iodepth=32 --rwmixread=75; sync; sleep 15; done",
    }
    return workloads.get(workload_type, None)

# create_sts_spec returns a list of need to deploy statefulsets
def create_sts_spec(node_name, workload_type) :
    sts_name = STS_PREFIX + node_name
    cmd = get_workload_command(workload_type, sts_name)
    container = client.V1Container(
        name=sts_name,
        image=IMAGE,
        command=["/bin/bash"],
        args=["-c", cmd],
        liveness_probe=client.V1Probe(
            _exec=client.V1ExecAction(
                command=["ls", "/mnt/"+sts_name]
            ),
            initial_delay_seconds=5,
            period_seconds=5
        ),
        volume_mounts=[client.V1VolumeMount(
            name=sts_name,
            mount_path="/mnt/"+sts_name
        )]
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app":sts_name}),
        spec=client.V1PodSpec(
            node_name=node_name,
            restart_policy="Always",
            termination_grace_period_seconds=10,
            containers=[container],

        )
    )

    spec = client.V1StatefulSetSpec(
        replicas=0,
        service_name=sts_name,
        selector=client.V1LabelSelector(
            match_labels={"app":sts_name}
        ),
        template=template,
        volume_claim_templates=[client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=sts_name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                storage_class_name="longhorn",
                resources=client.V1ResourceRequirements(
                    requests={"storage":"4Gi"}
                )
            )
        )]
    )

    statefulset=client.V1StatefulSet(
        api_version="apps/v1",
        kind="StatefulSet",
        metadata=client.V1ObjectMeta(name=sts_name),
        spec=spec
    )
    statefulset.spec.replicas

    return statefulset

def create_statefulsets(api, sts_objects):
    for sts in sts_objects:
        api.create_namespaced_stateful_set(namespace="default", body=sts)

def scale_statefulsets(api, sts_objects, n):
    for sts in sts_objects:
        sts = api.read_namespaced_stateful_set(name=sts.metadata.name, namespace="default")
        sts.spec.replicas = n
        api.patch_namespaced_stateful_set(name=sts.metadata.name, namespace="default", body=sts)
        
        

async def watch_pods_async():
    log = logging.getLogger('pod_events')
    log.setLevel(logging.INFO)
    v1 = client.CoreV1Api()
    w = watch.Watch()
    for event in w.stream(v1.list_namespaced_pod, namespace=NAMESPACE):
        process_pod_event(log, event)
        await asyncio.sleep(0)


def process_pod_event(log, event):
    log.info("Event: %s %s %s" % (event['type'], event['object'].kind, event['object'].metadata.name))
    if 'ADDED' in event['type']:
        pass
    elif 'DELETED' in event['type']:
        pass
    else:
        pass


async def watch_pvc_async():
    log = logging.getLogger('pvc_events')
    log.setLevel(logging.INFO)
    v1 = client.CoreV1Api()
    v1.list_namespaced_pod()
    w = watch.Watch()
    for event in w.stream(v1.list_namespaced_persistent_volume_claim, namespace=NAMESPACE):
        process_pvc_event(log, event)
        await asyncio.sleep(0)


def process_pvc_event(log, event):
    log.info("Event: %s %s %s" % (event['type'], event['object'].kind, event['object'].metadata.name))
    if 'ADDED' in event['type']:
        pass
    elif 'DELETED' in event['type']:
        pass
    else:
        pass


async def watch_va_async():
    log = logging.getLogger('va_events')
    log.setLevel(logging.INFO)
    storage = client.StorageV1Api()
    w = watch.Watch()
    for event in w.stream(storage.list_volume_attachment):
        process_va_event(log, event)
        await asyncio.sleep(0)


def process_va_event(log, event):
    log.info("Event: %s %s %s" % (event['type'], event['object'].kind, event['object'].metadata.name))
    if 'ADDED' in event['type']:
        pass
    elif 'DELETED' in event['type']:
        pass
    else:
        pass


if __name__ == '__main__':
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(stream=sys.stdout,
                        level=logging.INFO,
                        format=log_format)

    operation = input("Choose an operation (scale, monitor, all, dry_draw): ")

    if operation == "dry_draw":
        file_name = input("Enter file name: ")
        if file_name:
            monitor.draw_from_data_file(file_name)
        else:
            monitor.draw_from_data_file()
        sys.exit(0)
    
    config.load_kube_config(config_file=KUBE_CONFIG,
                            context=KUBE_CONTEXT)
    apps_v1 = client.AppsV1Api()
    core_api_v1 = client.CoreV1Api()
    custom_objects_ppi = client.CustomObjectsApi()

    if operation == "scale":
        count =  input("How many replicas per StatefulSet? ")
        count = int(count)
        sts_objects = get_sts_objects(apps_v1)
        scale_statefulsets(apps_v1, sts_objects, count)
        print("Scaled %d statefulsets so that each has %d replicas" % (len(sts_objects), count))
    elif operation == "monitor":
        preload = input("preload (yes)? ")   
        sts_objects = get_sts_objects(apps_v1)         
        m = monitor.Monitor(core_api_v1, custom_objects_ppi, 5, get_node_capacities(), preload == "yes", len(sts_objects), MAX_POD_STARTING_TIME, MAX_POD_CRASHING_COUNT)
        m.run()
    elif operation == "all":
        workload_type = input("workload type (non_io, io_1, io_2, io_3) ")
        if not get_workload_command(workload_type, ""):
            print("invalid workload type")
            sys.exit(1)
        
        count =  input("How many replicas per StatefulSet? ")
        count = int(count)

        node_names = get_node_name_list()
        sts_objects = create_sts_objects(node_names, workload_type)

        create_statefulsets(apps_v1, sts_objects)
        print("Created %d statefulsets" % (len(sts_objects)))

        print("sleeping for 15s")
        time.sleep(15)
        
        scale_statefulsets(apps_v1, sts_objects, count)
        print("Scaled %d statefulsets so that each has %d replicas" % (len(sts_objects), count))

        m = monitor.Monitor(core_api_v1, custom_objects_ppi, 5, get_node_capacities(), False, len(sts_objects), MAX_POD_STARTING_TIME, MAX_POD_CRASHING_COUNT)
        m.run()
    else:
        print(operation + "is an invalid operation")


    
    # Make a different command for: cleanup
    # Make the top value up 
    




    # logging.info("scale-test started")
    # datastructures to keep track of the timings
    # TODO: process events and keep track of the results
    #       results should be per pod/volume
    #       information to keep track: pod index per sts
    #       volume-creation time per pod
    #       volume-attach time per pod
    #       volume-detach time per pod
    # pvc_to_va_map = dict()
    # pvc_to_pod_map = dict()
    # results = dict()

    # start async event_loop
    # event_loop = asyncio.get_event_loop()
    # event_loop.create_task(watch_pods_async())
    # event_loop.create_task(watch_pvc_async())
    # event_loop.create_task(watch_va_async())
    # event_loop.run_forever()
    # logging.info("scale-test-finished")

