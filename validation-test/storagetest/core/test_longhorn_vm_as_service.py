from common_fixtures import *  # NOQA


def test_createVMService_with_root_on_longhorn(super_client, client):
    port = 6080
    env, service, con = createVMService(
        super_client, client, "root",
        str(port), root_disk=True, data_disk=False)
    vms = get_service_vm_list(super_client, service)
    assert len(vms) == 1
    for vm in vms:
        vm_host = get_host_for_vm(client, vm)
        assert vm.state == "running"
        validate_writes(vm_host, port, is_root=True)
    delete_all(client, [env])


def test_createVM_with_root_on_longhorn_stop(super_client, client):
    port = 6081
    # Create VM with ROOT disk using longhorn driver
    env, service, con = createVMService(
        super_client, client, "root-stop",
        str(port), root_disk=True, data_disk=False)

    vms = get_service_vm_list(super_client, service)
    assert len(vms) == 1
    for vm in vms:
        vm_host = get_host_for_vm(client, vm)
        assert vm.state == "running"
        # Validate that we are able to read/write to ROOT disk
        file_name, content = validate_writes(
            vm_host, port, is_root=True)

        # Stop VM
        exec_ssh_cmd(vm_host, port, "sync")
        vm = client.wait_success(vm.stop())

        # Wait for VM to start
        wait_for_vm_scale_to_adjust(super_client, service)
        vm = client.reload(vm)
        assert vm.state == "running"

        time.sleep(TIME_TO_BOOT_IN_SEC)

        # Validate access to existing file in ROOT disk
        assert read_data(vm_host, port, ROOT_DIR, file_name) == content
        # Validate reads/writes to ROOT disk
        validate_writes(vm_host, port, is_root=True)

    delete_all(client, [env])


def test_createVM_with_root_on_longhorn_delete(super_client, client):
    port = 6082
    # Create VM with ROOT disk using longhorn driver
    env, service, con = createVMService(
        super_client, client, "root-delete",
        str(port), root_disk=True, data_disk=False)
    vms = get_service_vm_list(super_client, service)
    assert len(vms) == 1

    for vm in vms:
        vm_host = get_host_for_vm(client, vm)
        assert vm.state == "running"

        # Validate that we are able to read/write to ROOT disk
        file_name, content = validate_writes(
            vm_host, port, is_root=True)

        # Delete VM
        exec_ssh_cmd(vm_host, port, "sync")
        vm = client.wait_success(client.delete(vm))
        assert vm.state == 'removed'

        # Wait for VM to be recreated
        wait_for_vm_scale_to_adjust(super_client, service)
        vms = client.list_virtual_machine(
            name=vm.name,
            include="hosts",
            removed_null=True)
        assert len(vms) == 1
        vm = vms[0]
        vm_host = vms[0].hosts[0]
        time.sleep(TIME_TO_BOOT_IN_SEC)

        # Validate access to existing file in ROOT disk
        assert read_data(vm_host, port, ROOT_DIR, file_name) == content
        # Validate reads/writes to ROOT disk
        validate_writes(vm_host, port, is_root=True)

    delete_all(client, [env])


def test_createVM_with_root_and_data_on_longhorn(super_client, client):
    port = 6083
    env, service, con = createVMService(
        super_client, client, "root-data",
        str(port), root_disk=True, data_disk=True)

    vms = get_service_vm_list(super_client, service)
    assert len(vms) == 1
    for vm in vms:
        assert vm.state == "running"
        vm_host = get_host_for_vm(client, vm)
        validate_writes(vm_host, port, is_root=True)
        validate_writes(vm_host, port, is_root=False)
    delete_all(client, [env])


def test_createVM_with_root_and_data_on_longhorn_stop_start(
        super_client, client):
    port = 6084
    env, service, con = createVMService(
        super_client, client, "root-data-stop",
        str(port), root_disk=True, data_disk=True)
    vms = get_service_vm_list(super_client, service)
    assert len(vms) == 1
    for vm in vms:
        vm_host = get_host_for_vm(client, vm)
        assert vm.state == "running"
        # Validate that we are able to read/write to ROOT disk
        file_name_r, content_r = validate_writes(
            vm_host, port, is_root=True)
        file_name_d, content_d = validate_writes(
            vm_host, port, is_root=False)
        # Stop VM
        exec_ssh_cmd(vm_host, port, "sync")
        vm = client.wait_success(vm.stop())

        # Wait for VM to start
        wait_for_vm_scale_to_adjust(super_client, service)
        vm = client.reload(vm)
        assert vm.state == "running"

        time.sleep(TIME_TO_BOOT_IN_SEC)

        # Validate access to existing file in ROOT and DATA disk
        assert read_data(vm_host, port, ROOT_DIR, file_name_r) == content_r
        mount_data_dir_check_file(vm_host, port, file_name_d, content_d)

        # Validate writes to ROOT disk
        validate_writes(vm_host, port, is_root=True)
        validate_writes(vm_host, port, is_root=False)

    delete_all(client, [env])


