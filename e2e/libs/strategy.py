from enum import Enum


class LonghornOperationStrategy(Enum):
    CRD = 'crd'
    REST = 'rest'


class CloudProvider(Enum):
    AWS = 'aws'
    LOCAL_CLUSTER = 'local'
