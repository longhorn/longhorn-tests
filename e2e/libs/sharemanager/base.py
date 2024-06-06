from abc import ABC, abstractmethod

class Base(ABC):

    @abstractmethod
    def list(self):
        return NotImplemented
