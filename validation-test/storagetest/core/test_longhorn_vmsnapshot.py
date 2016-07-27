from common_fixtures import *  # NOQA


def test_snapshot_with_root_on_longhorn_1(super_client, client):
    port = 6091
    snapshot_count = 5
    snapshot_revert_index = 3
    env, service, con, snapshots = revert_to_snapshot(
        super_client, client,
        "root-snap5-revert3", port, snapshot_count, snapshot_revert_index,
        is_root=True)
    delete_all(client, [env])


def test_snapshot_with_root_and_data_on_longhorn_1(super_client, client):
    port = 6092
    snapshot_count = 5
    snapshot_revert_index = 3
    env, service, con, snapshots = revert_to_snapshot(
        super_client, client,
        "data-snap5-revert3", port, snapshot_count, snapshot_revert_index,
        is_root=False)
    delete_all(client, [env])


def test_snapshot_with_root_on_longhorn_2(super_client, client):
    port = 6093
    snapshot_count = 5
    snapshot_revert_index = 1
    env, service, con, snapshots = revert_to_snapshot(
        super_client, client,
        "root-snap5-revert1", port, snapshot_count, snapshot_revert_index,
        is_root=True)
    delete_all(client, [env])


def test_snapshot_with_root_and_data_on_longhorn_2(super_client, client):
    port = 6094
    snapshot_count = 5
    snapshot_revert_index = 1
    env, service, con, snapshots = revert_to_snapshot(
        super_client, client,
        "data-snap5-revert1", port, snapshot_count, snapshot_revert_index,
        is_root=False)
    delete_all(client, [env])


def test_snapshot_with_root_on_longhorn_4(super_client, client):
    port = 6095
    snapshot_count = 5
    snapshot_revert_index = 5
    env, service, vms, snapshots = revert_to_snapshot(
        super_client, client,
        "root-snap5-revert5-1", port, snapshot_count, snapshot_revert_index,
        is_root=True)
    vm_host = get_host_for_vm(client, vms[0])
    validate_writes(vm_host, port, is_root=True)
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service, snapshots,
                                             snapshot_revert_index=4,
                                             is_root=True)
    validate_writes(vm_host, port, is_root=True)
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service, snapshots,
                                             snapshot_revert_index=3,
                                             is_root=True)
    validate_writes(vm_host, port, is_root=True)
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service, snapshots,
                                             snapshot_revert_index=2,
                                             is_root=True)
    validate_writes(vm_host, port, is_root=True)
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service, snapshots,
                                             snapshot_revert_index=1,
                                             is_root=True)
    validate_writes(vm_host, port, is_root=True)
    delete_all(client, [env])


def test_snapshot_with_root_and_data_on_longhorn_4(super_client, client):
    port = 6096
    snapshot_count = 5
    snapshot_revert_index = 5
    env, service, vms, snapshots = revert_to_snapshot(
        super_client, client,
        "data-snap5-revert5-1", port, snapshot_count, snapshot_revert_index,
        is_root=False)
    vm_host = get_host_for_vm(client, vms[0])
    validate_writes(vm_host, port, is_root=False)
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service, snapshots,
                                             snapshot_revert_index=4,
                                             is_root=False)
    validate_writes(vm_host, port, is_root=False)

    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service, snapshots,
                                             snapshot_revert_index=3,
                                             is_root=False)
    validate_writes(vm_host, port, is_root=False)
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service, snapshots,
                                             snapshot_revert_index=2,
                                             is_root=False)
    validate_writes(vm_host, port, is_root=False)
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service, snapshots,
                                             snapshot_revert_index=1,
                                             is_root=False)
    validate_writes(vm_host, port, is_root=False)
    delete_all(client, [env])


def test_snapshot_with_root_on_longhorn_with_deletes_1(super_client, client):
    port = 7001
    snapshot_count = 3
    snapshot_revert_index = 3
    snapshot_delete_indexes = [2]
    vm_name = "snap-del2-revert-3"

    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client, vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=True)
    delete_all(client, [env])


