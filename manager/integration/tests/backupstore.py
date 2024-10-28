import os
import time
import pytest
import base64
import hashlib
import json
import subprocess

from minio import Minio
from minio.error import ResponseError
from urllib.parse import urlparse

from common import SETTING_BACKUP_TARGET
from common import SETTING_BACKUP_TARGET_CREDENTIAL_SECRET
from common import SETTING_BACKUPSTORE_POLL_INTERVAL
from common import LONGHORN_NAMESPACE
from common import cleanup_all_volumes
from common import is_backupTarget_s3
from common import is_backupTarget_nfs
from common import is_backupTarget_cifs
from common import get_longhorn_api_client
from common import delete_backup_volume
from common import delete_backup_backing_image
from common import get_backupstore_url
from common import get_backupstore_poll_interval
from common import get_backupstores
from common import system_backups_cleanup
from common import get_custom_object_api_client
from common import wait_for_backup_delete

BACKUPSTORE_BV_PREFIX = "/backupstore/volumes/"
BACKUPSTORE_LOCK_DURATION = 150

TEMP_FILE_PATH = "/tmp/temp_file"

BACKUPSTORE = get_backupstores()


@pytest.fixture
def backupstore_invalid(client):
    set_backupstore_invalid(client)
    yield
    reset_backupstore_setting(client)
    backup_cleanup()


@pytest.fixture
def backupstore_s3(client):
    set_backupstore_s3(client)
    yield
    reset_backupstore_setting(client)


@pytest.fixture
def backupstore_nfs(client):
    set_backupstore_nfs(client)
    yield
    reset_backupstore_setting(client)


@pytest.fixture(params=BACKUPSTORE)
def set_random_backupstore(request, client):
    if request.param == "s3":
        set_backupstore_s3(client)
    elif request.param == "nfs":
        set_backupstore_nfs(client)
        mount_nfs_backupstore(client)
    elif request.param == "cifs":
        set_backupstore_cifs(client)

    yield
    cleanup_all_volumes(client)
    backupstore_cleanup(client)
    system_backups_cleanup(client)
    reset_backupstore_setting(client)

    if request.param == "nfs":
        umount_nfs_backupstore(client)


