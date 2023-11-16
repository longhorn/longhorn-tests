KIND_DEPLOYMENT = 'deployment'
KIND_STATEFULSET = 'statefulset'

LABEL_TEST = 'test.longhorn.io'
LABEL_TEST_VALUE = 'e2e'

ANNOT_CHECKSUM = f'{LABEL_TEST}/last-recorded-checksum'
ANNOT_EXPANDED_SIZE = f'{LABEL_TEST}/last-recorded-expanded-size'

NAME_PREFIX = 'e2e-test'