def test_snapshot_with_root_on_longhorn_with_deletes_2(super_client, client):
    port = 7002
    snapshot_count = 3
    snapshot_revert_index = 1
    snapshot_delete_indexes = [2]
    vm_name = "r-snap-del2-r-1"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=True)
    delete_all(client, [env])


def test_snapshot_with_root_on_longhorn_with_deletes_3(super_client, client):
    port = 7003
    snapshot_count = 6
    snapshot_revert_index = 1
    snapshot_delete_indexes = [2, 3, 5]

    vm_name = "r-snap-del235-r-1"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=True)

    delete_all(client, [env])


def test_snapshot_with_root_on_longhorn_with_deletes_4(super_client, client):
    port = 7004
    snapshot_count = 6
    snapshot_revert_index = 4
    snapshot_delete_indexes = [2, 3, 5]

    vm_name = "r-snap-del235-r-4"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=True)

    delete_all(client, [env])


def test_snapshot_with_root_on_longhorn_with_deletes_5(super_client, client):
    port = 7005
    snapshot_count = 3
    snapshot_revert_index = 2
    snapshot_delete_indexes = [1]

    vm_name = "r-snap-del1-revert-2"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=True)

    delete_all(client, [env])


def test_snapshot_with_data_on_longhorn_with_deletes_1(super_client, client):
    port = 8001
    snapshot_count = 3
    snapshot_revert_index = 3
    snapshot_delete_indexes = [2]
    vm_name = "d-snap-del2-revert-3"

    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client, vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=False)
    delete_all(client, [env])


def test_snapshot_with_data_on_longhorn_with_deletes_2(super_client, client):
    port = 8002
    snapshot_count = 3
    snapshot_revert_index = 1
    snapshot_delete_indexes = [2]
    vm_name = "d-snap-del2-revert-1"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=False)
    delete_all(client, [env])


def test_snapshot_with_data_on_longhorn_with_deletes_3(super_client, client):
    port = 8003
    snapshot_count = 6
    snapshot_revert_index = 1
    snapshot_delete_indexes = [2, 3, 5]

    vm_name = "d-snap-del235-r-1"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=False)

    delete_all(client, [env])


def test_snapshot_with_data_on_longhorn_with_deletes_4(super_client, client):
    port = 8004
    snapshot_count = 6
    snapshot_revert_index = 4
    snapshot_delete_indexes = [2, 3, 5]

    vm_name = "d-snap-del235-r-4"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=False)

    delete_all(client, [env])


def test_snapshot_with_data_on_longhorn_with_deletes_5(super_client, client):
    port = 8005
    snapshot_count = 6
    snapshot_revert_index = 1
    snapshot_delete_indexes = [2, 3, 5]

    vm_name = "d-snap-del235-r-1"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=False)

    delete_all(client, [env])


def test_snapshot_with_data_on_longhorn_with_deletes_6(super_client, client):
    port = 7005
    snapshot_count = 3
    snapshot_revert_index = 2
    snapshot_delete_indexes = [1]

    vm_name = "d-snap-del1-revert-2"
    env, service, vms = revert_to_snapshot_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_revert_index,
        is_root=False)

    delete_all(client, [env])


def test_backup_with_root_on_longhorn_1(super_client, client):
    port = 7010

    snapshot_count = 5
    snapshot_revert_index = 4
    env, service, vms, snapshots, backup = restore_from_backup(
        super_client, client,
        "root-snap5-backup4", port, snapshot_count, snapshot_revert_index,
        is_root=True)

    delete_all(client, [env])


def test_backup_with_data_on_longhorn_1(super_client, client):
    port = 7011

    snapshot_count = 5
    snapshot_revert_index = 4
    env, service, vms, snapshots, backup = restore_from_backup(
        super_client, client,
        "data-snap5-backup4", port, snapshot_count, snapshot_revert_index,
        is_root=False)

    delete_all(client, [env])


def test_backup_with_root_on_longhorn_2(super_client, client):
    port = 7012

    snapshot_count = 5
    snapshot_revert_index = 1
    env, service, vms, snapshots, backup = restore_from_backup(
        super_client, client,
        "root-snap5-backup1", port, snapshot_count, snapshot_revert_index,
        is_root=True)

    delete_all(client, [env])


