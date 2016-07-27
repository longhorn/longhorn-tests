from common_fixtures import *  # NOQA
import datetime


def test_createVM_with_root_on_longhorn(client):
    port = 8880
    # Create VM with ROOT disk using longhorn driver
    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=False)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"

    # Validate reads/writes to ROOT disk
    validate_writes(vm_host, port, is_root=True)
    delete_all(client, [vm])


def test_createVM_with_root_on_longhorn_stop_start(client):
    port = 8881
    # Create VM with ROOT disk using longhorn driver
    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=False)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"

    # Validate that we are able to read/write to ROOT disk
    file_name, content = validate_writes(
        vm_host, port, is_root=True)

    # Stop and start VM
    exec_ssh_cmd(vm_host, port, "sync")
    vm = client.wait_success(vm.stop())
    assert vm.state == "stopped"
    vm = client.wait_success(vm.start())
    assert vm.state == "running"
    time.sleep(TIME_TO_BOOT_IN_SEC)

    # Validate access to existing file in ROOT disk
    assert read_data(vm_host, port, ROOT_DIR, file_name) == content
    # Validate reads/writes to ROOT disk
    validate_writes(vm_host, port, is_root=True)

    delete_all(client, [vm])


def test_createVM_with_root_on_longhorn_restart(client):
    port = 8882
    # Create VM with ROOT disk using longhorn driver
    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=False)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"
    # Validate that we are able to read/write to ROOT disk
    file_name, content = validate_writes(
        vm_host, port, is_root=True)

    # Restart VM
    exec_ssh_cmd(vm_host, port, "sync")
    vm = client.wait_success(vm.restart())
    assert vm.state == "running"
    time.sleep(TIME_TO_BOOT_IN_SEC)

    # Validate access to existing file in ROOT disk
    assert read_data(vm_host, port, ROOT_DIR, file_name) == content
    # Validate reads/writes to ROOT disk
    validate_writes(vm_host, port, is_root=True)

    delete_all(client, [vm])


def test_createVM_with_data_on_longhorn(client):
    port = 8883
    # Create VM with DATA disk using longhorn driver
    vm = createVM(
        client, str(port), host=None, root_disk=False, data_disk=True)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"

    # Validate reads/writes to DATA disk
    validate_writes(vm_host, port, is_root=False)
    delete_all(client, [vm])


def test_createVM_with_data_on_longhorn_stop_start(client):
    port = 8884
    vm = createVM(
        client, str(port), host=None, root_disk=False, data_disk=True)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"
    file_name, content = validate_writes(
        vm_host, port, is_root=False)

    exec_ssh_cmd(vm_host, port, "sync")
    vm = client.wait_success(vm.stop())
    assert vm.state == "stopped"
    vm = client.wait_success(vm.start())
    assert vm.state == "running"
    time.sleep(TIME_TO_BOOT_IN_SEC)

    mount_data_dir_check_file(vm_host, port, file_name, content)

    validate_writes(vm_host, port, is_root=False)

    delete_all(client, [vm])


def test_createVM_with_data_on_longhorn_restart(client):
    port = 8885
    vm = createVM(
        client, str(port), host=None, root_disk=False, data_disk=True)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"
    time.sleep(TIME_TO_BOOT_IN_SEC)

    file_name, content = validate_writes(
        vm_host, port, is_root=False)

    exec_ssh_cmd(vm_host, port, "sync")
    vm = client.wait_success(vm.restart())
    assert vm.state == "running"
    time.sleep(TIME_TO_BOOT_IN_SEC)

    mount_data_dir_check_file(vm_host, port, file_name, content)

    validate_writes(vm_host, port, is_root=False)
    delete_all(client, [vm])


def test_createVM_with_root_and_data_on_longhorn(client):
    port = 8886
    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=True)
    assert vm.state == "running"
    vm_host = get_host_for_vm(client, vm)
    validate_writes(vm_host, port, is_root=True)
    delete_all(client, [vm])


