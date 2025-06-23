from utility.utility import logging
from storageclass import StorageClass


class storageclass_keywords:

    def __init__(self):
        self.storageclass = StorageClass()

    def create_storageclass(self, name, numberOfReplicas="3", migratable="false", dataLocality="disabled", fromBackup="", nfsOptions="", dataEngine="v1", encrypted="false", secretName="longhorn-crypto", secretNamespace="longhorn-system"):
        logging(f'Creating storageclass with {locals()}')
        self.storageclass.create(name, numberOfReplicas, migratable, dataLocality, fromBackup, nfsOptions, dataEngine, encrypted, secretName, secretNamespace)

    def cleanup_storageclasses(self):
        self.storageclass.cleanup()

    def set_storageclass_default_state(self, name, make_default):
        self.storageclass.set_storageclass_default_state(name, make_default)

    def assert_storageclass_is_default(self, name, is_default):
        self.storageclass.assert_storageclass_is_default(name, is_default)
