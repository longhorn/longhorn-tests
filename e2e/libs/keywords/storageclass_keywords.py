from utility.utility import logging
from storageclass.storageclass import create
from storageclass.storageclass import delete
from storageclass.storageclass import delete_all

class storageclass_keywords:

    def __init__(self):
        pass

    def init_storageclasses(self):
        create('longhorn-test')
        create('longhorn-test-strict-local', replica_count="1", data_locality='strict-local')

    def create_storageclass(self, name, replica_count="", migratable="", data_locality="", from_backup=""):
        logging(f'Creating storageclass {name}')
        create(name, replica_count, migratable, data_locality, from_backup)

    def delete_storageclass(self, name):
        delete(name)

    def cleanup_storageclasses(self):
        delete_all()
