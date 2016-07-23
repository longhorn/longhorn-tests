#!/usr/bin/env python

import logging
import os
import urllib
import urllib2
import subprocess
import json
import time
import shlex
import errno
import threading
import common
import packet

log = logging.getLogger("setup-rancher")

packet_host_machine_type = os.environ["PACKET_HOST_MACHINE_TYPE"]
packet_host_os_img = os.environ["PACKET_HOST_OS_IMG"]
packet_host_cloud_config = os.environ["PACKET_HOST_CLOUD_CONFIG"]

gce_rancher_machine_type = os.environ["GCE_RANCHER_MACHINE_TYPE"]
gce_rancher_os_img = os.environ["GCE_RANCHER_OS_IMG"]
gce_startup_script_rancher = os.environ["GCE_STARTUP_SCRIPT_RANCHER"]
gce_startup_script_nfs = os.environ["GCE_STARTUP_SCRIPT_NFS"]

key_label = "longhorn:test"


def silent_remove_file(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
            raise  # re-raise exception if a different error occured


def gce_create_instance(compute, name, gce_startup_script):
    # Get the latest Debian Jessie image.
    image_response = compute.images().getFromFamily(
        project="ubuntu-os-cloud", family=gce_rancher_os_img).execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/%s/machineTypes/" % common.gce_rancher_project_zone \
        + gce_rancher_machine_type
    log.info("startup_script: %s", gce_startup_script)

    config = {
        'name': name,
        'machineType': machine_type,
        'tags': "alt-http-server",

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/devstorage.read_only',
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script',
                'value': gce_startup_script
            }]
        }
    }

    return compute.instances().insert(
        project=common.gce_rancher_project_name,
        zone=common.gce_rancher_project_zone,
        body=config).execute()


def gce_get_IP(compute, name):
    request = compute.instances().get(
        project=common.gce_rancher_project_name,
        zone=common.gce_rancher_project_zone,
        instance=name)
    vm = request.execute()

    # get the external IP
    IP = vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']
    return IP


def packet_wait_for_creation(manager, device):
    while True:
        device = manager.get_device(device.id)
        if device.state == 'active':
            log.info("packet device name: %s is active now", device.hostname)
            return device

        log.info(
            "waiting for packet device name: %s being created",
            device.hostname)
        time.sleep(60)


def cattle_get_host_registration_command(IP):
    # formulate a request for cattle API to get the host registration cmd
    url = "http://" + IP + ":8080/v1/projects/1a5/registrationtokens"
    log.info("ip: %s, url: %s", IP, url)

    # first do a post to create a registration resource, with empty data body
    values = {}
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)

    # total wait time is 5 minutes
    retries = 10
    retry_wait_time = 30
    response_json = ""
    while retries >= 0:
        retries -= 1
        try:
            response_json = urllib2.urlopen(req).read()
            log.info("got response from the cattle server at: %s", url)
            break
        except urllib2.URLError:
            if retries == -1:
                raise
            log.info("retrying the cattle server at: %s", url)
            time.sleep(retry_wait_time)

    # response is a json dictionary, we need to check the state to be active
    response_map = json.loads(response_json)
    id = response_map["id"]
    resource = {}
    while True:
        response_json = urllib2.urlopen(url).read()
        response_map = json.loads(response_json)
        resources = response_map["data"]

        # data is array of existing registration resources, so find the one we
        # just created
        for resource in resources:
            if resource["id"] == id:
                break
        if resource["state"] == "active":
            break
        time.sleep(5)

    return resource["command"]


def packet_register_to_cattle(device, registration_command):
    # get its ipv4 address
    IP = device.ip_addresses[0]['address']

    # remote run cattle registration command in packet VM instance
    log.info(
        "register packet host name: %s to cattle, registration_command: %s",
        device.hostname,
        registration_command)
    retries = 10
    while retries >= 0:
        retries -= 1
        retCode = subprocess.call(
            "ssh -i id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            rancher@%s '%s'" %
            (IP, registration_command), shell=True)
        if retCode == 0:
            log.info(
                "Done registering packet host name: %s to cattle",
                device.hostname)
            break
        else:
            log.warn(
                "Error registering packet host name: %s to cattle",
                device.hostname)
            if retries == -1:
                raise Exception(
                    "Cannot register packet host name: %s to cattle" %
                    device.hostname)
            log.info(
                "retrying to register packet host name: %s using \
                registration_command: %s",
                device.hostname,
                registration_command)
            time.sleep(30)


def packet_create_register_host(name, registration_command):
    manager = packet.Manager(auth_token=common.packet_rancher_auth_token)
    log.info("creating packet instance name: %s", name)
    device = manager.create_device(
        project_id=common.packet_rancher_project_id,
        hostname=name,
        plan=packet_host_machine_type,
        facility='ewr1',
        operating_system=packet_host_os_img,
        userdata=packet_host_cloud_config)

    # wait for initializing and reboot
    device = packet_wait_for_creation(manager, device)
    log.info(
        "Packet device name: %s created, registering it to cattle ...",
        device.hostname)
    packet_register_to_cattle(device, registration_command)

    return device


def get_local_pub_key():
    # ensure there is no pre-existing id_rsa and id_rsa.pub keys
    silent_remove_file("id_rsa")
    silent_remove_file("id_rsa.pub")

    args = shlex.split('ssh-keygen -t rsa -N "" -f "./id_rsa"')
    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    p.communicate()[0]
    if p.returncode != 0:
        raise Exception("Errors running ssh-keygen")
    file = open("id_rsa.pub")
    return file.read()


def gce_create_server(compute, name, gce_startup_script):
    log.info("gce create instance name: %s ...", name)
    operation = gce_create_instance(compute, name, gce_startup_script)
    common.gce_wait_for_operation(compute, operation['name'])

    return gce_get_IP(compute, name)


def packet_upload_key(public_key):
    log.info("uploading packet public key: %s", public_key)
    manager = packet.Manager(auth_token=common.packet_rancher_auth_token)

    # update pre-existing key with the same label
    ssh_keys = manager.list_ssh_keys()
    for each in ssh_keys:
        if each.label == key_label:
            each.key = public_key
            each.update()
            return

    # if it doesn't exist, then create a new one
    manager.create_ssh_key(key_label, public_key)


def main():
    # generate ssh key pairs and upload public key to packet project to allow
    # ssh into the hosts
    public_key = get_local_pub_key()

    # create GCE servers: nfs and rancher
    compute = common.initialize_gcloud()
    nfs_IP = gce_create_server(
        compute,
        common.gce_nfs_server_name,
        gce_startup_script_nfs)
    rancher_IP = gce_create_server(
        compute,
        common.gce_rancher_server_name,
        gce_startup_script_rancher)
    registration_command = cattle_get_host_registration_command(rancher_IP)
    log.info("got registration_command from cattle: %s", registration_command)

    # create packet hosts
    packet_upload_key(public_key)

    threads = []
    for name in common.packet_host_names:
        t = threading.Thread(
            target=packet_create_register_host, args=(
                name, registration_command))
        t.start()
        threads.append(t)

    # wait for all devices to get ready
    for t in threads:
        t.join()

    # set test required environment variable to a property file
    property_file_name = os.environ["PROPERTY_FILE_NAME"]

    property_file = open(
        os.path.join(
            os.path.dirname(__file__),
            property_file_name),
        'w')
    property_file.write("CATTLE_TEST_URL=http://" + rancher_IP + ":8080\n")
    property_file.write("LONGHORN_BACKUP_SERVER_IP=" + nfs_IP + "\n")
    property_file.close()


if __name__ == '__main__':
    main()
