import sys
import logging

import longhorn
import common

# env setup
NODE_NAME = "jmoody-2818-post-work1"
VOLUME_PREFIX = "test-1859-post"
SNAPSHOT_NAME = "test-1859-post"

# local connection forwarded to cluster
# kubectl port-forward services/longhorn-frontend 8080:http -n longhorn-system
LONGHORN_URL = 'http://localhost:8080/v1'  # forwarded to cluster

NAMESPACE = "default"
VOLUME_SIZE = str(16 * 1024 * 1024)
VOLUME_COUNT = 1

# we only keep 5 completed backups per replica
# https://github.com/longhorn/longhorn-engine/blob/42283ca52d02838dfea437fa0552a2e2ee95447d/pkg/sync/rpc/server.go#L40
# while we keep an infinite amount of failed backup statuses
BACKUP_COUNT = 5


def attach_volume(client, volume_name, host_name):
    log = logging.getLogger()
    client.by_id_volume(volume_name).attach(hostId=host_name)
    volume = common.wait_for_volume_healthy(client, volume_name)
    log.info("volume %s attached to node %s" % (volume.name, host_name))
    return volume


def create_volume(client, volume_name):
    log = logging.getLogger()
    volume = client.by_id_volume(volume_name)
    if volume is not None:
        log.info("volume %s existing volume" % volume.name)
        return volume

    client.create_volume(name=volume_name, size=VOLUME_SIZE,
                         numberOfReplicas=3,
                         backingImage="", frontend="blockdev")
    volume = common.wait_for_volume_detached(client, volume_name)
    log.info("volume %s created" % volume.name)
    return volume


def get_snapshot(volume, snapshot_name):
    snapshots = volume.snapshotList(volume=volume.name)
    for snap in snapshots:
        if snap["name"] == snapshot_name:
            return volume.snapshotGet(name=snapshot_name)
    return None


def create_snapshot(volume, snapshot_name):
    log = logging.getLogger()
    snapshot = get_snapshot(volume, snapshot_name)
    if snapshot is not None:
        log.info("volume %s existing snapshot %s" % (volume.name, snapshot.name))
        return snapshot

    snapshot = volume.snapshotCreate(name=snapshot_name)
    log.info("volume %s created snapshot %s" % (volume.name, snapshot.name))
    return snapshot


def create_backup(volume, snapshot_name):
    log = logging.getLogger()
    backup = volume.snapshotBackup(name=snapshot_name)
    log.info("volume %s created backup %s" % (volume.name, backup.id))
    return backup


def test_1859_backup_status():
    log = logging.getLogger()
    client = longhorn.Client(url=LONGHORN_URL)

    # create volumes
    volumes = list()
    for i in range(VOLUME_COUNT):
        volume_name = VOLUME_PREFIX + str(i)
        create_volume(client, volume_name)
        volume = attach_volume(client, volume_name, NODE_NAME)
        volumes.append(volume)

    # create snapshots:
    snapshots = list()
    for i, volume in enumerate(volumes):
        snapshot = create_snapshot(volume, SNAPSHOT_NAME)
        snapshots.append(snapshot)

    # create backups:
    backups = dict()
    for _, volume in enumerate(volumes):
        backups[volume.name] = list()
        for _ in range(BACKUP_COUNT):
            backup = create_backup(volume, SNAPSHOT_NAME)
            backups[volume.name].append(backup)

    log.info("created %s volumes with %s backups each" % (VOLUME_COUNT, BACKUP_COUNT))


if __name__ == '__main__':
    # setup the monitor
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(stream=sys.stdout,
                        level=logging.INFO,
                        format=log_format)
    logging.info("1859-backup-test-started")

    # test bug + fix
    test_1859_backup_status()

    logging.info("1859-backup-test-finished")
