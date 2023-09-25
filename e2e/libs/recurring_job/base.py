from abc import ABC, abstractmethod


class Base(ABC):

    @abstractmethod
    def create(self, name, task, groups, cron, retain, concurrency, label):
        return NotImplemented

    @abstractmethod
    def delete(self, job_name, volume_name):
        return NotImplemented

    @abstractmethod
    def get(self, name):
        return NotImplemented

    @abstractmethod
    def add_to_volume(self, job_name, volume_name):
        return NotImplemented

    @abstractmethod
    def check_jobs_work(self, volume_name):
        return NotImplemented

    @abstractmethod
    def cleanup(self, volume_names):
        return NotImplemented