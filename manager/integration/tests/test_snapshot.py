import pytest
import os
import subprocess
import time
import datetime
import json
import pandas as pd

from common import client, volume_name  # NOQA
from common import update_setting
from common import get_self_host_id
from common import create_and_check_volume, wait_for_volume_healthy
from common import wait_for_rebuild_start, wait_for_rebuild_complete
from common import create_snapshot
from common import settings_reset # NOQA

from test_basic import get_volume_endpoint

from test_scheduling import get_host_replica, wait_new_replica_ready  # NOQA

from common import Gi, Mi
from common import RETRY_COUNTS, RETRY_INTERVAL
from common import SETTING_SNAPSHOT_DATA_INTEGRITY
from common import SETTING_SNAPSHOT_DATA_INTEGRITY_IMMEDIATE_CHECK_AFTER_SNAPSHOT_CREATION  # NOQA
from common import SETTING_SNAPSHOT_DATA_INTEGRITY_CRONJOB
from common import SETTING_SNAPSHOT_FAST_REPLICA_REBUILD_ENABLED
from common import SNAPSHOT_DATA_INTEGRITY_IGNORED
from common import SNAPSHOT_DATA_INTEGRITY_ENABLED
from common import SNAPSHOT_DATA_INTEGRITY_FAST_CHECK
from common import SNAPSHOT_DATA_INTEGRITY_DISABLED

RETRY_WAIT_CHECKSUM_COUNTS = 600
SNAPSHOT_CHECK_PERIOD = 300

# For the checksum calculated by periodic check mechanism
# We cannot precisely know when the event happens,
# so put a toleration here and check if the time elapsed is expected.
SNAPSHOT_CHECK_TOLERATION_DELAY = 60

def test_snapshot_hash_global_enabled_with_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are immediately calculated when the snapshots
    are created
    - global data-integrity is set to enabled
    - global immediate_hash is enabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_ENABLED,
                                       "true", "true")
    check_hashed_and_with_immediate_hash(client, volume_name,
                                         SNAPSHOT_DATA_INTEGRITY_IGNORED)


def test_snapshot_hash_global_enabled_without_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are calculated by the periodic checksum check
    - global data-integrity is set to enabled
    - global immediate_hash is disabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_ENABLED,
                                       "false", "true")
    check_hashed_and_without_immediate_hash(client, volume_name,
                                            SNAPSHOT_DATA_INTEGRITY_IGNORED)


def test_snapshot_hash_global_fast_check_with_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are immediately calculated when the snapshots
    are created
    - global data-integrity is set to fast-check
    - global immediate_hash is enabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_FAST_CHECK,
                                       "true", "true")
    check_hashed_and_with_immediate_hash(client,
                                         volume_name,
                                         SNAPSHOT_DATA_INTEGRITY_IGNORED)


def test_snapshot_hash_global_fast_check_without_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are calculated by the periodic checksum check
    - global data-integrity is set to fast-check
    - global immediate_hash is disabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_FAST_CHECK,
                                       "false",
                                       "true")
    check_hashed_and_without_immediate_hash(client, volume_name,
                                            SNAPSHOT_DATA_INTEGRITY_IGNORED)  # NOQA


def test_snapshot_hash_global_disabled_with_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are not calculated when
    check when
    - global data-integrity is set to disabled
    - global immediate_hash is enabled
    - per-volume data-integrity is set to disabled and follows the
      global setting
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_DISABLED,
                                       "true",
                                       "true")
    check_per_volume_hash_disable(client, volume_name,
                                  SNAPSHOT_DATA_INTEGRITY_IGNORED)


def test_snapshot_hash_global_disabled_without_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are not calculated when
    check when
    - global data-integrity is set to disabled
    - global immediate_hash is disabled
    - per-volume data-integrity is set to disabled and follows the
      global setting
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_DISABLED,
                                       "false",
                                       "true")
    check_per_volume_hash_disable(client, volume_name,
                                  SNAPSHOT_DATA_INTEGRITY_IGNORED)


def test_snapshot_hash_global_disabled_and_per_volume_enabled_and_with_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are immediately calculated when the snapshots
    check when
    - global data-integrity is set to disabled
    - global immediate_hash is enabled
    - per-volume data-integrity is set to enabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_DISABLED,
                                       "true",
                                       "true")
    check_hashed_and_with_immediate_hash(client, volume_name,
                                         SNAPSHOT_DATA_INTEGRITY_ENABLED)