def test_backup_with_data_on_longhorn_2(super_client, client):
    port = 7013

    snapshot_count = 5
    snapshot_revert_index = 1
    env, service, vms, snapshots, backup = restore_from_backup(
        super_client, client,
        "data-snap5-backup1", port, snapshot_count, snapshot_revert_index,
        is_root=False)

    delete_all(client, [env])


def test_backup_with_root_on_longhorn_with_deletes_1(super_client, client):
    port = 7021
    snapshot_count = 3
    snapshot_backup_index = 3
    snapshot_delete_indexes = [2]
    vm_name = "r-snap-del2-revert-3"

    env, service, vms = restore_from_backup_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_backup_index,
        is_root=True)

    delete_all(client, [env])


def test_backup_with_root_on_longhorn_with_deletes_2(super_client, client):
    port = 7022
    snapshot_count = 3
    snapshot_revert_index = 1
    snapshot_backup_indexes = [2]
    vm_name = "r-snap-del2-revert-1"
    env, service, vms = restore_from_backup_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_backup_indexes,
        snapshot_revert_index,
        is_root=True)
    delete_all(client, [env])


def test_backup_with_data_on_longhorn_with_deletes_1(super_client, client):
    port = 7021
    snapshot_count = 3
    snapshot_backup_index = 3
    snapshot_delete_indexes = [2]
    vm_name = "r-snap-del2-revert-3"

    env, service, vms = restore_from_backup_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_delete_indexes,
        snapshot_backup_index,
        is_root=False)

    delete_all(client, [env])


def test_backup_with_data_on_longhorn_with_deletes_2(super_client, client):
    port = 7022
    snapshot_count = 3
    snapshot_revert_index = 1
    snapshot_backup_indexes = [2]
    vm_name = "r-snap-del2-revert-1"
    env, service, vms = restore_from_backup_after_snapshot_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_backup_indexes,
        snapshot_revert_index,
        is_root=False)
    delete_all(client, [env])


def test_root_restore_from_backup_after_backup_deletes(super_client, client):
    port = 7023
    vm_name = "r-backup2-del1-r-1"
    snapshot_count = 3
    snapshot_backup_index = 2
    snapshot_count_2 = 2
    snapshot_backup_index_2 = 1

    env, service, vms = restore_from_backup_after_backup_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_backup_index,
        snapshot_count_2, snapshot_backup_index_2,
        is_root=True)
    delete_all(client, [env])


def test_data_restore_from_backup_after_backup_deletes(super_client, client):
    port = 7025
    vm_name = "d-backup2-del1-r-1"
    snapshot_count = 4
    snapshot_backup_index = 3
    snapshot_count_2 = 3
    snapshot_backup_index_2 = 2

    env, service, vms = restore_from_backup_after_backup_deletes(
        super_client, client,
        vm_name, port, snapshot_count,
        snapshot_backup_index,
        snapshot_count_2, snapshot_backup_index_2,
        is_root=False)
    delete_all(client, [env])


def revert_to_snapshot(super_client, client, vm_name, port, snapshot_count,
                       snapshot_revert_index, is_root=True):
    # Create service with root disk using longhorn driver
    env, service, vms = createVMService(
        super_client, client, vm_name,
        str(port), root_disk=True, data_disk=True)

    # Take 5 snapshots of root disk
    snapshots = take_snapshots_for_vm_service(super_client, client, port,
                                              service,
                                              is_root=is_root,
                                              snapshot_count=snapshot_count)
    # Restore Root/Data volume to snapshot
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service,
                                             snapshots, snapshot_revert_index,
                                             is_root=is_root)
    return env, service, vms, snapshots


