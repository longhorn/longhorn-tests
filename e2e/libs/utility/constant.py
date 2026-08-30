KIND_DEPLOYMENT = 'deployment'
KIND_STATEFULSET = 'statefulset'

LABEL_LONGHORN_COMPONENT = "longhorn.io/component"
LABEL_TEST = 'test.longhorn.io'
LABEL_TEST_VALUE = 'e2e'

ANNOT_CHECKSUM = f'{LABEL_TEST}/last-recorded-checksum'
ANNOT_EXPANDED_SIZE = f'{LABEL_TEST}/last-recorded-expanded-size'
ANNOT_REPLICA_NAMES = f'{LABEL_TEST}/replica-names'

NAME_PREFIX = 'e2e-test'
STORAGECLASS_NAME_PREFIX = 'longhorn-test'

STREAM_EXEC_TIMEOUT = 300

LONGHORN_NAMESPACE = 'longhorn-system'

DISK_BEING_SYNCING = "being syncing and please retry later"
NODE_UPDATE_RETRY_INTERVAL = 6

LONGHORN_UNINSTALL_JOB_LABEL="job-name=longhorn-uninstall"
LONGHORN_INSTALL_SCRIPT_PATH="utilities/longhorn-install.sh"
LONGHORN_INSTALL_TIMEOUT = 600

# The activeDeadlineSeconds is set to 900 in https://raw.githubusercontent.com/longhorn/longhorn/master/uninstall/uninstall.yaml
LONGHORN_UNINSTALL_TIMEOUT = 900

DEFAULT_BACKUPSTORE="s3://backupbucket@us-east-1/backupstore$minio-secret"

BLOCK_PVC_VOLUME_DEVICE_NAME = "longhorn-testblk"
BLOCK_PVC_VOLUME_DEVICE_DIR = "/dev/longhorn"
# This path is used in the deployment template for block volume
BLOCK_PVC_VOLUME_DEVICE_PATH = BLOCK_PVC_VOLUME_DEVICE_DIR + "/" + BLOCK_PVC_VOLUME_DEVICE_NAME

# Pod label selectors for longhorn-system namespace
LABEL_SELECTOR_LONGHORN_MANAGER = "app=longhorn-manager"
LABEL_SELECTOR_INSTANCE_MANAGER = "longhorn.io/component=instance-manager"
LABEL_SELECTOR_ENGINE_IMAGE = "longhorn.io/component=engine-image"
LABEL_SELECTOR_CSI_PLUGIN = "app=longhorn-csi-plugin"
LABEL_SELECTOR_CSI_ATTACHER = "app=csi-attacher"
LABEL_SELECTOR_CSI_PROVISIONER = "app=csi-provisioner"
LABEL_SELECTOR_CSI_RESIZER = "app=csi-resizer"
LABEL_SELECTOR_CSI_SNAPSHOTTER = "app=csi-snapshotter"
LABEL_SELECTOR_DRIVER_DEPLOYER = "app=longhorn-driver-deployer"
LABEL_SELECTOR_LONGHORN_UI = "app=longhorn-ui"

DISK_UNSCHEDULABLE_KEEP_ROUNDS = 30

DEFAULT_BLOCK_DISK_NAME = "block-disk"
DEFAULT_FILESYSTEM_DISK_NAME_PREFIX = "default-disk"

SPDK_SETUP_SCRIPT = "/usr/src/spdk/scripts/setup.sh"
BDF_PATTERN = r"^[a-fA-F0-9]{4}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}\.[a-fA-F0-9]$"
USERSPACE_PCI_DRIVERS = ["vfio_pci", "uio_pci_generic"]
# What the SPDK setup script reports for a device that is bound to no driver.
NO_PCI_DRIVER = "-"
