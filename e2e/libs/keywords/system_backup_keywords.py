from kubernetes import client

from system_backup import SystemBackup
import utility.constant as constant


class system_backup_keywords:

    def __init__(self):
        self.system_backup = SystemBackup()

    def create_system_backup(self, backup_name, backup_policy='if-not-present'):
        self.system_backup.create(backup_name, backup_policy)

    def create_system_restore(self, backup_name, wait=True):
        return self.system_backup.restore(backup_name, wait=wait)

    def wait_for_system_restore_completed(self, restore_name):
        self.system_backup.wait_for_system_restore_completed(restore_name)

    def delete_system_backup(self, backup_name):
        self.system_backup.delete_system_backup(backup_name)

    def wait_for_system_backup_ready(self, backup_name):
        self.system_backup.wait_for_system_backup_ready(backup_name)

    def cleanup_system_backups(self):
        self.system_backup.cleanup_system_backups()

    def cleanup_system_restores(self):
        self.system_backup.cleanup_system_restores()

    def set_system_backup_status(self, backup_name, **status):
        return self.system_backup.set_system_backup_status(backup_name, status)

    def check_system_backup_created_at_empty(self, backup_name):
        self.system_backup.check_system_backup_created_at_empty(backup_name)

    def wait_for_system_backup_deleted(self, backup_name):
        self.system_backup.wait_for_system_backup_deleted(backup_name)

    def check_system_restore_job_registry_secret(self, restore_name, secret_name):
        job_name = f"longhorn-system-rollout-{restore_name}"
        job = client.BatchV1Api().read_namespaced_job(job_name, constant.LONGHORN_NAMESPACE)
        secrets = [secret.name for secret in (job.spec.template.spec.image_pull_secrets or [])]
        assert secret_name in secrets, (
            f"Job {job_name} imagePullSecrets {secrets} does not contain {secret_name}")
