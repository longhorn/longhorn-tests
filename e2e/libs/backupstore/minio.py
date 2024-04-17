from backupstore.base import Base
import os
import base64
import json
import tempfile
from minio import Minio
from minio.error import ResponseError
from urllib.parse import urlparse

class Minio(Base):

    def get_api_client(self, client, core_api, minio_secret_name):
        secret = core_api.read_namespaced_secret(name=minio_secret_name,
                                                 namespace='longhorn-system')

        base64_minio_access_key = secret.data['AWS_ACCESS_KEY_ID']
        base64_minio_secret_key = secret.data['AWS_SECRET_ACCESS_KEY']
        base64_minio_endpoint_url = secret.data['AWS_ENDPOINTS']

        minio_access_key = \
            base64.b64decode(base64_minio_access_key).decode("utf-8")
        minio_secret_key = \
            base64.b64decode(base64_minio_secret_key).decode("utf-8")

        minio_endpoint_url = \
            base64.b64decode(base64_minio_endpoint_url).decode("utf-8")
        minio_endpoint_url = minio_endpoint_url.replace('https://', '')

        return Minio(minio_endpoint_url,
                     access_key=minio_access_key,
                     secret_key=minio_secret_key,
                     secure=True)

    def get_backupstore_bucket_name(self, client):
        backupstore = self.get_backup_target()
        assert self.is_backupTarget_s3(backupstore)
        bucket_name = urlparse(backupstore).netloc.split('@')[0]
        return bucket_name

    def get_backupstore_path(self, client):
        backupstore = self.get_backup_target()
        assert self.is_backupTarget_s3(backupstore)
        backupstore_path = urlparse(backupstore).path.split('$')[0].strip("/")
        return backupstore_path

    def get_backup_volume_prefix(self, client, volume_name):
        backupstore_bv_path = self.backup_volume_path(volume_name)
        backupstore_path = self.get_backupstore_path(client)
        return backupstore_path + backupstore_bv_path

    def get_backup_cfg_file_path(self, client, volume_name, backup_name):
        prefix = self.get_backup_volume_prefix(client, volume_name)
        return prefix + "/backups/backup_" + backup_name + ".cfg"

    def get_volume_cfg_file_path(self, client, volume_name):
        prefix = self.get_backup_volume_prefix(client, volume_name)
        return prefix + "/volume.cfg"

    def get_backup_blocks_dir(self, client, volume_name):
        prefix = self.get_backup_volume_prefix(client, volume_name)
        return prefix + "/blocks"

    def create_file_in_backupstore(self, client, core_api, file_path, data={}): # NOQA

        secret_name = self.get_secret()

        minio_api = self.get_api_client(client, core_api, secret_name)
        bucket_name = self.get_backupstore_bucket_name(client)

        if len(data) == 0:
            data = {"testkey": "test data from mino_create_file_in_backupstore()"}

        with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
            json.dump(data, fp)
            try:
                with open(fp.name, mode='rb') as f:
                    temp_file_stat = os.stat(fp.name)
                    minio_api.put_object(bucket_name,
                                         file_path,
                                         f,
                                         temp_file_stat.st_size)
            except ResponseError as err:
                print(err)

    def write_backup_cfg_file(self, client, core_api, volume_name, backup_name, backup_cfg_data): # NOQA
        secret_name = self.get_secret()
        assert secret_name != ''

        minio_api = self.get_api_client(client, core_api, secret_name)
        bucket_name = self.get_backupstore_bucket_name(client)
        minio_backup_cfg_file_path = self.get_backup_cfg_file_path(volume_name,
                                                                   backup_name)

        with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
            fp.write(str(backup_cfg_data))
            fp.close()
            try:
                with open(fp.name, mode='rb') as f:
                    tmp_bkp_cfg_file_stat = os.stat(fp.name)
                    minio_api.put_object(bucket_name,
                                         minio_backup_cfg_file_path,
                                         f,
                                         tmp_bkp_cfg_file_stat.st_size)
            except ResponseError as err:
                print(err)

    def delete_file_in_backupstore(self, client, core_api, file_path):

        secret_name = self.get_secret()

        minio_api = self.get_api_client(client, core_api, secret_name)
        bucket_name = self.get_backupstore_bucket_name(client)

        try:
            minio_api.remove_object(bucket_name, file_path)
        except ResponseError as err:
            print(err)

    def delete_backup_cfg_file(self, client, core_api, volume_name, backup_name):
        secret_name = self.get_secret()
        assert secret_name != ''

        minio_api = self.get_api_client(client, core_api, secret_name)
        bucket_name = self.get_backupstore_bucket_name(client)
        minio_backup_cfg_file_path = self.get_backup_cfg_file_path(volume_name,
                                                                   backup_name)

        try:
            minio_api.remove_object(bucket_name, minio_backup_cfg_file_path)
        except ResponseError as err:
            print(err)

    def delete_volume_cfg_file(self, client, core_api, volume_name):
        secret_name = self.get_secret()
        assert secret_name != ''

        minio_api = self.get_api_client(client, core_api, secret_name)
        bucket_name = self.get_backupstore_bucket_name(client)
        minio_volume_cfg_file_path = self.get_volume_cfg_file_path(volume_name)

        try:
            minio_api.remove_object(bucket_name, minio_volume_cfg_file_path)
        except ResponseError as err:
            print(err)

    def delete_random_backup_block(self, client, core_api, volume_name):
        secret_name = self.get_secret()
        assert secret_name != ''

        minio_api = self.get_api_client(client, core_api, secret_name)

        bucket_name = self.get_backupstore_bucket_name(client)
        backup_blocks_dir = self.get_backup_blocks_dir(volume_name)

        block_object_files = minio_api.list_objects(bucket_name,
                                                    prefix=backup_blocks_dir,
                                                    recursive=True)

        object_file = block_object_files.__next__().object_name

        try:
            minio_api.remove_object(bucket_name, object_file)
        except ResponseError as err:
            print(err)

    def count_backup_block_files(self, client, core_api, volume_name):
        secret_name = self.get_secret()
        assert secret_name != ''

        minio_api = self.get_api_client(client, core_api, secret_name)
        bucket_name = self.get_backupstore_bucket_name(client)
        backup_blocks_dir = self.get_backup_blocks_dir(volume_name)

        block_object_files = minio_api.list_objects(bucket_name,
                                                    prefix=backup_blocks_dir,
                                                    recursive=True)

        block_object_files_list = list(block_object_files)

        return len(block_object_files_list)
