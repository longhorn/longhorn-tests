from persistentvolume import PersistentVolume
from utility.utility import logging


class persistentvolume_keywords:

    def __init__(self):
        self.pv = PersistentVolume()

    def delete_persistentvolume(self, name):
        logging(f'Deleting persistentvolume {name}')
        return self.pv.delete(name)
