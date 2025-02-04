from abc import ABC, abstractmethod

class Base(ABC):

    @abstractmethod
    def create(self, backup_name):
        return NotImplemented

    @abstractmethod
    def restore(self, backup_name):
        return NotImplemented
