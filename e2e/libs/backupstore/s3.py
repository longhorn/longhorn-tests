import os
import base64
import json
import tempfile
import subprocess
import time

from minio import Minio
from minio.error import ResponseError

from workload.workload import get_workload_pod_names

from backupstore.base import Base

from urllib.parse import urlparse
from utility.utility import logging
from utility.utility import subprocess_exec_cmd
import utility.constant as constant

class S3(Base):

    MINIO_SERVER_PORT = 9000
    PORT_FORWARD = 39000

    def port_forward(self):
        return subprocess.Popen(
            ["/usr/local/bin/kubectl", "port-forward", "service/minio-service", f"{self.PORT_FORWARD}:{self.MINIO_SERVER_PORT}"])

    def get_api_client(self, minio_secret_name):
        secret = self.core_api.read_namespaced_secret(name=minio_secret_name,
                                                      namespace=constant.LONGHORN_NAMESPACE)

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
        minio_endpoint_url = f"localhost:{self.PORT_FORWARD}"

        minio_cert_file_path = os.path.join(os.getcwd(), "minio_cert.crt")
        with open(minio_cert_file_path, 'w') as minio_cert_file:
            base64_minio_cert = \
                base64.b64decode(base64_minio_cert).decode("utf-8")
            minio_cert_file.write(base64_minio_cert)

        os.environ["SSL_CERT_FILE"] = minio_cert_file_path

        return Minio(minio_endpoint_url,
                     access_key=minio_access_key,
                     secret_key=minio_secret_key,
                     secure=True)

    def get_backupstore_bucket_name(self):
        backupstore = self.backup_target
        assert self.is_backupTarget_s3(backupstore)
        bucket_name = urlparse(backupstore).netloc.split('@')[0]
        return bucket_name

    def get_backupstore_path(self):
        backupstore = self.backup_target
        assert self.is_backupTarget_s3(backupstore)
        backupstore_path = urlparse(backupstore).path.split('$')[0].strip("/")
        return backupstore_path

    def get_backup_volume_prefix(self, volume_name):
        backupstore_bv_path = self.backup_volume_path(volume_name)
        backupstore_path = self.get_backupstore_path()
        return backupstore_path + backupstore_bv_path

    def get_backup_cfg_file_path(self, volume_name, backup_name):
        prefix = self.get_backup_volume_prefix(volume_name)
        return prefix + "/backups/backup_" + backup_name + ".cfg"

    def get_volume_cfg_file_path(self, volume_name):
        prefix = self.get_backup_volume_prefix(volume_name)
        return prefix + "/volume.cfg"

    def get_backup_blocks_dir(self, volume_name):
        prefix = self.get_backup_volume_prefix(volume_name)
        return prefix + "/blocks"

    def create_file_in_backupstore(self, file_path, data={}): # NOQA

        process = self.port_forward()

        secret_name = self.secret

        minio_api = self.get_api_client(secret_name)
        bucket_name = self.get_backupstore_bucket_name()

        if len(data) == 0:
            data = {"testkey": "test data from create_file_in_backupstore()"}

        with tempfile.NamedTemporaryFile('w') as fp:
            json.dump(data, fp)
            fp.flush()
            try:
                with open(fp.name, mode='rb') as f:
                    temp_file_stat = os.stat(fp.name)
                    minio_api.put_object(bucket_name,
                                         file_path,
                                         f,
                                         temp_file_stat.st_size)
                    read_back = minio_api.get_object(bucket_name,
                                                     file_path)
                    assert read_back.data.decode("utf-8") == json.dumps(data), f"{read_back.data.decode('utf-8')}, {json.dumps(data)}"
                    logging(f"Created file {file_path} in backupstore")
            except ResponseError as err:
                print(err)

        process.kill()

    def write_backup_cfg_file(self, volume_name, backup_name, backup_cfg_data): # NOQA
        secret_name = self.secret
        assert secret_name != ''

        minio_api = self.get_api_client(secret_name)
        bucket_name = self.get_backupstore_bucket_name()
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

    def delete_file_in_backupstore(self, file_path):

        process = self.port_forward()

        secret_name = self.secret

        minio_api = self.get_api_client(secret_name)
        bucket_name = self.get_backupstore_bucket_name()

        try:
            minio_api.remove_object(bucket_name, file_path)
        except ResponseError as err:
            print(err)
        logging(f"Deleted file {file_path} in backupstore")

        process.kill()

    def delete_backup_cfg_file(self, volume_name, backup_name):
        secret_name = self.secret
        assert secret_name != ''

        minio_api = self.get_api_client(secret_name)
        bucket_name = self.get_backupstore_bucket_name()
        minio_backup_cfg_file_path = self.get_backup_cfg_file_path(volume_name,
                                                                   backup_name)

        try:
            minio_api.remove_object(bucket_name, minio_backup_cfg_file_path)
        except ResponseError as err:
            print(err)

    def delete_volume_cfg_file(self, volume_name):
        secret_name = self.secret
        assert secret_name != ''

        minio_api = self.get_api_client(secret_name)
        bucket_name = self.get_backupstore_bucket_name()
        minio_volume_cfg_file_path = self.get_volume_cfg_file_path(volume_name)

        try:
            minio_api.remove_object(bucket_name, minio_volume_cfg_file_path)
        except ResponseError as err:
            print(err)

    def delete_random_backup_block(self, volume_name):
        secret_name = self.secret
        assert secret_name != ''

        minio_api = self.get_api_client(secret_name)

        bucket_name = self.get_backupstore_bucket_name()
        backup_blocks_dir = self.get_backup_blocks_dir(volume_name)

        block_object_files = minio_api.list_objects(bucket_name,
                                                    prefix=backup_blocks_dir,
                                                    recursive=True)

        object_file = block_object_files.__next__().object_name

        try:
            minio_api.remove_object(bucket_name, object_file)
        except ResponseError as err:
            print(err)

    def count_backup_block_files(self, volume_name):
        secret_name = self.secret
        assert secret_name != ''

        minio_api = self.get_api_client(secret_name)
        bucket_name = self.get_backupstore_bucket_name()
        backup_blocks_dir = self.get_backup_blocks_dir(volume_name)

        block_object_files = minio_api.list_objects(bucket_name,
                                                    prefix=backup_blocks_dir,
                                                    recursive=True)

        block_object_files_list = list(block_object_files)

        return len(block_object_files_list)

    def create_dummy_backup(self, filename):
        logging(f"Creating dummy backup from file {filename}")
        self.extract_dummy_backup(filename)
        backupstore_pod_name = get_workload_pod_names("longhorn-test-minio")[0]
        cmd = ["kubectl", "exec", backupstore_pod_name, "--", "mkdir", "-p", "/storage/backupbucket/backupstore"]
        subprocess_exec_cmd(cmd)
        cmd = ["kubectl", "-c", "minio-helper", "cp", "./backupstore", f"{backupstore_pod_name}:/storage/backupbucket/backupstore"]
        subprocess_exec_cmd(cmd)
        cmd = ["rm", "-rf", "./backupstore"]
        subprocess_exec_cmd(cmd)
        # wait for backup sync by sleeping for the poll interval
        time.sleep(30)
        logging(f"Created dummy backup from file {filename}")