def restore_from_backup(super_client, client, vm_name, port, snapshot_count,
                        snapshot_backup_index, is_root=True):
    # Create service with root disk using longhorn driver
    env, service, vms = createVMService(
        super_client, client, vm_name,
        str(port), root_disk=True, data_disk=True)

    # Take snapshots of root disk
    snapshots = take_snapshots_for_vm_service(super_client, client, port,
                                              service,
                                              is_root=is_root,
                                              snapshot_count=snapshot_count)
    # Restore Root/Data volume from Backup
    backup = restore_volume_from_backup_for_vm_service(
        super_client, client, port,
        service,
        snapshots, snapshot_backup_index,
        is_root=is_root)
    return env, service, vms, snapshots, backup


def revert_to_snapshot_after_snapshot_deletes(super_client, client,
                                              vm_name, port, snapshot_count,
                                              snapshot_delete_indexes,
                                              snapshot_revert_index,
                                              is_root=True):
    # Create service with root disk using longhorn driver
    env, service, vms = createVMService(
        super_client, client, vm_name,
        str(port), root_disk=True, data_disk=True)

    # Take snapshots of root disk
    snapshots = take_snapshots_for_vm_service(super_client, client, port,
                                              service,
                                              is_root=is_root,
                                              snapshot_count=snapshot_count)
    # Delete snapshots
    for snapshot_delete_index in snapshot_delete_indexes:
        snapshot_delete = snapshots[snapshot_delete_index - 1]["snapshot"]
        snapshot_delete = client.wait_success(client.delete(snapshot_delete))
        assert snapshot_delete.state == 'removed'

    # Restore Root/Data volume to snapshot
    revert_volume_to_snapshot_for_vm_service(super_client, client, port,
                                             service,
                                             snapshots, snapshot_revert_index,
                                             is_root=is_root)
    return env, service, vms


def restore_from_backup_after_snapshot_deletes(super_client, client,
                                               vm_name, port, snapshot_count,
                                               snapshot_delete_indexes,
                                               snapshot_backup_index,
                                               is_root=True):
    # Create service with root disk using longhorn driver
    env, service, vms = createVMService(
        super_client, client, vm_name,
        str(port), root_disk=True, data_disk=True)

    # Take snapshots of root disk
    snapshots = take_snapshots_for_vm_service(super_client, client, port,
                                              service,
                                              is_root=is_root,
                                              snapshot_count=snapshot_count)
    # Delete snapshots
    for snapshot_delete_index in snapshot_delete_indexes:
        snapshot_delete = snapshots[snapshot_delete_index - 1]["snapshot"]
        snapshot_delete = client.wait_success(client.delete(snapshot_delete))
        assert snapshot_delete.state == 'removed'

    # Restore Root/Data volume from Backup
    restore_volume_from_backup_for_vm_service(super_client, client, port,
                                              service,
                                              snapshots, snapshot_backup_index,
                                              is_root=is_root)
    return env, service, vms


def restore_from_backup_after_backup_deletes(super_client, client,
                                             vm_name, port, snapshot_count,
                                             snapshot_backup_index,
                                             snapshot_count_2,
                                             snapshot_backup_index_2,
                                             is_root=True):
    env, service, vms, snapshots1, backup1 = restore_from_backup(
        super_client, client, vm_name, port, snapshot_count,
        snapshot_backup_index, is_root=is_root)

    # Take snapshots of root/data disk
    snapshots2 = take_snapshots_for_vm_service(super_client, client, port,
                                               service,
                                               is_root=is_root,
                                               snapshot_count=snapshot_count_2)
    # Create a backup
    snapshot_backup = snapshots2[snapshot_backup_index_2 - 1]["snapshot"]
    backup2 = \
        client.wait_success(snapshot_backup.backup(backupTargetId="1bt1"),
                            timeout=120)
    assert backup2.state == "created"

    # Take snapshots of root/data disk
    snapshot_count_3 = 2
    snapshots3 = take_snapshots_for_vm_service(super_client, client, port,
                                               service,
                                               is_root=is_root,
                                               snapshot_count=snapshot_count_3)

    # Delete the first backup
    backup1 = client.wait_success(client.delete(backup1))
    assert backup1.state == "removed"

    # Restore volume to backup2
    restore_volume_from_backup(super_client, client, port,
                               service, snapshots2,
                               snapshot_backup_index_2,
                               backup2,
                               is_root=is_root)

    # Check for existence files that was created as part of first backup
    for vm in vms:
        vm_host = get_host_for_vm(client, vm)
        dir = ROOT_DIR
        if not is_root:
            mount_data_dir(vm_host, port)
            dir = DATA_DIR
        for i in range(0, snapshot_backup_index):
            file = snapshots1[i]["filename"]
            content = snapshots1[i]["content"]
            assert check_if_file_exists(vm_host, port, dir + "/" + file)
            assert read_data(vm_host, port, dir, file) == content
        if snapshot_backup_index < len(snapshots1):
            for i in range(snapshot_backup_index, len(snapshots1)):
                file = snapshots1[i]["filename"]
                assert not check_if_file_exists(
                    vm_host, port, dir + "/" + file)

        # Check for non existence of files that was created after the
        # second backup
        for snapshot in snapshots3:
            file = snapshot["filename"]
            assert not check_if_file_exists(vm_host, port, dir + "/" + file)
    return env, service, vms