def test_createVM_with_root_and_data_on_longhorn_stop_start(client):
    port = 8887
    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=True)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"
    file_name_r, content_r = validate_writes(
        vm_host, port, is_root=True)
    file_name_d, content_d = validate_writes(
        vm_host, port, is_root=False)

    exec_ssh_cmd(vm_host, port, "sync")
    vm = client.wait_success(vm.stop())
    assert vm.state == "stopped"
    vm = client.wait_success(vm.start())
    assert vm.state == "running"
    time.sleep(TIME_TO_BOOT_IN_SEC)

    assert read_data(vm_host, port, ROOT_DIR, file_name_r) == content_r
    mount_data_dir_check_file(vm_host, port, file_name_d, content_d)

    validate_writes(vm_host, port, is_root=True)

    delete_all(client, [vm])


def test_createVM_with_root_and_data_on_longhorn_restart(client):
    port = 8888
    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=True)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"
    file_name_r, content_r = validate_writes(
        vm_host, port, is_root=True)
    file_name_d, content_d = validate_writes(
        vm_host, port, is_root=False)

    exec_ssh_cmd(vm_host, port, "sync")
    vm = client.wait_success(vm.restart())
    assert vm.state == "running"
    time.sleep(TIME_TO_BOOT_IN_SEC)

    assert read_data(vm_host, port, ROOT_DIR, file_name_r) == content_r
    mount_data_dir_check_file(vm_host, port, file_name_d, content_d)
    validate_writes(vm_host, port, is_root=False)
    validate_writes(vm_host, port, is_root=True)

    delete_all(client, [vm])


def test_createVM_rootdisk_replica_delete(super_client, client):
    port = 9090
    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=False)
    vm_host = get_host_for_vm(client, vm)
    env_name = get_system_env_name(vm)

    env, service = get_env_service_by_name(client, env_name, REPLICA)
    assert service.scale == 2

    con_env, con_service = \
        get_env_service_by_name(client, env_name, CONTROLLER)
    assert con_service.scale == 1
    controller = get_service_containers_with_name(
            super_client, con_service, env_name+"_"+CONTROLLER)
    assert len(controller) == 1

    for i in range(0, 2):
        replica_containers = get_service_containers_with_name(
            super_client, service, env_name+"_"+REPLICA)
        assert len(replica_containers) == service.scale
        for con in replica_containers:
            # Delete one of the replicas of the container of the service
            delete_replica_and_wait_for_service_reconcile(
                super_client, client, service, [con])
            validate_writes(vm_host, port, is_root=True)
            new_replica_containers = get_service_containers_with_name(
                super_client, service, env_name+"_"+REPLICA)
            assert len(new_replica_containers) == service.scale
            # wait for replica to get to RW mode
            wait_for_replica_rebuild(controller[0], new_replica_containers)
    delete_all(client, [vm])


def test_createVM_datadisk_replica_delete(super_client, client):
    port = 9080

    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=True)
    vm_host = get_host_for_vm(client, vm)
    env_name = get_system_env_name(vm, False)

    env, service = get_env_service_by_name(client, env_name, REPLICA)
    assert service.scale == 2

    con_env, con_service = \
        get_env_service_by_name(client, env_name, CONTROLLER)
    assert con_service.scale == 1
    controller = get_service_containers_with_name(
        super_client, con_service, env_name+"_"+CONTROLLER)
    assert len(controller) == 1

    for i in range(0, 2):
        replica_containers = get_service_containers_with_name(
            super_client, service, env_name+"_"+REPLICA)
        assert len(replica_containers) == service.scale
        for con in replica_containers:
            # Delete one of the replicas of the container of the service
            delete_replica_and_wait_for_service_reconcile(
                super_client, client, service, [con])
            validate_writes(vm_host, port, is_root=False)
            new_replica_containers = get_service_containers_with_name(
                super_client, service, env_name+"_"+REPLICA)
            assert len(new_replica_containers) == service.scale
            # wait for replica to get to RW mode
            wait_for_replica_rebuild(controller[0], new_replica_containers)
    delete_all(client, [vm])


