from abc import ABC, abstractmethod


class Base(ABC):

    @abstractmethod
    def get_enginefrontends(self, volume_name):
        return NotImplemented