def reset_backupstore_setting(client):
    backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
    client.update(backup_target_setting, value="")
    backup_target_credential_setting = client.by_id_setting(
        SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
    client.update(backup_target_credential_setting, value="")
    backup_store_poll_interval = client.by_id_setting(
        SETTING_BACKUPSTORE_POLL_INTERVAL)
    client.update(backup_store_poll_interval, value="300")


def set_backupstore_invalid(client):
    poll_interval = get_backupstore_poll_interval()
    set_backupstore_url(client, "nfs://notexist:/opt/backupstore")
    set_backupstore_credential_secret(client, "")
    set_backupstore_poll_interval(client, poll_interval)


def set_backupstore_s3(client):
    backupstores = get_backupstore_url()
    poll_interval = get_backupstore_poll_interval()
    for backupstore in backupstores:
        if is_backupTarget_s3(backupstore):
            backupsettings = backupstore.split("$")
            set_backupstore_url(client, backupsettings[0])
            set_backupstore_credential_secret(client, backupsettings[1])
            set_backupstore_poll_interval(client, poll_interval)
            break


def set_backupstore_nfs(client):
    backupstores = get_backupstore_url()
    poll_interval = get_backupstore_poll_interval()
    for backupstore in backupstores:
        if is_backupTarget_nfs(backupstore):
            set_backupstore_url(client, backupstore)
            set_backupstore_credential_secret(client, "")
            set_backupstore_poll_interval(client, poll_interval)
            break


def set_backupstore_cifs(client):
    backupstores = get_backupstore_url()
    poll_interval = get_backupstore_poll_interval()
    for backupstore in backupstores:
        if is_backupTarget_cifs(backupstore):
            backupsettings = backupstore.split("$")
            set_backupstore_url(client, backupsettings[0])
            set_backupstore_credential_secret(client, backupsettings[1])
            set_backupstore_poll_interval(client, poll_interval)
            break


def set_backupstore_url(client, url):
    backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
    backup_target_setting = client.update(backup_target_setting,
                                          value=url)
    assert backup_target_setting.value == url


def set_backupstore_credential_secret(client, credential_secret):
    backup_target_credential_setting = client.by_id_setting(
        SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
    backup_target_credential_setting = client.update(
        backup_target_credential_setting, value=credential_secret)
    assert backup_target_credential_setting.value == credential_secret


def set_backupstore_poll_interval(client, poll_interval):
    backup_store_poll_interval_setting = client.by_id_setting(
        SETTING_BACKUPSTORE_POLL_INTERVAL)
    backup_target_poll_interal_setting = client.update(
        backup_store_poll_interval_setting, value=poll_interval)
    assert backup_target_poll_interal_setting.value == poll_interval


def mount_nfs_backupstore(client, mount_path="/mnt/nfs"):
    cmd = ["mkdir", "-p", mount_path]
    subprocess.check_output(cmd)
    nfs_backuptarget = client.by_id_setting(SETTING_BACKUP_TARGET).value
    nfs_url = urlparse(nfs_backuptarget).netloc + \
        urlparse(nfs_backuptarget).path
    cmd = ["mount", "-t", "nfs", "-o", "nfsvers=4.2", nfs_url, mount_path]
    subprocess.check_output(cmd)


def umount_nfs_backupstore(client, mount_path="/mnt/nfs"):
    cmd = ["umount", mount_path]
    subprocess.check_output(cmd)
    cmd = ["rmdir", mount_path]
    subprocess.check_output(cmd)


def backup_cleanup():
    # Use k8s api to delete all backup especially backup in error state
    # Because backup in error state does not have backup volume
    api = get_custom_object_api_client()
    backups = api.list_namespaced_custom_object("longhorn.io",
                                                "v1beta2",
                                                "longhorn-system",
                                                "backups")
    for backup in backups['items']:
        api.delete_namespaced_custom_object("longhorn.io",
                                            "v1beta2",
                                            "longhorn-system",
                                            "backups",
                                            backup['metadata']['name'])


def backupstore_cleanup(client):
    backup_volumes = client.list_backup_volume()
    # we delete the whole backup volume, which skips block gc
    for backup_volume in backup_volumes:
        delete_backup_volume(client, backup_volume.name)

    backup_volumes = client.list_backup_volume()
    assert backup_volumes.data == []

    backup_backing_images = client.list_backup_backing_image()
    for backup_backing_image in backup_backing_images:
        delete_backup_backing_image(client, backup_backing_image.name)

    backup_backing_images = client.list_backup_backing_image()
    assert backup_backing_images.data == []


def minio_get_api_client(client, core_api, minio_secret_name):
    secret = core_api.read_namespaced_secret(name=minio_secret_name,
                                             namespace=LONGHORN_NAMESPACE)

    base64_minio_access_key = secret.data['AWS_ACCESS_KEY_ID']
    base64_minio_secret_key = secret.data['AWS_SECRET_ACCESS_KEY']
    base64_minio_endpoint_url = secret.data['AWS_ENDPOINTS']
    base64_minio_cert = secret.data['AWS_CERT']

    minio_access_key = \
        base64.b64decode(base64_minio_access_key).decode("utf-8")
    minio_secret_key = \
        base64.b64decode(base64_minio_secret_key).decode("utf-8")

    minio_endpoint_url = \
        base64.b64decode(base64_minio_endpoint_url).decode("utf-8")
    minio_endpoint_url = minio_endpoint_url.replace('https://', '')

    minio_cert_file_path = "/tmp/minio_cert.crt"
    with open(minio_cert_file_path, 'w') as minio_cert_file:
        base64_minio_cert = \
            base64.b64decode(base64_minio_cert).decode("utf-8")
        minio_cert_file.write(base64_minio_cert)

    os.environ["SSL_CERT_FILE"] = minio_cert_file_path

    return Minio(minio_endpoint_url,
                 access_key=minio_access_key,
                 secret_key=minio_secret_key,
                 secure=True)


def minio_get_backupstore_bucket_name(client):
    backupstore = backupstore_get_backup_target(client)

    assert is_backupTarget_s3(backupstore)
    bucket_name = urlparse(backupstore).netloc.split('@')[0]
    return bucket_name


def minio_get_backupstore_path(client):
    backupstore = backupstore_get_backup_target(client)
    assert is_backupTarget_s3(backupstore)
    backupstore_path = urlparse(backupstore).path.split('$')[0].strip("/")
    return backupstore_path


def get_nfs_mount_point(client):
    nfs_backuptarget = client.by_id_setting(SETTING_BACKUP_TARGET).value
    nfs_url = urlparse(nfs_backuptarget).netloc + \
        urlparse(nfs_backuptarget).path

    cmd = ["findmnt", "-t", "nfs4", "-n", "--output", "source,target"]
    stdout = subprocess.run(cmd, capture_output=True).stdout
    mount_info = stdout.decode().strip().split(" ")

    assert mount_info[0] == nfs_url
    return mount_info[1]


def backup_volume_path(volume_name):
    volume_name_sha512 = \
        hashlib.sha512(volume_name.encode('utf-8')).hexdigest()

    volume_dir_level_1 = volume_name_sha512[0:2]
    volume_dir_level_2 = volume_name_sha512[2:4]

    backupstore_bv_path = BACKUPSTORE_BV_PREFIX + \
        volume_dir_level_1 + "/" + \
        volume_dir_level_2 + "/" + \
        volume_name

    return backupstore_bv_path


def backupstore_get_backup_volume_prefix(client, volume_name):
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        return minio_get_backup_volume_prefix(volume_name)

    elif is_backupTarget_nfs(backupstore):
        return nfs_get_backup_volume_prefix(client, volume_name)

    else:
        raise NotImplementedError


def minio_get_backup_volume_prefix(volume_name):
    client = get_longhorn_api_client()
    backupstore_bv_path = backup_volume_path(volume_name)
    backupstore_path = minio_get_backupstore_path(client)
    return backupstore_path + backupstore_bv_path


def nfs_get_backup_volume_prefix(client, volume_name):
    mount_point = get_nfs_mount_point(client)
    return mount_point + backup_volume_path(volume_name)


def backupstore_get_backup_target(client):
    backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
    return backup_target_setting.value


def backupstore_get_secret(client):
    backup_target_credential_setting = client.by_id_setting(
        SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)

    return backup_target_credential_setting.value


def backupstore_get_backup_cfg_file_path(client, volume_name, backup_name):
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        return minio_get_backup_cfg_file_path(volume_name, backup_name)

    elif is_backupTarget_nfs(backupstore):
        return nfs_get_backup_cfg_file_path(client, volume_name, backup_name)

    else:
        raise NotImplementedError


def minio_get_backup_cfg_file_path(volume_name, backup_name):
    prefix = minio_get_backup_volume_prefix(volume_name)
    return prefix + "/backups/backup_" + backup_name + ".cfg"


def nfs_get_backup_cfg_file_path(client, volume_name, backup_name):
    prefix = nfs_get_backup_volume_prefix(client, volume_name)
    return prefix + "/backups/backup_" + backup_name + ".cfg"


def backupstore_get_volume_cfg_file_path(client, volume_name):
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        return minio_get_volume_cfg_file_path(volume_name)

    elif is_backupTarget_nfs(backupstore):
        return nfs_get_volume_cfg_file_path(client, volume_name)

    else:
        raise NotImplementedError


def nfs_get_volume_cfg_file_path(client, volume_name):
    prefix = nfs_get_backup_volume_prefix(client, volume_name)
    return prefix + "/volume.cfg"


def minio_get_volume_cfg_file_path(volume_name):
    prefix = minio_get_backup_volume_prefix(volume_name)
    return prefix + "/volume.cfg"


def backupstore_get_backup_blocks_dir(client, volume_name):
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        return minio_get_backup_blocks_dir(volume_name)

    elif is_backupTarget_nfs(backupstore):
        return nfs_get_backup_blocks_dir(client, volume_name)

    else:
        raise NotImplementedError


def minio_get_backup_blocks_dir(volume_name):
    prefix = minio_get_backup_volume_prefix(volume_name)
    return prefix + "/blocks"


def nfs_get_backup_blocks_dir(client, volume_name):
    prefix = nfs_get_backup_volume_prefix(client, volume_name)
    return prefix + "/blocks"


def backupstore_create_file(client, core_api, file_path, data={}):
    backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
    backupstore = backup_target_setting.value

    if is_backupTarget_s3(backupstore):
        return mino_create_file_in_backupstore(client,
                                               core_api,
                                               file_path,
                                               data)
    elif is_backupTarget_nfs(backupstore):
        return nfs_create_file_in_backupstore(file_path, data={})

    else:
        raise NotImplementedError


def mino_create_file_in_backupstore(client, core_api, file_path, data={}): # NOQA
    backup_target_credential_setting = client.by_id_setting(
        SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)

    secret_name = backup_target_credential_setting.value

    minio_api = minio_get_api_client(client, core_api, secret_name)
    bucket_name = minio_get_backupstore_bucket_name(client)

    if len(data) == 0:
        data = {"testkey": "test data from mino_create_file_in_backupstore()"}

    with open(TEMP_FILE_PATH, 'w') as temp_file:
        json.dump(data, temp_file)

    try:
        with open(TEMP_FILE_PATH, 'rb') as temp_file:
            temp_file_stat = os.stat(TEMP_FILE_PATH)
            minio_api.put_object(bucket_name,
                                 file_path,
                                 temp_file,
                                 temp_file_stat.st_size)
    except ResponseError as err:
        print(err)


def nfs_create_file_in_backupstore(file_path, data={}):
    with open(file_path, 'w') as cfg_file:
        cfg_file.write(str(data))

def backupstore_write_backup_cfg_file(client, core_api, volume_name, backup_name, data): # NOQA
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        minio_write_backup_cfg_file(client,
                                    core_api,
                                    volume_name,
                                    backup_name,
                                    data)

    elif is_backupTarget_nfs(backupstore):
        nfs_write_backup_cfg_file(client,
                                  volume_name,
                                  backup_name,
                                  data)

    else:
        raise NotImplementedError


def nfs_write_backup_cfg_file(client, volume_name, backup_name, data):
    nfs_backup_cfg_file_path = nfs_get_backup_cfg_file_path(client,
                                                            volume_name,
                                                            backup_name)
    with open(nfs_backup_cfg_file_path, 'w') as cfg_file:
        cfg_file.write(str(data))


def minio_write_backup_cfg_file(client, core_api, volume_name, backup_name, backup_cfg_data): # NOQA
    secret_name = backupstore_get_secret(client)
    assert secret_name != ''

    minio_api = minio_get_api_client(client, core_api, secret_name)
    bucket_name = minio_get_backupstore_bucket_name(client)
    minio_backup_cfg_file_path = minio_get_backup_cfg_file_path(volume_name,
                                                                backup_name)

    tmp_backup_cfg_file = "/tmp/backup_" + backup_name + ".cfg"
    with open(tmp_backup_cfg_file, 'w') as tmp_bkp_cfg_file:
        tmp_bkp_cfg_file.write(str(backup_cfg_data))

    try:
        with open(tmp_backup_cfg_file, 'rb') as tmp_bkp_cfg_file:
            tmp_bkp_cfg_file_stat = os.stat(tmp_backup_cfg_file)
            minio_api.put_object(bucket_name,
                                 minio_backup_cfg_file_path,
                                 tmp_bkp_cfg_file,
                                 tmp_bkp_cfg_file_stat.st_size)
    except ResponseError as err:
        print(err)


def backupstore_delete_file(client, core_api, file_path):
    backup_target_setting = client.by_id_setting(SETTING_BACKUP_TARGET)
    backupstore = backup_target_setting.value

    if is_backupTarget_s3(backupstore):
        return mino_delete_file_in_backupstore(client,
                                               core_api,
                                               file_path)

    elif is_backupTarget_nfs(backupstore):
        return nfs_delete_file_in_backupstore(file_path)

    else:
        raise NotImplementedError


def mino_delete_file_in_backupstore(client, core_api, file_path):
    backup_target_credential_setting = client.by_id_setting(
        SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)

    secret_name = backup_target_credential_setting.value

    minio_api = minio_get_api_client(client, core_api, secret_name)
    bucket_name = minio_get_backupstore_bucket_name(client)

    try:
        minio_api.remove_object(bucket_name, file_path)
    except ResponseError as err:
        print(err)


def nfs_delete_file_in_backupstore(file_path):
    try:
        os.remove(file_path)
    except Exception as ex:
        print("error while deleting file:",
              file_path)
        print(ex)


def backupstore_delete_backup_cfg_file(client, core_api, volume_name, backup_name):  # NOQA
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        minio_delete_backup_cfg_file(client,
                                     core_api,
                                     volume_name,
                                     backup_name)

    elif is_backupTarget_nfs(backupstore):
        nfs_delete_backup_cfg_file(client, volume_name, backup_name)

    else:
        raise NotImplementedError


def nfs_delete_backup_cfg_file(client, volume_name, backup_name):
    nfs_backup_cfg_file_path = nfs_get_backup_cfg_file_path(client,
                                                            volume_name,
                                                            backup_name)
    try:
        os.remove(nfs_backup_cfg_file_path)
    except Exception as ex:
        print("error while deleting backup cfg file:",
              nfs_backup_cfg_file_path)
        print(ex)


def minio_delete_backup_cfg_file(client, core_api, volume_name, backup_name):
    secret_name = backupstore_get_secret(client)
    assert secret_name != ''

    minio_api = minio_get_api_client(client, core_api, secret_name)
    bucket_name = minio_get_backupstore_bucket_name(client)
    minio_backup_cfg_file_path = minio_get_backup_cfg_file_path(volume_name,
                                                                backup_name)

    try:
        minio_api.remove_object(bucket_name, minio_backup_cfg_file_path)
    except ResponseError as err:
        print(err)


def backupstore_delete_volume_cfg_file(client, core_api, volume_name):  # NOQA
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        minio_delete_volume_cfg_file(client,
                                     core_api,
                                     volume_name)

    elif is_backupTarget_nfs(backupstore):
        nfs_delete_volume_cfg_file(client, volume_name)

    else:
        raise NotImplementedError


def nfs_delete_volume_cfg_file(client, volume_name):
    nfs_volume_cfg_path = nfs_get_volume_cfg_file_path(client, volume_name)
    try:
        os.remove(nfs_volume_cfg_path)
    except Exception as ex:
        print("error while deleting backup cfg file:", nfs_volume_cfg_path)
        print(ex)


def minio_delete_volume_cfg_file(client, core_api, volume_name):
    secret_name = backupstore_get_secret(client)
    assert secret_name != ''

    minio_api = minio_get_api_client(client, core_api, secret_name)
    bucket_name = minio_get_backupstore_bucket_name(client)
    minio_volume_cfg_file_path = minio_get_volume_cfg_file_path(volume_name)

    try:
        minio_api.remove_object(bucket_name, minio_volume_cfg_file_path)
    except ResponseError as err:
        print(err)


def backupstore_create_dummy_in_progress_backup(client, core_api, volume_name):
    dummy_backup_cfg_data = {"Name": "dummy_backup",
                             "VolumeName": volume_name,
                             "CreatedTime": ""}

    backupstore_write_backup_cfg_file(client,
                                      core_api,
                                      volume_name,
                                      "backup-dummy",
                                      dummy_backup_cfg_data)


def backupstore_corrupt_backup_cfg_file(client, core_api, volume_name, backup_name): # NOQA
    corrupt_backup_cfg_data = "{corrupt: definitely"

    backupstore_write_backup_cfg_file(client,
                                      core_api,
                                      volume_name,
                                      backup_name,
                                      corrupt_backup_cfg_data)


def backupstore_delete_dummy_in_progress_backup(client, core_api, volume_name):
    backupstore_delete_backup_cfg_file(client,
                                       core_api,
                                       volume_name,
                                       "backup-dummy")
    # Longhorn automatically creates backup resource in the cluster
    # when there is a backup in the backupstore.
    # We need to check if the backup resource is deleted as well.
    wait_for_backup_delete(client, volume_name, "backup-dummy")


def backupstore_delete_random_backup_block(client, core_api, volume_name):
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        minio_delete_random_backup_block(client, core_api, volume_name)

    elif is_backupTarget_nfs(backupstore):
        nfs_delete_random_backup_block(client, volume_name)

    else:
        raise NotImplementedError


def nfs_delete_random_backup_block(client, volume_name):
    backup_blocks_dir = nfs_get_backup_blocks_dir(client, volume_name)
    cmd = ["find", backup_blocks_dir, "-type", "f"]
    find_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    head_cmd = subprocess.check_output(["head", "-1"], stdin=find_cmd.stdout)
    backup_block_file_path = head_cmd.decode().strip()

    try:
        os.remove(backup_block_file_path)
    except Exception as ex:
        print("error while deleting backup block file:",
              backup_block_file_path)
        print(ex)


def minio_delete_random_backup_block(client, core_api, volume_name):
    secret_name = backupstore_get_secret(client)
    assert secret_name != ''

    minio_api = minio_get_api_client(client, core_api, secret_name)

    bucket_name = minio_get_backupstore_bucket_name(client)
    backup_blocks_dir = minio_get_backup_blocks_dir(volume_name)

    block_object_files = minio_api.list_objects(bucket_name,
                                                prefix=backup_blocks_dir,
                                                recursive=True)

    object_file = block_object_files.__next__().object_name

    try:
        minio_api.remove_object(bucket_name, object_file)
    except ResponseError as err:
        print(err)


def backupstore_count_backup_block_files(client, core_api, volume_name):
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        return minio_count_backup_block_files(client, core_api, volume_name)

    elif is_backupTarget_nfs(backupstore):
        return nfs_count_backup_block_files(client, volume_name)

    else:
        raise NotImplementedError


def nfs_count_backup_block_files(client, volume_name):
    backup_blocks_dir = nfs_get_backup_blocks_dir(client, volume_name)
    cmd = ["find", backup_blocks_dir, "-type", "f"]
    find_cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    wc_cmd = subprocess.check_output(["wc", "-l"], stdin=find_cmd.stdout)
    backup_blocks_count = int(wc_cmd.decode().strip())

    return backup_blocks_count


def minio_count_backup_block_files(client, core_api, volume_name):
    secret_name = backupstore_get_secret(client)
    assert secret_name != ''

    minio_api = minio_get_api_client(client, core_api, secret_name)
    bucket_name = minio_get_backupstore_bucket_name(client)
    backup_blocks_dir = minio_get_backup_blocks_dir(volume_name)

    block_object_files = minio_api.list_objects(bucket_name,
                                                prefix=backup_blocks_dir,
                                                recursive=True)

    block_object_files_list = list(block_object_files)

    return len(block_object_files_list)


def backupstore_wait_for_lock_expiration():
    """
    waits 150 seconds which is the lock duration
    TODO: once we have implemented the delete functions,
          we can switch to removing the locks directly
    """
    time.sleep(BACKUPSTORE_LOCK_DURATION)
