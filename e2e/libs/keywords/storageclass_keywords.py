from utility.utility import logging
from storageclass import StorageClass

class storageclass_keywords:

    def __init__(self):
        self.storageclass = StorageClass()

    def create_storageclass(self, name, numberOfReplicas="3", migratable="false", dataLocality="disabled", fromBackup="", nfsOptions=""):
        logging(f'Creating storageclass with {locals()}')
        self.storageclass.create(name, numberOfReplicas, migratable, dataLocality, fromBackup, nfsOptions)

    def cleanup_storageclasses(self):
        self.storageclass.cleanup()