def test_snapshot_hash_global_disabled_and_per_volume_enabled_and_without_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are calculated by the periodic checksum check
    - global data-integrity is set to disabled
    - global immediate_hash is disabled
    - per-volume data-integrity is set to enabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_DISABLED,
                                       "false",
                                       "true")
    check_hashed_and_without_immediate_hash(client, volume_name,
                                            SNAPSHOT_DATA_INTEGRITY_ENABLED)


def test_snapshot_hash_global_disabled_and_per_volume_fast_check_and_with_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are immediately calculated when the snapshots
    check when
    - global data-integrity is set to disabled
    - global immediate_hash is enabled
    - per-volume data-integrity is set to fast-check
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_DISABLED,
                                       "true",
                                       "true")
    check_hashed_and_with_immediate_hash(client, volume_name,
                                         SNAPSHOT_DATA_INTEGRITY_FAST_CHECK)


def test_snapshot_hash_global_disabled_and_per_volume_fast_check_and_without_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are calculated by the periodic checksum check
    - global data-integrity is set to disabled
    - global immediate_hash is disabled
    - per-volume data-integrity is set to fast-check
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_DISABLED,
                                       "false",
                                       "true")
    check_hashed_and_without_immediate_hash(client, volume_name,
                                            SNAPSHOT_DATA_INTEGRITY_FAST_CHECK)


def test_snapshot_hash_global_enabled_and_per_volume_disable_and_with_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are not calculated
    - global data-integrity is set to enabled
    - global immediate_hash is enabled
    - per-volume data-integrity is set to disabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_ENABLED,
                                       "true",
                                       "true")
    check_per_volume_hash_disable(client, volume_name,
                                  SNAPSHOT_DATA_INTEGRITY_DISABLED)


def test_snapshot_hash_global_enabled_and_per_volume_disable_and_without_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are not calculated
    - global data-integrity is set to enabled
    - global immediate_hash is disabled
    - per-volume data-integrity is set to disabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_ENABLED,
                                       "false",
                                       "true")
    check_per_volume_hash_disable(client, volume_name,
                                  SNAPSHOT_DATA_INTEGRITY_DISABLED)


def test_snapshot_hash_global_fast_check_and_per_volume_disable_and_with_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are not calculated
    - global data-integrity is set to fast-check
    - global immediate_hash is enabled
    - per-volume data-integrity is set to disabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_FAST_CHECK,
                                       "true",
                                       "true")
    check_per_volume_hash_disable(client, volume_name,
                                  SNAPSHOT_DATA_INTEGRITY_DISABLED)


def test_snapshot_hash_global_fast_check_and_per_volume_disable_and_without_immediate_hash(client, volume_name, settings_reset):  # NOQA
    """
    Check snapshots' checksums are not calculated
    - global data-integrity is set to fast-check
    - global immediate_hash is disabled
    - per-volume data-integrity is set to disabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_FAST_CHECK,
                                       "false",
                                       "true")
    check_per_volume_hash_disable(client, volume_name,
                                  SNAPSHOT_DATA_INTEGRITY_DISABLED)


@pytest.mark.long_running
def test_snapshot_hash_detect_corruption_in_global_enabled_mode(client, volume_name, settings_reset):  # NOQA
    """
    Check the snapshot corruption can be detected and replica is rebuilt
    - global data-integrity is set to enabled
    - global immediate_hash is enabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_ENABLED,
                                       "true",
                                       "false")
    detect_and_repair_corrupted_replica(client, volume_name,
                                        SNAPSHOT_DATA_INTEGRITY_ENABLED,
                                        retry_count=SNAPSHOT_CHECK_PERIOD * 2)


@pytest.mark.long_running
def test_snapshot_hash_detect_corruption_in_global_fast_check_mode(client, volume_name, settings_reset):  # NOQA
    """
    Check the snapshot corruption can be detected and replica is rebuilt
    - global data-integrity is set to fast-check
    - global immediate_hash is enabled
    """
    prepare_settings_for_snapshot_test(client,
                                       SNAPSHOT_DATA_INTEGRITY_FAST_CHECK,
                                       "true",
                                       "false")
    detect_and_repair_corrupted_replica(client, volume_name,
                                        SNAPSHOT_DATA_INTEGRITY_FAST_CHECK,
                                        retry_count=SNAPSHOT_CHECK_PERIOD * 2)


