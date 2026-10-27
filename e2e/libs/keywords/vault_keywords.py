import time

from vault import Vault

from utility.utility import logging
from utility.utility import get_retry_count_and_interval


class vault_keywords:

    def __init__(self):
        self.vault = Vault()
        self.saved_keys = {}
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def deploy_vault_fixture(self):
        self.vault.deploy()

    def set_vault_available(self, available):
        self.vault.set_available(available)

    def restore_vault_availability(self):
        if self.vault.is_deployed():
            self.vault.set_available(True)

    def collect_vault_diagnostics(self):
        self.vault.collect_diagnostics()

    def cleanup_vault_keys(self):
        self.vault.cleanup_keys()

    def assert_vault_has_key_of_volume(self, volume_name):
        passphrase, version = self.vault.get_key(volume_name)
        logging(f"Vault holds key version {version} of volume {volume_name}")
        assert passphrase, f"Vault holds no key for volume {volume_name}"
        assert version >= 1, f"unexpected key version {version} for volume {volume_name}"

    def assert_vault_has_no_key_of_volume(self, volume_name):
        assert not self.vault.has_key(volume_name), f"Vault still holds a key for volume {volume_name}"

    def assert_vault_keys_of_volumes_are_equal(self, volume_name, other_volume_name):
        passphrase, _ = self.vault.get_key(volume_name)
        other, _ = self.vault.get_key(other_volume_name)
        assert passphrase and other, f"both volumes need a key: {volume_name}={bool(passphrase)} {other_volume_name}={bool(other)}"
        assert passphrase == other, f"volumes {volume_name} and {other_volume_name} hold different keys"

    def assert_vault_keys_of_volumes_are_different(self, volume_name, other_volume_name):
        passphrase, _ = self.vault.get_key(volume_name)
        other, _ = self.vault.get_key(other_volume_name)
        assert passphrase and other, f"both volumes need a key: {volume_name}={bool(passphrase)} {other_volume_name}={bool(other)}"
        assert passphrase != other, f"volumes {volume_name} and {other_volume_name} share one key"

    def record_vault_key_of_volume(self, volume_name, key_id):
        passphrase, version = self.vault.get_key(volume_name)
        assert passphrase, f"Vault holds no key for volume {volume_name}"
        self.saved_keys[key_id] = passphrase
        logging(f"Recorded key version {version} of volume {volume_name} as key {key_id}")

    def restore_vault_key_of_volume(self, volume_name, key_id):
        assert key_id in self.saved_keys, f"no recorded key {key_id}"
        self.vault.put_key(volume_name, self.saved_keys[key_id])

    def delete_vault_key_of_volume(self, volume_name):
        logging(f"Deleting the Vault key of volume {volume_name}")
        self.vault.delete_key(volume_name)

    def corrupt_vault_key_of_volume(self, volume_name):
        logging(f"Overwriting the Vault key of volume {volume_name} with a wrong passphrase")
        self.vault.put_key(volume_name, "not-the-passphrase-of-this-volume")

    def get_encryption_secret_name(self):
        return self.vault.SECRET_NAME

    def _wait_for(self, check, what):
        # The controllers write and destroy entries some reconciles after the triggering call returns.
        for i in range(self.retry_count):
            if check():
                return
            logging(f"Waiting for {what} ... ({i})")
            time.sleep(self.retry_interval)
        raise AssertionError(f"timed out waiting for {what}")

    def assert_vault_has_key_of_backup(self, backup_name):
        self._wait_for(lambda: self.vault.has_backup_key(backup_name), f"the Vault key of backup {backup_name}")

    def assert_vault_has_no_key_of_backup(self, backup_name):
        self._wait_for(lambda: not self.vault.has_backup_key(backup_name), f"the Vault key of backup {backup_name} to be destroyed")

    def assert_vault_key_of_backup_equals_volume(self, backup_name, volume_name):
        self.assert_vault_has_key_of_backup(backup_name)
        backup_key, _ = self.vault.get_backup_key(backup_name)
        volume_key, _ = self.vault.get_key(volume_name)
        assert backup_key is not None, f"Vault holds no key for backup {backup_name}"
        assert backup_key == volume_key, \
            f"the key of backup {backup_name} differs from the key of volume {volume_name}; a restore would not open"

    def wait_for_vault_key_of_volume_gone(self, volume_name):
        self._wait_for(lambda: not self.vault.has_key(volume_name), f"the Vault key of volume {volume_name} to be destroyed")
