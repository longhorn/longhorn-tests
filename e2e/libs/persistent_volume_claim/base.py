from abc import ABC, abstractmethod


class Base(ABC):

    @abstractmethod
    def get(self, volume_name):
        return NotImplemented

    @abstractmethod
    def expand(self, claim_name, size, claim_namespace="default"):
        return NotImplemented