def prepare_settings_for_snapshot_test(client, data_integrity, immediate_check, fast_replica_rebuild, period_in_second=SNAPSHOT_CHECK_PERIOD):  # NOQA
    period_in_minute = period_in_second // 60
    # Make the next hash time more predictable
    now = datetime.datetime.now()
    minutes = ",".join(str(e)
                       for e in [(now.minute + i) % 60
                                 for i in range(0, 30, period_in_minute)])
    hours = str(now.hour) + "," + str((now.hour + 1) % 24)

    cronjob = f"{minutes} {hours} * * *"

    update_setting(client,
                   SETTING_SNAPSHOT_DATA_INTEGRITY,
                   data_integrity)
    update_setting(client,
                   SETTING_SNAPSHOT_DATA_INTEGRITY_IMMEDIATE_CHECK_AFTER_SNAPSHOT_CREATION,  # NOQA
                   immediate_check)
    update_setting(client,
                   SETTING_SNAPSHOT_DATA_INTEGRITY_CRONJOB,
                   cronjob)
    update_setting(client,
                   SETTING_SNAPSHOT_FAST_REPLICA_REBUILD_ENABLED,
                   fast_replica_rebuild)


def detect_and_repair_corrupted_replica(client, volume_name, data_integrity_mode, retry_count=SNAPSHOT_CHECK_PERIOD+SNAPSHOT_CHECK_TOLERATION_DELAY):  # NOQA
    """
    1. Create and attach a volume
    2. Create snapshots
    3. Check snapshots' checksums are calculated and set and also
       check the checksums of the snapshot disk files are matched
       with the values from the api
    4. Corrupt the snapshot of replica on the local host
    5. Check the replica rebuild is ran correctly
    6. Check snapshots are repaired
    """

    # Step 1
    volume = create_and_check_volume(client, volume_name, 3, size=str(2 * Gi))

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = wait_for_volume_healthy(client, volume_name)
    volume = client.by_id_volume(volume_name)

    # Step 2
    create_snapshots(client, volume, 1536, 3)

    # Step 3
    assert check_snapshot_checksums_and_change_timestamps(volume)

    # Step 4
    snapshot_name = get_available_snapshot(volume)
    assert snapshot_name != ""

    assert corrupt_snapshot_on_local_host(volume, snapshot_name)

    # Step 5
    wait_for_rebuild_start(client, volume_name, retry_count, 1)

    volume = client.by_id_volume(volume_name)
    assert len(volume.replicas) == 3

    wait_for_rebuild_complete(client, volume_name)

    # Step 6
    # The checksum in checksum file should be updated by the periodic check
    time.sleep(SNAPSHOT_CHECK_PERIOD+SNAPSHOT_CHECK_TOLERATION_DELAY)
    assert check_snapshot_checksums_and_change_timestamps(volume)


def get_available_snapshot(volume):
    data_path = get_local_host_replica_data_path(volume)
    assert data_path != ""

    value = volume.snapshotList()
    snapshots = value.data
    for s in snapshots:
        if s.name != "volume-head" and s.usercreated is True:
            return s.name

    return ""


def corrupt_snapshot_on_local_host(volume, snapshot_name):
    data_path = get_local_host_replica_data_path(volume)
    assert data_path != ""

    disk_path = os.path.join(data_path,
                             "volume-snap-" + snapshot_name + ".img")
    exec_cmd = ["dd", "if=/dev/urandom", "of=" + disk_path,
                "bs=1", "count=10", "conv=notrunc"]
    try:
        subprocess.check_output(exec_cmd)
    except subprocess.CalledProcessError as e:
        print(e.output)
        return False
    return True


