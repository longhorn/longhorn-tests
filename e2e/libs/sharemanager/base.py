from abc import ABC, abstractmethod

class Base(ABC):

    @abstractmethod
    def list(self):
        return NotImplemented

    @abstractmethod
    def get(self, name):
        return NotImplemented

    @abstractmethod
    def delete(self, name):
        return NotImplemented

    @abstractmethod
    def wait_for_running(self, name):
        return NotImplemented
    
    @abstractmethod
    def wait_for_restart(self, name, last_creation_time):
        return NotImplemented