def test_startVM_with_existing_data_on_longhorn(client):
    port = 9050
    vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=True)
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"

    file_name, content = validate_writes(
        vm_host, port, is_root=True)

    file_name, content = validate_writes(
        vm_host, port, is_root=False)

    exec_ssh_cmd(vm_host, port, "sync")
    vm = client.wait_success(vm.stop())
    assert vm.state == "stopped"

    # Create new VM with existing data volume
    data_vol = get_volume_name(vm, root_disk=False)
    new_vm = createVM(
        client, str(port), host=None, root_disk=True, data_disk=True,
        data_vol=data_vol)
    assert new_vm.state == "running"
    host = get_host_for_vm(client, new_vm)
    make_dir(host, port, DATA_DIR, False)
    mount_data_dir_check_file(host, port, file_name, content)

    delete_all(client, [vm, new_vm])


def test_createVM_with_data_using_dd(client):
    port = 4545
    # Create VM with DATA disk using longhorn driver
    vm = createVM(
        client, str(port), host=None, root_disk=True,
        data_disk=True, data_disk_size="10g")
    vm_host = get_host_for_vm(client, vm)
    assert vm.state == "running"
    # Validate reads/writes to DATA disk
    writes_with_dd(vm_host, port, is_root=False,
                   in_bg=False, gb_count=7)
    delete_all(client, [vm])


def test_createVM_with_data_using_dd_in_bg(super_client, client,
                                           socat_containers):
    port = 4546

    # Create VM with DATA disk using longhorn driver
    vm = createVM(
        client, str(port), host=None, root_disk=True,
        data_disk=True, data_disk_size="10g")
    assert vm.state == "running"
    vm_host = get_host_for_vm(client, vm)

    for i in range(0, 5):
        # Writes to DATA disk
        print datetime.datetime.now().time()
        writes_with_dd(vm_host, port, is_root=False,
                       in_bg=True, gb_count=7)
        print datetime.datetime.now().time()
        time.sleep(60)

        # When write is still in progress , kill replica process
        env_name = get_system_env_name(vm, root_disk=False)
        env, service = get_env_service_by_name(client, env_name, REPLICA)
        assert service.scale == 2
        replica_containers = get_service_containers_with_name(
                super_client, service, env_name+"_"+REPLICA)
        assert len(replica_containers) == service.scale

        kill_system_process_and_wait_for_service_reconcile(
            super_client, client, service, replica_containers[0])

        print datetime.datetime.now().time()
        # Issue sync on data file
        exec_ssh_cmd(vm_host, port, "cd /datadir1;sync;")
        print datetime.datetime.now().time()
        # Validate Writes
        validate_writes(vm_host, port, is_root=False)
        exec_ssh_cmd(vm_host, port, "cd /datadir1;rm f_*;sync;")
        print datetime.datetime.now().time()

        env, service = get_env_service_by_name(client, env_name, REPLICA)
        assert service.scale == 2
        replica_containers = get_service_containers_with_name(
                super_client, service, env_name+"_"+REPLICA)
        assert len(replica_containers) == service.scale

        env, service = get_env_service_by_name(client, env_name, CONTROLLER)
        assert service.scale == 1
        controller_containers = get_service_containers_with_name(
                super_client, service, env_name+"_"+CONTROLLER)
        assert len(controller_containers) == service.scale

        wait_for_replica_rebuild(controller_containers[0], replica_containers)

    delete_all(client, [vm])