def check_snapshot_checksums_and_change_timestamps(volume):
    data_path = get_local_host_replica_data_path(volume)
    assert data_path != ""

    for i in range(RETRY_COUNTS):
        value = volume.snapshotList()
        snapshots = value.data
        for s in snapshots:
            if s.name != "volume-head" and s.usercreated is True:
                if s.checksum == "":
                    break

                # Check checksums in snapshot resource and in checksum file
                # are matched
                disk_path = os.path.join(data_path,
                                         "volume-snap-" + s.name + ".img")
                checksum = get_checksum_in_checksum_file(disk_path)
                print(f'snapshot {s.name}: '
                      f'checksum in resource={s.checksum}, '
                      f'checksum recalculated={checksum}')
                assert checksum == s.checksum

                # Check checksums in snapshot resource and the calculated value
                # are matched
                checksum = get_checksum_from_snapshot_disk_file(data_path,
                                                                s.name)
                print(f'snapshot {s.name}: '
                      f'checksum in resource={s.checksum}, '
                      f'checksum recorded={checksum}')
                assert checksum == s.checksum

                # Check ctime in checksum file and from stat are matched
                ctime_recorded = get_ctime_in_checksum_file(disk_path)
                ctime = get_ctime_from_snapshot_disk_file(data_path, s.name)

                print(f'snapshot {s.name}: '
                      f'ctime recorded={ctime_recorded}, '
                      f'ctime={ctime}')

                df = pd.DataFrame({'string': [ctime_recorded, ctime]})
                df['timestamp'] = pd.to_datetime(df['string'].str.replace(" +0000", "", regex=False))  # NOQA
                assert str(df['timestamp'][0]) == str(df['timestamp'][1])

            if snapshots.index(s) == len(snapshots)-1:
                return True

        time.sleep(RETRY_INTERVAL)

    return False


def get_checksum_in_checksum_file(disk_path):
    checksum_file = disk_path + ".checksum"
    try:
        f = open(checksum_file)
        metadata = json.load(f)
    except OSError as e:
        print(e)
        raise

    return metadata["checksum"]


def get_ctime_in_checksum_file(disk_path):
    checksum_file = disk_path + ".checksum"
    try:
        f = open(checksum_file)
        metadata = json.load(f)
    except OSError as e:
        print(e)
        raise

    return metadata["change_time"]


def check_snapshot_checksums_set(volume):
    value = volume.snapshotList()
    snapshots = value.data
    for s in snapshots:
        if s.name == "volume-head":
            continue
        if s.checksum == "":
            return False

    for s in snapshots:
        print(f'Checksum of snapshot {s.name} is {s.checksum}')
    return True


def get_local_host_replica_data_path(volume):
    lht_hostId = get_self_host_id()

    dataPath = ""
    replicas = volume.replicas
    for r in replicas:
        if r.hostId == lht_hostId:
            dataPath = r.dataPath
            break

    return dataPath


def get_checksum_from_snapshot_disk_file(data_path, snapshot_name):
    exec_cmd = ["java", "-jar", "/jacksum.jar", "-a", "crc64_go-iso",
                os.path.join(data_path,
                             "volume-snap-" + snapshot_name + ".img")]
    try:
        output = subprocess.check_output(exec_cmd)
    except subprocess.CalledProcessError as e:
        print(e.output)
        return ""

    data = str(output, 'utf-8')
    fields = data.split(' ')
    return fields[0]


def get_ctime_from_snapshot_disk_file(data_path, snapshot_name):
    exec_cmd = ["stat", "-c", "%z",
                os.path.join(data_path,
                             "volume-snap-" + snapshot_name + ".img")]
    try:
        output = subprocess.check_output(exec_cmd)
    except subprocess.CalledProcessError as e:
        print(e.output)
        return ""

    return str(output, 'utf-8').rstrip('\n') + " UTC"


def create_snapshots(client, volume, data_size, num_snapshots):  # NOQA
    dev = get_volume_endpoint(volume)

    snaps = []
    for i in range(num_snapshots):
        assert write_device_random_data(dev, data_size)
        snap = create_snapshot(client, volume.name)
        snaps.append(snap)

    snapshots = volume.snapshotList()
    snapMap = {}
    for snap in snapshots:
        snapMap[snap.name] = snap

    for i in range(num_snapshots):
        snap = snaps[i]
        assert snapMap[snap.name].name == snap.name
        assert snapMap[snap.name].removed is False
        if i > 0:
            prev_snap = snaps[i-1]
            assert snapMap[snap.name].parent == prev_snap.name


