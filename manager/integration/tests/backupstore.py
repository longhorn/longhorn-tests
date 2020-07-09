import os
import base64
import hashlib
import json
import subprocess


from minio import Minio
from minio.error import ResponseError
from urllib.parse import urlparse

from common import SETTING_BACKUP_TARGET
from common import SETTING_BACKUP_TARGET_CREDENTIAL_SECRET
from common import LONGHORN_NAMESPACE
from common import is_backupTarget_s3
from common import is_backupTarget_nfs
from common import get_longhorn_api_client
from common import wait_for_backup_volume_delete

BACKUPSTORE_BV_PREFIX = "/backupstore/volumes/"


TEMP_FILE_PATH = "/tmp/temp_file"


def backupstore_cleanup(client):
    backup_volumes = client.list_backup_volume()

    for backup_volume in backup_volumes:
        backups = backup_volume.backupList()

        for backup in backups:
            backup_name = backup.name
            backup_volume.backupDelete(name=backup_name)
            wait_for_backup_volume_delete(client, backup_name)

        client.delete(backup_volume)

    backup_volumes = client.list_backup_volume()
    assert backup_volumes.data == []


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


def nfs_write_backup_cfg_file(client, volume_name, backup_name, data):
    nfs_backup_cfg_file_path = nfs_get_backup_cfg_file_path(client,
                                                            volume_name,
                                                            backup_name)
    cfg_file = open(nfs_backup_cfg_file_path, 'w')
    cfg_file.write(str(data))
    cfg_file.close()


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


def backupstore_delete_backup_cfg_file(client, core_api, volume_name, backup_name):  # NOQA
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        minio_delete_backup_cfg_file(client,
                                     core_api,
                                     volume_name,
                                     backup_name)

    elif is_backupTarget_nfs(backupstore):
        nfs_delete_backup_cfg_file(client, volume_name, backup_name)


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


def backupstore_delete_random_backup_block(client, core_api, volume_name):
    backupstore = backupstore_get_backup_target(client)

    if is_backupTarget_s3(backupstore):
        minio_delete_random_backup_block(client, core_api, volume_name)

    elif is_backupTarget_nfs(backupstore):
        nfs_delete_random_backup_block(client, volume_name)


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