def createVM(client, port, host=None, root_disk=True, data_disk=True,
             data_vol=None,  health_check_on=True, data_disk_size="1g"):

    random_name = random_str()
    vm_name = random_name.replace("-", "")
    root_lh_disk = {"name": ROOT_DISK, "root": True,
                    "size": "10g", "driver": VOLUME_DRIVER}
    if data_vol is None:
        data_volume = DATA_DISK
    else:
        data_volume = data_vol
    data_lh_disk = {"name": data_volume, "root": False,
                    "size": data_disk_size, "driver": VOLUME_DRIVER}
    longhorn_disk = []
    if root_disk:
        longhorn_disk.append(root_lh_disk)
    if data_disk:
        longhorn_disk.append(data_lh_disk)
    vm_args = {"disks": longhorn_disk,
               "imageUuid": VM_IMAGE_UUID,
               "memoryMb": 512,
               "vcpu": 1,
               "name": vm_name,
               "networkMode": "managed",
               "ports": [port+":22/tcp"]}
    if host is not None:
        vm_args["requestedHostId"] = host.id

    health_check = {"name": "check1", "responseTimeout": 2000,
                    "interval": 2000, "healthyThreshold": 2,
                    "unhealthyThreshold": 3,
                    "requestLine": "", "port": 22}
    if health_check_on is not None:
        vm_args["healthCheck"] = health_check

    virtual_machine = client.create_virtual_machine(vm_args)
    virtual_machine = wait_for_condition(
        client, virtual_machine,
        lambda x: x.state == "running",
        lambda x: 'State is: ' + x.state,
        600)

    if root_disk:
        root_system_env_name = get_system_env_name(virtual_machine)
        print root_system_env_name

        envs = client.list_environment(name=root_system_env_name)
        assert len(envs) == 1
        root_vol_sys_env = envs[0]
        services = root_vol_sys_env.services()
        assert len(services) == 2

        for service in root_vol_sys_env.services():
            assert service.state == "active"
            if service.name == REPLICA:
                assert service.scale == 2
            if service.name == CONTROLLER:
                assert service.scale == 1

    if data_disk and data_vol is None:
        data_system_env_name = get_system_env_name(virtual_machine, False)
        envs = client.list_environment(name=data_system_env_name)
        assert len(envs) == 1
        data_vol_sys_env = envs[0]
        services = data_vol_sys_env.services()
        assert len(services) == 2

        for service in data_vol_sys_env.services():
            assert service.state == "active"
            if service.name == REPLICA:
                assert service.scale == 2
            if service.name == CONTROLLER:
                assert service.scale == 1

    # Wait for VM to become healthy
    assert virtual_machine.state == "running"
    wait_for_condition(
        client, virtual_machine,
        lambda x: x.healthState == 'healthy',
        lambda x: 'State is: ' + x.healthState,
        120)
    # time.sleep(TIME_TO_BOOT_IN_SEC)
    if root_disk:
        if host is None:
            host = get_host_for_vm(client, virtual_machine)
        make_dir(host, int(port), ROOT_DIR, False)
    if data_disk and data_vol is None:
        if host is None:
            host = get_host_for_vm(client, virtual_machine)
        make_dir(host, int(port), DATA_DIR, True)

    return virtual_machine


def wait_for_replica_rebuild(controller, replicas, timeout=60):
    start = time.time()
    rebuild_complete = False
    while not rebuild_complete:
        if time.time() - start > timeout:
            raise \
                Exception('Timedout waiting for replica rebuild to complete')
        replica_stat_text = get_replica_stats(controller)
        print replica_stat_text
        replica_ip = []
        for replica in replicas:
            replica_ip.append(
                "tcp://" + replica.primaryIpAddress + ":9502")
        replica_stat_resp = replica_stat_text.split()

        if (replica_ip[0] in replica_stat_resp and
                replica_ip[1] in replica_stat_resp):
            replica1_idx = replica_stat_resp.index(replica_ip[0])
            replica2_idx = replica_stat_resp.index(replica_ip[1])
            if (replica_stat_resp[replica1_idx+1] == "RW" and
                    replica_stat_resp[replica2_idx+1] == "RW"):
                    rebuild_complete = True
                    time.sleep(10)
