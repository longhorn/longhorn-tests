Steps to run the setupRancher.py and teardownRancher.py to setup and teardown machines for longhorn tests

# first create a properties file to retrieve machine build results from container
# it will contain CATTLE_TEST_URL and LONGHORN_BACKUP_SERVER_IP
touch $PROPERTY_FILE_NAME

# call setupRancher.py using environment variables to setup longhorn test machines
docker run --rm -v $(pwd)/$PROPERTY_FILE_NAME:/$PROPERTY_FILE_NAME \
    -e PROPERTY_FILE_NAME="$PROPERTY_FILE_NAME" \
    -e GCE_SERVICE_KEY_JSON="$GCE_SERVICE_KEY_JSON" \
    -e GCE_RANCHER_PROJECT_NAME="$GCE_RANCHER_PROJECT_NAME" \
    -e GCE_RANCHER_PROJECT_ZONE="$GCE_RANCHER_PROJECT_ZONE" \
    -e GCE_NFS_SERVER_NAME="$GCE_NFS_SERVER_NAME" \
    -e GCE_RANCHER_SERVER_NAME="$GCE_RANCHER_SERVER_NAME" \
    -e PACKET_HOST_NAMES="$PACKET_HOST_NAMES" \
    -e PACKET_RANCHER_AUTH_TOKEN="$PACKET_RANCHER_AUTH_TOKEN" \
    -e PACKET_RANCHER_PROJECT_ID="$PACKET_RANCHER_PROJECT_ID" \
    -e PACKET_HOST_MACHINE_TYPE="$PACKET_HOST_MACHINE_TYPE" \
    -e PACKET_HOST_OS_IMG="$PACKET_HOST_OS_IMG" \
    -e PACKET_HOST_CLOUD_CONFIG="$PACKET_HOST_CLOUD_CONFIG" \
    -e GCE_RANCHER_MACHINE_TYPE="$GCE_RANCHER_MACHINE_TYPE" \
    -e GCE_RANCHER_OS_IMG="$GCE_RANCHER_OS_IMG" \
    -e GCE_STARTUP_SCRIPT_RANCHER="$GCE_STARTUP_SCRIPT_RANCHER" \
    -e GCE_STARTUP_SCRIPT_NFS="$GCE_STARTUP_SCRIPT_NFS" \
    rancher/longhorn-env-setup setupRancher.py


# call teardownRancher.py using environment variables to destroy longhorn test machines
docker run --rm \
    -e GCE_SERVICE_KEY_JSON="$GCE_SERVICE_KEY_JSON" \
    -e GCE_RANCHER_PROJECT_NAME="$GCE_RANCHER_PROJECT_NAME" \
    -e GCE_RANCHER_PROJECT_ZONE="$GCE_RANCHER_PROJECT_ZONE" \
    -e GCE_NFS_SERVER_NAME="$GCE_NFS_SERVER_NAME" \
    -e GCE_RANCHER_SERVER_NAME="$GCE_RANCHER_SERVER_NAME" \
    -e PACKET_HOST_NAMES="$PACKET_HOST_NAMES" \
    -e PACKET_RANCHER_AUTH_TOKEN="$PACKET_RANCHER_AUTH_TOKEN" \
    -e PACKET_RANCHER_PROJECT_ID="$PACKET_RANCHER_PROJECT_ID" \
    rancher/longhorn-env-setup teardownRancher.py 


where environment variables are:
PROPERTY_FILE_NAME:         result from running setupRancher.py, contains CATTLE_TEST_URL and LONGHORN_BACKUP_SERVER_IP
GCE_SERVICE_KEY_JSON:       a GCE service account secrete key
GCE_RANCHER_PROJECT_NAME:   rancher project name on GCE
GCE_RANCHER_PROJECT_ZONE:   rancher project zone on GCE
GCE_NFS_SERVER_NAME:        NFS server name on GCE to be created
GCE_RANCHER_SERVER_NAME:    Rancher server name on GCE to be created
GCE_RANCHER_MACHINE_TYPE:   Rancher server machine type, such as n1-standard-4
GCE_RANCHER_OS_IMG:         Rancher server OS image name, such as ubuntu-1604-lts
GCE_STARTUP_SCRIPT_RANCHER: Rancher server startup script run by GCE during boot
GCE_STARTUP_SCRIPT_NFS:     NFS server startup script run by GCE during boot
PACKET_HOST_NAMES:          a list of hosts to be created on Packet separated by commas, such as host1,host2,host3
PACKET_RANCHER_AUTH_TOKEN:  rancher project auth token on Packet
PACKET_RANCHER_PROJECT_ID:  rancher project on Packet
PACKET_HOST_MACHINE_TYPE:   host machine type on Packet, such as baremetal_1
PACKET_HOST_OS_IMG:         host OS image on Packet, such as ubuntu_14_04
PACKET_HOST_CLOUD_CONFIG:   host startup script run by Packet during boot
