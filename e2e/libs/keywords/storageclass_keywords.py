from utility.utility import logging
from storageclass import StorageClass


class storageclass_keywords:

    def __init__(self):
        self.storageclass = StorageClass()

    def create_storageclass(self, name, numberOfReplicas=None, migratable=None, dataLocality=None, fromBackup=None, nfsOptions=None, dataEngine=None, encrypted=None, recurringJobSelector=None, volumeBindingMode=None, allowedTopologies=None, backingImage=None):
        logging(f'Creating storageclass with {locals()}')
        self.storageclass.create(name, numberOfReplicas, migratable, dataLocality, fromBackup, nfsOptions, dataEngine, encrypted, recurringJobSelector, volumeBindingMode, allowedTopologies, backingImage)

    def cleanup_storageclasses(self):
        self.storageclass.cleanup()

    def set_storageclass_default_state(self, name, make_default):
        self.storageclass.set_storageclass_default_state(name, make_default)

    def assert_storageclass_is_default(self, name, is_default):
        self.storageclass.assert_storageclass_is_default(name, is_default)
