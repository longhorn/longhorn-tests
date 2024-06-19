KIND_DEPLOYMENT = 'deployment'
KIND_STATEFULSET = 'statefulset'

LABEL_TEST = 'test.longhorn.io'
LABEL_TEST_VALUE = 'e2e'

ANNOT_CHECKSUM = f'{LABEL_TEST}/last-recorded-checksum'
ANNOT_EXPANDED_SIZE = f'{LABEL_TEST}/last-recorded-expanded-size'

NAME_PREFIX = 'e2e-test'
STORAGECLASS_NAME_PREFIX = 'longhorn-test'

STREAM_EXEC_TIMEOUT = 300

LONGHORN_NAMESPACE = 'longhorn-system'

DISK_BEING_SYNCING = "being syncing and please retry later"
NODE_UPDATE_RETRY_INTERVAL = 6
