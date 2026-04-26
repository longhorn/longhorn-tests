import os
import time

from kubernetes import client
from kubernetes.client.rest import ApiException

from node import Node

from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import pod_exec
import utility.constant as constant


class live_switchover_keywords:

    DATA_DIR = "/data/switchover_io"
    DATA_FILE = f"{DATA_DIR}/data.bin"
    MANIFEST = "/tmp/switchover_manifest"
    STOP_FILE = "/tmp/switchover_stop"
    CHUNK_FILE = "/tmp/switchover_chunk"
    DONE_FILE = "/tmp/switchover_writer_done"
    ERROR_FILE = "/tmp/switchover_writer_error"
    PID_FILE = "/tmp/switchover_io.pid"
    LOG_FILE = "/tmp/switchover_io.log"
    CHUNK_SIZE = 65536
    IO_SCRIPT_REMOTE = "/tmp/live_switchover_io.sh"

    def __init__(self):
        self.core_api = client.CoreV1Api()
        self.obj_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        self.io_script_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "live_switchover_io.sh"))

    def assert_live_switchover_resources_start_on_same_node(self, pvc_name, namespace="default"):
        volume_name = self._get_volume_name_from_pvc(pvc_name, namespace)
        volume = self._get_volume(volume_name)
        engines = self._get_engines(volume_name)
        engine_frontends = self._get_engine_frontends(volume_name)

        assert len(engines) == 1, f"Expected one engine for volume {volume_name}, got {len(engines)}: {engines}"
        assert len(engine_frontends) == 1, \
            f"Expected one enginefrontend for volume {volume_name}, got {len(engine_frontends)}: {engine_frontends}"

        node_a = volume["spec"]["nodeID"]
        current_node = volume["status"]["currentNodeID"]
        current_engine_node = volume["status"]["currentEngineNodeID"]
        engine_node = engines[0]["spec"]["nodeID"]
        engine_frontend_node = engine_frontends[0]["spec"]["nodeID"]

        assert volume["status"]["state"] == "attached", f"Expected volume {volume_name} attached, got {volume['status']}"
        assert volume["status"]["robustness"] == "healthy", f"Expected volume {volume_name} healthy, got {volume['status']}"
        assert node_a, f"Expected volume {volume_name} spec.nodeID to be set: {volume}"
        assert current_node == node_a, f"Expected volume currentNodeID {current_node} to equal Node A {node_a}"
        assert current_engine_node == node_a, f"Expected currentEngineNodeID {current_engine_node} to equal Node A {node_a}"
        assert engine_node == node_a, f"Expected engine on Node A {node_a}, got {engine_node}"
        assert engine_frontend_node == node_a, f"Expected enginefrontend on Node A {node_a}, got {engine_frontend_node}"

        logging(f"Live switchover Node A is {node_a} for volume {volume_name}", also_report=True)
        return node_a

    def start_live_switchover_io(self, pod_name, namespace="default"):
        self._install_io_script(pod_name, namespace)
        pid = pod_exec(pod_name, namespace, f"sh {self.IO_SCRIPT_REMOTE} start").strip()
        logging(f"Started live switchover writer in pod {pod_name}, pid={pid}", also_report=True)
        self._assert_writer_running_and_progressing(pod_name, namespace)

    def run_live_switchover_rounds(self, pvc_name, pod_name, rounds=5, post_write_seconds=180, namespace="default"):
        rounds = int(rounds)
        post_write_seconds = int(post_write_seconds)
        volume_name = self._get_volume_name_from_pvc(pvc_name, namespace)
        node_a = self.assert_live_switchover_resources_start_on_same_node(pvc_name, namespace)
        node_b, node_c = self._pick_target_nodes(node_a)
        initial_restart_count = self._get_pod_restart_count(pod_name, namespace)
        last_count = self._get_manifest_line_count(pod_name, namespace)

        for round_index in range(1, rounds + 1):
            logging(f"##### START LIVE SWITCHOVER ROUND {round_index}/{rounds} #####", also_report=True)
            last_count = self._switch_and_verify(
                volume_name, pod_name, namespace, node_a, node_a, node_b,
                round_index, initial_restart_count, last_count, post_write_seconds)
            last_count = self._switch_and_verify(
                volume_name, pod_name, namespace, node_a, node_b, node_c,
                round_index, initial_restart_count, last_count, post_write_seconds)
            last_count = self._switch_and_verify(
                volume_name, pod_name, namespace, node_a, node_c, node_a,
                round_index, initial_restart_count, last_count, post_write_seconds)
            logging(f"##### LIVE SWITCHOVER ROUND {round_index}/{rounds} COMPLETE #####", also_report=True)

        self._assert_common_state(volume_name, pod_name, namespace, node_a, initial_restart_count, last_count)
        logging(f"Completed {rounds} live switchover rounds for volume {volume_name}", also_report=True)

    def run_live_switchover_sequence(self, pvc_name, pod_name, post_write_seconds=180, namespace="default"):
        post_write_seconds = int(post_write_seconds)
        volume_name = self._get_volume_name_from_pvc(pvc_name, namespace)
        node_a = self.assert_live_switchover_resources_start_on_same_node(pvc_name, namespace)
        node_b, node_c = self._pick_target_nodes(node_a)
        initial_restart_count = self._get_pod_restart_count(pod_name, namespace)
        last_count = self._get_manifest_line_count(pod_name, namespace)
        switchovers = [
            (node_a, node_b),
            (node_b, node_c),
            (node_c, node_b),
            (node_b, node_a),
        ]

        logging(f"##### START LIVE SWITCHOVER SEQUENCE: {node_a} -> {node_b} -> "
                f"{node_c} -> {node_b} -> {node_a} #####", also_report=True)
        for step_index, (from_node, target_node) in enumerate(switchovers, start=1):
            last_count = self._switch_and_verify(
                volume_name, pod_name, namespace, node_a, from_node, target_node,
                f"{step_index}/{len(switchovers)}", initial_restart_count, last_count, post_write_seconds)

        self._assert_common_state(volume_name, pod_name, namespace, node_a, initial_restart_count, last_count)
        logging(f"Completed live switchover sequence for volume {volume_name}", also_report=True)

    def stop_live_switchover_io(self, pod_name, namespace="default"):
        output = pod_exec(pod_name, namespace, f"sh {self.IO_SCRIPT_REMOTE} stop")
        logging(f"Stopped live switchover writer in pod {pod_name}: {output}", also_report=True)
        return output

    def stop_live_switchover_io_if_running(self, pod_name, namespace="default"):
        try:
            pod = self.core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
            if pod.metadata.deletion_timestamp:
                return
            pod_exec(pod_name, namespace, f"sh {self.IO_SCRIPT_REMOTE} stop-if-running")
        except Exception as e:
            logging(f"Stopping live switchover writer in pod {pod_name} ignored error: {e}")

    def verify_live_switchover_checksum(self, pod_name, namespace="default"):
        output = pod_exec(pod_name, namespace, f"sh {self.IO_SCRIPT_REMOTE} verify")
        assert "CHECKSUM_OK" in output, f"Live switchover checksum verification failed: {output}"
        logging(output, also_report=True)
        return output

    def verify_live_switchover_final_state(self, pvc_name, pod_name, namespace="default"):
        volume_name = self._get_volume_name_from_pvc(pvc_name, namespace)
        node_a = self.assert_live_switchover_resources_start_on_same_node(pvc_name, namespace)
        pod = self.core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
        restart_count = self._get_pod_restart_count(pod_name, namespace)
        assert pod.status.phase == "Running", f"Expected pod {pod_name} Running, got {pod.status.phase}"
        assert restart_count == 0, f"Expected pod {pod_name} restart count 0, got {restart_count}"
        logging(f"Live switchover final state verified for volume {volume_name} on Node A {node_a}", also_report=True)

    def cleanup_live_switchover_resources(self, pvc_name, pod_name, namespace="default"):
        volume_name = self._get_volume_name_from_pvc_if_exists(pvc_name, namespace)
        self.stop_live_switchover_io_if_running(pod_name, namespace)
        self._delete_pod_if_exists(pod_name, namespace)
        self._delete_pvc_if_exists(pvc_name, namespace)
        if volume_name:
            self._wait_for_longhorn_volume_deleted(volume_name)

    def _switch_and_verify(self, volume_name, pod_name, namespace, node_a, from_node, target_node,
                           round_index, initial_restart_count, last_count, post_write_seconds):
        logging(f"Round {round_index}: live switchover {from_node} -> {target_node}; Volume/EF stay on {node_a}",
                also_report=True)
        last_count = self._assert_common_state(volume_name, pod_name, namespace, node_a, initial_restart_count, last_count)
        self._patch_volume_engine_node(volume_name, target_node)

        deadline = time.time() + 420
        while time.time() < deadline:
            time.sleep(5)
            last_count = self._assert_common_state(
                volume_name, pod_name, namespace, node_a, initial_restart_count, last_count)

            volume = self._get_volume(volume_name)
            try:
                active_engine = self._get_active_engine(volume_name)
                engine_frontend = self._get_single_engine_frontend(volume_name)
            except AssertionError as e:
                logging(f"Waiting for switchover resources to settle: {e}")
                continue

            if self._is_switchover_complete(volume, active_engine, engine_frontend, node_a, target_node):
                logging(f"Round {round_index}: switchover to {target_node} completed; post-write {post_write_seconds}s",
                        also_report=True)
                post_deadline = time.time() + post_write_seconds
                while time.time() < post_deadline:
                    time.sleep(min(30, max(1, int(post_deadline - time.time()))))
                    last_count = self._assert_common_state(
                        volume_name, pod_name, namespace, node_a, initial_restart_count, last_count)
                    engine_frontend = self._get_single_engine_frontend(volume_name)
                    assert engine_frontend["spec"]["nodeID"] == node_a, \
                        f"EngineFrontend moved away from Node A {node_a}: {engine_frontend}"
                logging(f"Round {round_index}: post-write for {target_node} completed", also_report=True)
                return last_count

        volume = self._get_volume(volume_name)
        engines = self._get_engines(volume_name)
        engine_frontends = self._get_engine_frontends(volume_name)
        assert False, f"Timeout waiting for switchover to {target_node}: volume={volume}, engines={engines}, enginefrontends={engine_frontends}"

    def _assert_common_state(self, volume_name, pod_name, namespace, node_a, initial_restart_count, last_count):
        volume = self._get_volume(volume_name)
        pod = self.core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
        current_count = self._assert_writer_running_and_progressing(pod_name, namespace, last_count)
        restart_count = self._get_pod_restart_count(pod_name, namespace)

        assert volume["status"]["state"] == "attached", f"Volume {volume_name} is not attached: {volume}"
        assert volume["status"]["robustness"] == "healthy", f"Volume {volume_name} is not healthy: {volume}"
        assert volume["spec"]["nodeID"] == node_a, f"Volume spec.nodeID moved away from Node A {node_a}: {volume}"
        assert volume["status"]["currentNodeID"] == node_a, \
            f"Volume status.currentNodeID moved away from Node A {node_a}: {volume}"
        assert pod.status.phase == "Running", f"Pod {pod_name} is not Running: {pod.status.phase}"
        assert restart_count == initial_restart_count, \
            f"Pod {pod_name} restart count changed from {initial_restart_count} to {restart_count}"

        logging(f"Live switchover check: volume={volume['status']['state']}/{volume['status']['robustness']} "
                f"currentEngineNode={volume['status'].get('currentEngineNodeID', '')} "
                f"specEngineNode={volume['spec'].get('engineNodeID', '')} pod={pod.status.phase} "
                f"restarts={restart_count} chunks={current_count}")
        return current_count

    def _is_switchover_complete(self, volume, active_engine, engine_frontend, node_a, target_node):
        engine_ip = active_engine["status"].get("ip", "")
        engine_port = str(active_engine["status"].get("port", ""))
        ef_target_port = str(engine_frontend["status"].get("targetPort", ""))

        complete = \
            volume["status"].get("currentEngineNodeID") == target_node and \
            volume["status"].get("state") == "attached" and \
            volume["status"].get("robustness") == "healthy" and \
            active_engine["spec"].get("nodeID") == target_node and \
            active_engine["status"].get("currentState") == "running" and \
            engine_frontend["spec"].get("nodeID") == node_a and \
            engine_frontend["spec"].get("engineName") == active_engine["metadata"]["name"] and \
            engine_frontend["status"].get("currentState") == "running" and \
            engine_frontend["status"].get("endpoint", "") != "" and \
            engine_frontend["status"].get("targetIP", "") == engine_ip and \
            ef_target_port == engine_port

        logging(f"Switchover status target={target_node}: complete={complete}, "
                f"activeEngine={active_engine['metadata']['name']} node={active_engine['spec'].get('nodeID')} "
                f"state={active_engine['status'].get('currentState')} addr={engine_ip}:{engine_port}, "
                f"engineFrontend={engine_frontend['metadata']['name']} node={engine_frontend['spec'].get('nodeID')} "
                f"engine={engine_frontend['spec'].get('engineName')} state={engine_frontend['status'].get('currentState')} "
                f"endpoint={engine_frontend['status'].get('endpoint', '')} "
                f"target={engine_frontend['status'].get('targetIP', '')}:{ef_target_port}")
        return complete

    def _assert_writer_running_and_progressing(self, pod_name, namespace, last_count=None):
        output = pod_exec(pod_name, namespace, f"sh {self.IO_SCRIPT_REMOTE} count").strip()
        current_count = int(output.splitlines()[-1])
        if last_count is not None:
            assert current_count > int(last_count), \
                f"Live switchover writer did not progress: previous={last_count}, current={current_count}"
        return current_count

    def _get_manifest_line_count(self, pod_name, namespace):
        return int(pod_exec(pod_name, namespace, f"wc -l < {self.MANIFEST}").strip().splitlines()[-1])

    def _install_io_script(self, pod_name, namespace):
        with open(self.io_script_path, "r", encoding="utf-8") as f:
            script = f.read()
        cmd = f"cat > {self.IO_SCRIPT_REMOTE} <<'LIVE_SWITCHOVER_IO_SCRIPT'\n{script}\nLIVE_SWITCHOVER_IO_SCRIPT\nchmod +x {self.IO_SCRIPT_REMOTE}"
        pod_exec(pod_name, namespace, cmd)

    def _get_pod_restart_count(self, pod_name, namespace):
        pod = self.core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
        return sum(status.restart_count for status in (pod.status.container_statuses or []))

    def _get_volume_name_from_pvc(self, pvc_name, namespace):
        pvc = self.core_api.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)
        assert pvc.spec.volume_name, f"PVC {namespace}/{pvc_name} is not bound to a volume"
        return pvc.spec.volume_name

    def _get_volume_name_from_pvc_if_exists(self, pvc_name, namespace):
        try:
            pvc = self.core_api.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)
            return pvc.spec.volume_name
        except ApiException as e:
            if e.status == 404:
                return None
            raise e

    def _get_volume(self, volume_name):
        return self.obj_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="volumes",
            name=volume_name)

    def _get_engines(self, volume_name):
        resp = self.obj_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="engines",
            label_selector=f"longhornvolume={volume_name}")
        return resp.get("items", [])

    def _get_engine_frontends(self, volume_name):
        try:
            resp = self.obj_api.list_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=constant.LONGHORN_NAMESPACE,
                plural="enginefrontends",
                label_selector=f"longhornvolume={volume_name}")
        except ApiException as e:
            assert False, f"Failed to list EngineFrontend CRs. Is the v2 EngineFrontend CRD installed? {e}"
        return resp.get("items", [])

    def _get_active_engine(self, volume_name):
        engines = self._get_engines(volume_name)
        active_engines = [engine for engine in engines if engine["spec"].get("active")]
        assert len(active_engines) == 1, \
            f"Expected one active engine for volume {volume_name}, got {len(active_engines)}: {engines}"
        return active_engines[0]

    def _get_single_engine_frontend(self, volume_name):
        engine_frontends = self._get_engine_frontends(volume_name)
        assert len(engine_frontends) == 1, \
            f"Expected one enginefrontend for volume {volume_name}, got {len(engine_frontends)}: {engine_frontends}"
        return engine_frontends[0]

    def _patch_volume_engine_node(self, volume_name, target_node):
        logging(f"Patching volume {volume_name} spec.engineNodeID={target_node}", also_report=True)
        self.obj_api.patch_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="volumes",
            name=volume_name,
            body={"spec": {"engineNodeID": target_node}})

    def _pick_target_nodes(self, node_a):
        worker_nodes = Node().list_node_names_by_role("worker")
        target_nodes = [node for node in worker_nodes if node != node_a]
        assert len(target_nodes) >= 2, \
            f"Live switchover test requires at least three worker nodes, got Node A={node_a}, workers={worker_nodes}"
        return target_nodes[0], target_nodes[1]

    def _delete_pod_if_exists(self, pod_name, namespace):
        try:
            self.core_api.delete_namespaced_pod(name=pod_name, namespace=namespace)
            logging(f"Deleted pod {namespace}/{pod_name}", also_report=True)
        except ApiException as e:
            if e.status != 404:
                raise e

    def _delete_pvc_if_exists(self, pvc_name, namespace):
        try:
            self.core_api.delete_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)
            logging(f"Deleted PVC {namespace}/{pvc_name}", also_report=True)
        except ApiException as e:
            if e.status != 404:
                raise e

    def _wait_for_longhorn_volume_deleted(self, volume_name):
        for i in range(self.retry_count):
            try:
                self._get_volume(volume_name)
                logging(f"Waiting for volume {volume_name} deleted ... ({i})")
            except ApiException as e:
                if e.status == 404:
                    logging(f"Deleted volume {volume_name}", also_report=True)
                    return
                raise e
            time.sleep(self.retry_interval)
        assert False, f"Waiting for volume {volume_name} deleted failed"