def test_createVM_with_root_and_data_on_longhorn_with_iops(
        super_client, client):
    port = 9993
    readiops = 100
    writeiops = 200

    env, service, con = createVMService(
        super_client, client, "root-data-iop",
        str(port), root_disk=True, data_disk=True,
        readiops=readiops, writeiops=writeiops)

    vms = get_service_vm_list(super_client, service)
    assert len(vms) == 1
    for vm in vms:
        assert vm.state == "running"
        vm_host = get_host_for_vm(client, vm)
        validate_writes(vm_host, port, is_root=True)
        validate_writes(vm_host, port, is_root=False)

    system_envname = get_system_env_name_for_vm_service(vms[0], root_disk=True)
    replica_containers = get_service_containers_with_name(
        super_client, service, system_envname + "_" + REPLICA)
    assert len(replica_containers) == 2
    for con in replica_containers:
        docker_client = get_docker_client(con.hosts[0])
        inspect = docker_client.inspect_container(con.externalId)
        print inspect
        assert \
            inspect
        ["HostConfig"]["BlkioDeviceReadIOps"][0]["Rate"] == readiops
        assert \
            inspect
        ["HostConfig"]["BlkioDeviceWriteIOps"][0]["Rate"] == writeiops

    delete_all(client, [env])


def test_multiple_service_deployment(client):
    root_disk = True
    data_disk = True
    scale = 1
    health_check_on = True
    readiops = 0
    writeiops = 0
    memory = 512
    cpu = 1

    env = create_env(client)
    root_lh_disk = {"name": ROOT_DISK, "root": True,
                    "size": "10g", "driver": VOLUME_DRIVER}
    data_lh_disk = {"name": DATA_DISK, "root": False,
                    "size": "1g", "driver": VOLUME_DRIVER}

    if readiops != 0:
        root_lh_disk["readIops"] = readiops
        data_lh_disk["readIops"] = readiops

    if writeiops != 0:
        data_lh_disk["writeIops"] = writeiops
        root_lh_disk["writeIops"] = writeiops

    longhorn_disk = []
    if root_disk:
        longhorn_disk.append(root_lh_disk)
    if data_disk:
        longhorn_disk.append(data_lh_disk)

    health_check = {"name": "check1", "responseTimeout": 2000,
                    "interval": 2000, "healthyThreshold": 2,
                    "unhealthyThreshold": 3,
                    "requestLine": "", "port": 22}

    launch_config = {"kind": "virtualMachine",
                     "disks": longhorn_disk,
                     "imageUuid": VM_IMAGE_UUID,
                     "memoryMb": memory,
                     "vcpu": cpu,
                     "networkMode": "managed",
                     }
    if health_check_on is not None:
        launch_config["healthCheck"] = health_check
    services = []
    for i in range(0, 10):
        service = create_svc(client, env, launch_config, scale,
                             service_name="test")
        service = client.wait_success(service)
        assert service.state == "inactive"
        service = service.activate()
        services.append(service)
        time.sleep(5)
