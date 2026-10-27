"""In-cluster Vault fixture for the vault key provider of encrypted volumes:
deploys deploy/vault/vault.yaml, configures policy, auth mount and role, and
reads or breaks the key entries Longhorn stores. Vault calls go through the
vault CLI in the fixture pod with the dev root token.
"""

import ast
import base64
import json
import shlex
import time

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import logging
from utility.utility import pod_exec
from utility.utility import subprocess_exec_cmd
from utility.utility import get_retry_count_and_interval
import utility.constant as constant


class Vault():

    MANIFEST = "./deploy/vault/vault.yaml"
    NAMESPACE = "vault"
    DEPLOYMENT = "vault"
    LABEL_SELECTOR = "app=vault"
    ADDR = "http://vault.vault.svc:8200"
    KV_MOUNT = "secret"
    KV_PREFIX = "longhorn/"
    POLICY = "longhorn-csi"
    ROLE = "longhorn-csi"
    AUTH_PATH = "auth/kubernetes-e2e"
    # The encryption Secret a vault StorageClass names, in Longhorn's namespace.
    SECRET_NAME = "longhorn-vault"
    VOLUME_KEY_DIR = "volumes"
    BACKUP_KEY_DIR = "backups"
    CSI_PLUGIN_DAEMONSET = "longhorn-csi-plugin"

    def __init__(self):
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    # ------------------------------------------------------------------ deploy

    def deploy(self):
        """Apply the fixture, wait for the pod, configure Vault. Idempotent."""
        subprocess_exec_cmd(f"kubectl apply -f {self.MANIFEST}")
        self.set_available(True)
        self.configure()
        self.write_encryption_secret()

    def is_deployed(self):
        try:
            self.apps_api.read_namespaced_deployment(self.DEPLOYMENT, self.NAMESPACE)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def get_pod_name(self):
        pods = self.core_api.list_namespaced_pod(self.NAMESPACE, label_selector=self.LABEL_SELECTOR).items
        for pod in pods:
            if pod.metadata.deletion_timestamp is None:
                return pod.metadata.name
        return None

    def wait_for_ready(self):
        for i in range(self.retry_count):
            logging(f"Waiting for the Vault fixture pod to be ready ... ({i})")
            pods = self.core_api.list_namespaced_pod(self.NAMESPACE, label_selector=self.LABEL_SELECTOR).items
            for pod in pods:
                if pod.metadata.deletion_timestamp is not None or pod.status.phase != "Running":
                    continue
                if all(cs.ready for cs in (pod.status.container_statuses or [])):
                    return pod.metadata.name
            time.sleep(self.retry_interval)
        assert False, "the Vault fixture pod did not become ready"

    SERVICE = "vault"
    OFFLINE_SELECTOR = {"app": "vault-offline"}

    def set_available(self, available):
        """An outage points the Service selector at a label nothing carries:
        scaling the dev server to zero would wipe its in-memory keys."""
        if available:
            logging("Making the Vault fixture reachable again")
            self.wait_for_ready()
            self.core_api.patch_namespaced_service(
                self.SERVICE, self.NAMESPACE, {"spec": {"selector": {"app": "vault"}}})
            self.wait_for_endpoints(present=True)
        else:
            logging("Making the Vault fixture unreachable")
            self.core_api.patch_namespaced_service(
                self.SERVICE, self.NAMESPACE, {"spec": {"selector": self.OFFLINE_SELECTOR}})
            self.wait_for_endpoints(present=False)

    def wait_for_endpoints(self, present):
        for i in range(self.retry_count):
            try:
                endpoints = self.core_api.read_namespaced_endpoints(self.SERVICE, self.NAMESPACE)
                addresses = [a for subset in (endpoints.subsets or []) for a in (subset.addresses or [])]
            except ApiException as e:
                if e.status != 404:
                    raise
                addresses = []
            logging(f"Vault service endpoints: {len(addresses)} (want {'some' if present else 'none'}) ... ({i})")
            if bool(addresses) == present:
                return
            time.sleep(self.retry_interval)
        assert False, f"the Vault service endpoints did not become {'present' if present else 'absent'}"

    # --------------------------------------------------------------- configure

    def exec(self, command, check=True):
        pod = self.get_pod_name()
        assert pod is not None, "the Vault fixture has no pod"
        output = pod_exec(pod, self.NAMESPACE, command)
        if check and ("Error" in output or "error" in output.split("\n")[0]):
            assert False, f"vault command failed: {command}\n{output}"
        return output

    @staticmethod
    def parse_structured(output, opener):
        """The exec client may hand back JSON output as a Python repr, so
        accept both. None when the output holds neither."""
        start = output.find(opener)
        if start < 0:
            return None
        text = output[start:].strip()
        try:
            return json.loads(text)
        except ValueError:
            pass
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return None

    def exec_json(self, command):
        output = self.exec(command)
        parsed = self.parse_structured(output, "{")
        assert parsed is not None, f"vault command returned no JSON: {command}\n{output}"
        return parsed

    def get_csi_plugin_service_account(self):
        """The driver deployer creates the DaemonSet after the Helm install
        returns, so wait for it."""
        for i in range(self.retry_count):
            try:
                ds = self.apps_api.read_namespaced_daemon_set(self.CSI_PLUGIN_DAEMONSET, constant.LONGHORN_NAMESPACE)
                return ds.spec.template.spec.service_account_name or "default"
            except ApiException as e:
                if e.status != 404:
                    raise
            logging(f"Waiting for the {self.CSI_PLUGIN_DAEMONSET} DaemonSet ... ({i})")
            time.sleep(self.retry_interval)
        assert False, f"DaemonSet {constant.LONGHORN_NAMESPACE}/{self.CSI_PLUGIN_DAEMONSET} did not appear"

    def configure(self):
        """Policy, auth mount and role. Safe to run again."""
        service_account = self.get_csi_plugin_service_account()
        logging(f"Configuring Vault for the CSI plugin ServiceAccount {constant.LONGHORN_NAMESPACE}/{service_account}")

        policy = (
            f'path "{self.KV_MOUNT}/data/{self.KV_PREFIX}*" {{ capabilities = ["create", "read", "update", "delete"] }}\n'
            f'path "{self.KV_MOUNT}/metadata/{self.KV_PREFIX}*" {{ capabilities = ["read", "delete", "list"] }}\n'
        )
        self.exec(f"printf %s {shlex.quote(policy)} | vault policy write {self.POLICY} -")

        auth_mounts = self.exec_json("vault auth list -format=json")

        mount = self.AUTH_PATH.split("/", 1)[1]
        if f"{mount}/" not in auth_mounts:
            self.exec(f"vault auth enable -path={mount} kubernetes")
        self.exec(f"vault write {self.AUTH_PATH}/config kubernetes_host=https://kubernetes.default.svc:443")
        self.exec(
            f"vault write {self.AUTH_PATH}/role/{self.ROLE} "
            f"bound_service_account_names={service_account} "
            f"bound_service_account_namespaces={constant.LONGHORN_NAMESPACE} "
            f"audience=vault policies={self.POLICY} ttl=24h")

    # ------------------------------------------------------------- diagnostics

    def collect_diagnostics(self, since="30m"):
        """Post-mortem logs for a failed vault test. Never raises."""
        def run(cmd):
            try:
                return subprocess_exec_cmd(cmd, verbose=False)
            except Exception as e:  # pylint: disable=broad-except
                return f"<{cmd} failed: {e}>"

        ns = constant.LONGHORN_NAMESPACE
        logging("=== vault diagnostics: volumes ===\n" + run(
            f"kubectl get volumes.longhorn.io -n {ns} -o jsonpath='{{range .items[*]}}{{.metadata.name}} state={{.status.state}} "
            f"encryption.spec={{.spec.encryption}} encryption.status={{.status.encryption}}{{\"\\n\"}}{{end}}'"))
        logging("=== vault diagnostics: workload pods ===\n" + run("kubectl get pods -n default -o wide"))
        logging("=== vault diagnostics: events (default) ===\n" + run(
            "kubectl get events -n default --sort-by=.lastTimestamp | tail -n 40"))
        pods = run(f"kubectl get pods -n {ns} -l app=longhorn-csi-plugin -o name").split()
        for pod in pods:
            logging(f"=== vault diagnostics: {pod} longhorn-csi-plugin log (since {since}) ===\n" + run(
                f"kubectl logs {pod} -n {ns} -c longhorn-csi-plugin --since={since} 2>&1 | grep -iE 'encrypt|vault|key|luks|NodeStage|NodeExpand|error' | tail -n 120"))
        logging("=== vault diagnostics: vault pods ===\n" + run(f"kubectl get pods,svc,endpoints -n {self.NAMESPACE} -o wide"))
        if self.get_pod_name():
            logging("=== vault diagnostics: keys ===\n" + run(
                f"kubectl exec -n {self.NAMESPACE} {self.get_pod_name()} -- vault kv list -mount={self.KV_MOUNT} {self.KV_PREFIX}"))

    # -------------------------------------------------------------------- keys

    def _path(self, kind, name):
        return f"{self.KV_PREFIX}{kind}/{name}"

    def _get(self, path):
        """(passphrase, version), or (None, 0) when no live key exists."""
        entry = self.parse_structured(self.exec(f"vault kv get -format=json -mount={self.KV_MOUNT} {path}", check=False), "{")
        data = (entry or {}).get("data") or {}
        metadata = data.get("metadata") or {}
        if metadata.get("destroyed") or metadata.get("deletion_time") or not data.get("data"):
            return None, 0
        return data["data"].get("passphrase"), metadata.get("version", 0)

    def _delete(self, path):
        self.exec(f"vault kv metadata delete -mount={self.KV_MOUNT} {path}", check=False)

    def get_key(self, volume_name):
        return self._get(self._path(self.VOLUME_KEY_DIR, volume_name))

    def has_key(self, volume_name):
        return self.get_key(volume_name)[0] is not None

    def put_key(self, volume_name, passphrase):
        self.exec(f"vault kv put -mount={self.KV_MOUNT} {self._path(self.VOLUME_KEY_DIR, volume_name)} passphrase={shlex.quote(passphrase)}")

    def delete_key(self, volume_name):
        self._delete(self._path(self.VOLUME_KEY_DIR, volume_name))

    def get_backup_key(self, backup_name):
        return self._get(self._path(self.BACKUP_KEY_DIR, backup_name))

    def has_backup_key(self, backup_name):
        return self.get_backup_key(backup_name)[0] is not None

    def cleanup_keys(self):
        if not self.is_deployed() or self.get_pod_name() is None:
            return
        for kind in (self.VOLUME_KEY_DIR, self.BACKUP_KEY_DIR):
            output = self.exec(f"vault kv list -format=json -mount={self.KV_MOUNT} {self.KV_PREFIX}{kind}/", check=False)
            for key in self.parse_structured(output, "[") or []:
                logging(f"Deleting leftover Vault key {kind}/{key}")
                self._delete(self._path(kind, key))

    # ------------------------------------------------------- encryption secret

    def write_encryption_secret(self):
        data = {
            "CRYPTO_KEY_PROVIDER": "vault",
            "VAULT_ADDR": self.ADDR,
            "VAULT_AUTH_PATH": self.AUTH_PATH,
            "VAULT_ROLE": self.ROLE,
            "VAULT_KV_MOUNT": self.KV_MOUNT,
            "VAULT_KV_PREFIX": self.KV_PREFIX,
            "VAULT_DESTROY_KEYS": "true",
        }
        body = client.V1Secret(
            metadata=client.V1ObjectMeta(name=self.SECRET_NAME, namespace=constant.LONGHORN_NAMESPACE),
            string_data=data)
        try:
            self.core_api.create_namespaced_secret(namespace=constant.LONGHORN_NAMESPACE, body=body)
            logging(f"Created encryption Secret {constant.LONGHORN_NAMESPACE}/{self.SECRET_NAME}")
        except ApiException as e:
            if e.status != 409:
                raise
            self.core_api.patch_namespaced_secret(
                name=self.SECRET_NAME, namespace=constant.LONGHORN_NAMESPACE, body=body)
            logging(f"Refreshed encryption Secret {constant.LONGHORN_NAMESPACE}/{self.SECRET_NAME}")