def test_createVM_with_root_and_data_on_longhorn_delete(super_client, client):
    port = 6085
    env, service, con = createVMService(
        super_client, client, "root-data-delete",
        str(port), root_disk=True, data_disk=True)
    vms = get_service_vm_list(super_client, service)
    assert len(vms) == 1
    for vm in vms:
        vm_host = get_host_for_vm(client, vm)
        assert vm.state == "running"

        file_name_r, content_r = validate_writes(
            vm_host, port, is_root=True)
        file_name_d, content_d = validate_writes(
            vm_host, port, is_root=False)

        exec_ssh_cmd(vm_host, port, "sync")

        # Delete VM
        exec_ssh_cmd(vm_host, port, "sync")
        vm = client.wait_success(client.delete(vm))
        assert vm.state == 'removed'

        # Wait for VM to be recreated
        wait_for_vm_scale_to_adjust(super_client, service)
        vms = client.list_virtual_machine(
            name=vm.name,
            include="hosts",
            removed_null=True)
        assert len(vms) == 1
        vm = vms[0]
        vm_host = vms[0].hosts[0]
        time.sleep(TIME_TO_BOOT_IN_SEC)

        assert read_data(vm_host, port, ROOT_DIR, file_name_r) == content_r
        make_dir(vm_host, port, DATA_DIR, False)
        mount_data_dir_check_file(vm_host, port, file_name_d, content_d)

        validate_writes(vm_host, port, is_root=True)
        validate_writes(vm_host, port, is_root=False)
    delete_all(client, [env])


def test_createVM_with_root_and_data_on_longhorn_ha(super_client, client):
    port = 6086
    env, service, con = createVMService(
        super_client, client, "ha",
        str(port), root_disk=True, data_disk=True)
    vms = get_service_vm_list(super_client, service)
    assert len(vms) == 1
    for vm in vms:
        vm_host = get_host_for_vm(client, vm)
        assert vm.state == "running"

        file_name_r, content_r = validate_writes(
            vm_host, port, is_root=True)
        file_name_d, content_d = validate_writes(vm_host, port, is_root=False)
        exec_ssh_cmd(vm_host, port, "sync")

        # Deactivate Host
        vm_host = client.wait_success(vm_host.deactivate())
        assert vm_host.state == 'inactive'

        # Delete VM
        exec_ssh_cmd(vm_host, port, "sync")
        vm = client.wait_success(client.delete(vm))
        assert vm.state == 'removed'
        wait_for_condition(
            super_client, vm,
            lambda x: x.state == "purged",
            lambda x: 'State is: ' + x.state)

        # Wait for VM to be recreated
        wait_for_vm_scale_to_adjust(super_client, service)
        vms = client.list_virtual_machine(
            name=vm.name,
            include="hosts",
            removed_null=True)
        assert len(vms) == 1
        vm = vms[0]
        new_vm_host = vms[0].hosts[0]
        time.sleep(TIME_TO_BOOT_IN_SEC)

        assert \
            read_data(new_vm_host, port, ROOT_DIR, file_name_r) == content_r
        make_dir(new_vm_host, port, DATA_DIR, False)
        mount_data_dir_check_file(new_vm_host, port, file_name_d, content_d)

        validate_writes(new_vm_host, port, is_root=True)
        validate_writes(new_vm_host, port, is_root=False)
        # Activate Host
        vm_host = client.wait_success(vm_host.activate())
        assert vm_host.state == 'active'

    delete_all(client, [env])


def test_createVM_with_root_and_data_on_longhorn_multiple(
        super_client, client):
    ports = [6088, 6089, 6090, 6091]
    scale = 1
    for port in ports:
        env, service, con = createVMService(
            super_client, client, "multiple",
            str(port), root_disk=True, data_disk=True,
            scale=scale)

        vms = get_service_vm_list(super_client, service)
        assert len(vms) == scale
        for vm in vms:
            assert vm.state == "running"
            assert vm.healthState == "healthy"
            vm_host = get_host_for_vm(client, vm)
            validate_writes(vm_host, port, is_root=True)
            validate_writes(vm_host, port, is_root=False)
        delete_all(client, [service])