def write_device_random_data(dev, size):
    exec_cmd = ["dd", "if=/dev/urandom", "of=" + dev,
                "bs=1M", "count=" + str(size)]
    try:
        subprocess.check_output(exec_cmd)
    except subprocess.CalledProcessError as e:
        print(e.output)
        return False
    return True


def check_hashed_and_with_immediate_hash(client, volume_name, snapshot_data_integrity, volume_size=16, data_size=1):  # NOQA
    """
    1. Create and attach a volume
    2. Create snapshots
    3. Check snapshots' checksums are calculated and set and also
       check the checksums of the snapshot disk files are matched
       with the values from the api
    """

    # Step 1
    volume = create_and_check_volume(client, volume_name, 3,
                                     size=str(volume_size * Mi),
                                     snapshot_data_integrity=snapshot_data_integrity) # NOQA

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    # Step 2
    create_snapshots(client, volume, data_size, 3)

    # Step 3
    generate_checksums_time = wait_for_snapshot_checksums_generate(volume) # NOQA
    # The checksum should be calculated after creating the snapshot immediately
    time_range = range(0, SNAPSHOT_CHECK_TOLERATION_DELAY)
    assert generate_checksums_time in time_range


def check_hashed_and_without_immediate_hash(client, volume_name, snapshot_data_integrity): # NOQA
    """
    1. Create and attach a volume
    2. Create snapshots
    3. Sleep for 120 seconds. Check snapshots' checksums are not calculated
       and not set, because the immediate hash after snapshot creation feature
       is disabled
    4. Check snapshots' checksums are calculated and set by the periodic check
       mechanism
    """

    # Step 1
    volume = create_and_check_volume(client, volume_name, 3,
                                     size=str(16 * Mi),
                                     snapshot_data_integrity=snapshot_data_integrity) # NOQA

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    # Step 2
    create_snapshots(client, volume, 1, 3)

    # Step 3
    sleep_time = 120
    time.sleep(sleep_time)
    assert not check_snapshot_checksums_set(volume)

    # Step 4
    generate_checksums_time = wait_for_snapshot_checksums_generate(volume) # NOQA
    remaining = SNAPSHOT_CHECK_PERIOD - sleep_time
    time_range = range(remaining-SNAPSHOT_CHECK_TOLERATION_DELAY,
                       remaining+SNAPSHOT_CHECK_TOLERATION_DELAY)
    assert generate_checksums_time in time_range


def check_per_volume_hash_disable(client, volume_name, snapshot_data_integrity):  # NOQA
    """
    1. Create and attach a volume
    2. Create snapshots
    3. Sleep for SNAPSHOT_CHECK_PERIOD+SNAPSHOT_CHECK_TOLERATION_DELAY seconds.
       Check snapshots' checksums are calculated
       and set and also check the checksums of the snapshot disk files
       are matched with the values from the api
       Check snapshots' checksums are calculated by periodic snapshot
       verification mechanism and set and also check the checksums of
       the snapshot disk files are matched with the values from the api
    """

    # Step 1
    volume = create_and_check_volume(client, volume_name, 3,
                                     size=str(16 * Mi),
                                     snapshot_data_integrity=snapshot_data_integrity)  # NOQA

    lht_hostId = get_self_host_id()
    volume = volume.attach(hostId=lht_hostId)
    volume = wait_for_volume_healthy(client, volume_name)

    volume = client.by_id_volume(volume_name)

    # Step 2
    create_snapshots(client, volume, 1, 3)

    # Step 3
    time.sleep(SNAPSHOT_CHECK_PERIOD+SNAPSHOT_CHECK_TOLERATION_DELAY)
    assert not check_snapshot_checksums_set(volume)


def wait_for_snapshot_checksums_generate(volume_name):   # NOQA
    snapshot_checksums_generate = False

    count = 0
    for count in range(RETRY_WAIT_CHECKSUM_COUNTS):
        if check_snapshot_checksums_set(volume_name):
            print(f'All checksums are set in {count} sec')
            snapshot_checksums_generate = True
            break
        else:
            time.sleep(RETRY_INTERVAL)

    assert snapshot_checksums_generate
    return count
