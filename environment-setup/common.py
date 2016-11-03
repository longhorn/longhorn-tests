#!/usr/bin/env python

import os
import logging
import subprocess
import time
from oauth2client.client import GoogleCredentials
from googleapiclient import discovery


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("common")

packet_rancher_auth_token = os.environ["PACKET_RANCHER_AUTH_TOKEN"]
packet_rancher_project_id = os.environ["PACKET_RANCHER_PROJECT_ID"]

gce_key_file_content = os.environ["GCE_SERVICE_KEY_JSON"]
gce_key_file = "servicekey.json"
gce_rancher_project_name = os.environ["GCE_RANCHER_PROJECT_NAME"]
gce_rancher_project_zone = os.environ["GCE_RANCHER_PROJECT_ZONE"]

gce_nfs_server_name = os.environ["GCE_NFS_SERVER_NAME"]
gce_rancher_server_name = os.environ["GCE_RANCHER_SERVER_NAME"]
packet_host_names = os.environ["PACKET_HOST_NAMES"].split(",")


def gce_wait_for_operation(compute, operation):
    log.info('Waiting for GCE operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=gce_rancher_project_name,
            zone=gce_rancher_project_zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(10)


def initialize_gcloud():
    # generate a gce_key_file from environment variable text(multi-line string)
    servicekey_file = open(
        os.path.join(
            os.path.dirname(__file__),
            gce_key_file),
        'w')
    servicekey_file.write(gce_key_file_content)
    servicekey_file.close()

    retCode = subprocess.call(
        "./google-cloud-sdk/bin/gcloud auth activate-service-account \
        --key-file " + gce_key_file,
        shell=True)
    if retCode != 0:
        raise Exception("failed to gcloud auth activate-service-account")
    retCode = subprocess.call(
        "./google-cloud-sdk/bin/gcloud config set project " +
        gce_rancher_project_name,
        shell=True)
    if retCode != 0:
        raise Exception("failed to gcloud config set project")

    # before making any python client lib call, enable oauth
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gce_key_file
    credentials = GoogleCredentials.get_application_default()

    # initialize an instance of the Google Compute Engine service
    log.info("getting gce compute service ...")
    compute = discovery.build('compute', 'v1', credentials=credentials)
    return compute
