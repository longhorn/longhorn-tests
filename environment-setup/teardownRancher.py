#!/usr/bin/env python

import time
import logging
import common
import packet


log = logging.getLogger("teardown-rancher")


def gce_delete_servers(compute, servers):
    # get all instance names from GCE
    result = compute.instances().list(
        project=common.gce_rancher_project_name,
        zone=common.gce_rancher_project_zone).execute()
    for instance in result['items']:
        if instance['name'] not in servers:
            continue
        retries = 5
        while retries >= 0:
            retries -= 1
            try:
                operation = gce_delete_instance(compute, instance['name'])
                common.gce_wait_for_operation(compute, operation['name'])
                break
            except:
                time.sleep(30)
                continue


def gce_delete_instance(compute, name):
    return compute.instances().delete(
        project=common.gce_rancher_project_name,
        zone=common.gce_rancher_project_zone,
        instance=name).execute()


def packet_remove_devices(device_names):
    manager = packet.Manager(auth_token=common.packet_rancher_auth_token)
    devices = manager.list_devices(project_id=common.packet_rancher_project_id)
    for each in devices:
        if each.hostname not in device_names:
            continue
        retries = 5
        while retries >= 0:
            retries -= 1
            try:
                each.delete()
                break
            except:
                time.sleep(30)
                continue


def main():
    compute = common.initialize_gcloud()

    # destroy machines
    packet_remove_devices(common.packet_host_names)
    gce_delete_servers(compute,
                       [common.gce_rancher_server_name,
                        common.gce_nfs_server_name])


if __name__ == '__main__':
    main()
