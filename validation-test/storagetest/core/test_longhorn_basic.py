from common_fixtures import *  # NOQA
import websocket as ws
import base64


VOLUME_DRIVER = "rancher-longhorn"

STACK_NAME_PREFIX = "volume-"
CONTROLLER = "controller"
REPLICA = "replica"


def test_container_with_volume_execute(client, test_name):
    volume_name = 'vol' + test_name
    cleanup_items = []
    cleanup_vols = []
    try:
        c = client.create_container(
                name=test_name,
                imageUuid=TEST_IMAGE_UUID,
                networkMode=MANAGED_NETWORK,
                dataVolumes=[volume_name + ":/vol"],
                volumeDriver=VOLUME_DRIVER,
                attachStdin=True,
                attachStdout=True,
                tty=True,
                command='/bin/bash')
        cleanup_items.append(c)
        container = client.wait_success(c, timeout=120)

        vols = client.list_volume(name=volume_name)
        assert len(vols) == 1
        cleanup_vols.append(vols[0])

        test_msg = 'EXEC_WORKS'
        assert_execute(container, test_msg)
    finally:
        delete_all(client, cleanup_items)

        for volume in cleanup_vols:
            volume = client.wait_success(client.delete(volume))
            assert volume.state == "removed"
            volume = client.wait_success(volume.purge())
            assert volume.state == "purged"


def test_container_migrate_volume(client, test_name):
    volume_name = 'vol' + test_name

    hosts = client.list_host(kind='docker', removed_null=True)
    assert len(hosts) > 2

    test_msg = 'EXEC_WORKS'
    cleanup_items = []
    cleanup_vols = []
    try:
        c1 = client.create_container(
                name=test_name,
                imageUuid=TEST_IMAGE_UUID,
                networkMode=MANAGED_NETWORK,
                dataVolumes=[volume_name + ":/vol"],
                volumeDriver=VOLUME_DRIVER,
                requestHostId=hosts[0].id,
                attachStdin=True,
                attachStdout=True,
                tty=True,
                command='/bin/bash')
        cleanup_items.append(c1)
        container = client.wait_success(c1, timeout=120)

        vols = client.list_volume(name=volume_name)
        assert len(vols) == 1
        cleanup_vols.append(vols[0])

        assert_execute(container, test_msg)

        client.wait_success(client.delete(c1))
        cleanup_items.remove(c1)

        c2 = client.create_container(
                name=test_name + "-2",
                imageUuid=TEST_IMAGE_UUID,
                networkMode=MANAGED_NETWORK,
                dataVolumes=[volume_name + ":/vol"],
                volumeDriver=VOLUME_DRIVER,
                requestHostId=hosts[1].id,
                attachStdin=True,
                attachStdout=True,
                tty=True,
                command='/bin/bash')
        cleanup_items.append(c2)
        container = client.wait_success(c2, timeout=180)

        assert_read(container, test_msg)

    finally:
        delete_all(client, cleanup_items)

        for volume in cleanup_vols:
            volume = client.wait_success(client.delete(volume))
            assert volume.state == "removed"
            volume = client.wait_success(volume.purge())
            assert volume.state == "purged"


def test_container_replica_down(admin_client, client, test_name):
    volume_name = 'vol' + test_name
    cleanup_items = []
    cleanup_vols = []
    try:
        c = client.create_container(
                name=test_name,
                imageUuid=TEST_IMAGE_UUID,
                networkMode=MANAGED_NETWORK,
                dataVolumes=[volume_name + ":/vol"],
                volumeDriver=VOLUME_DRIVER,
                attachStdin=True,
                attachStdout=True,
                tty=True,
                command='/bin/bash')
        cleanup_items.append(c)
        container = client.wait_success(c, timeout=120)

        vols = client.list_volume(name=volume_name)
        assert len(vols) == 1
        cleanup_vols.append(vols[0])

        test_msg = 'EXEC_WORKS'
        assert_execute(container, test_msg)

        replicas = get_replica_containers(admin_client, client, volume_name)
        assert len(replicas) == 2

        rep1 = client.wait_success(client.delete(replicas[0]))
        assert rep1.state == 'removed'

        # make sure data is intact
        assert_read(container, test_msg)

        test_msg = 'EXEC_WORKS_AFTER_REMOVE'
        assert_execute(container, test_msg)

        # TODO implement check of volume status, wait it to be UP

    finally:
        delete_all(client, cleanup_items)

        for volume in cleanup_vols:
            volume = client.wait_success(client.delete(volume))
            assert volume.state == "removed"
            volume = client.wait_success(volume.purge())
            assert volume.state == "purged"


@pytest.mark.skip(reason="need a way to stop replica without HA it")
def test_container_both_replica_down_and_rebuild(
        admin_client, client, test_name):
    volume_name = 'vol' + test_name
    cleanup_items = []
    cleanup_vols = []
    try:
        c1 = client.create_container(
                name=test_name,
                imageUuid=TEST_IMAGE_UUID,
                networkMode=MANAGED_NETWORK,
                dataVolumes=[volume_name + ":/vol"],
                volumeDriver=VOLUME_DRIVER,
                attachStdin=True,
                attachStdout=True,
                tty=True,
                command='/bin/bash')
        cleanup_items.append(c1)
        container = client.wait_success(c1, timeout=120)

        vols = client.list_volume(name=volume_name)
        assert len(vols) == 1
        cleanup_vols.append(vols[0])

        test_msg = 'EXEC_WORKS'
        assert_execute(container, test_msg)

        replicas = get_replica_containers(admin_client, client, volume_name)
        assert len(replicas) == 2

        rep1 = client.wait_success(replicas[0].stop())
        assert rep1.state == 'stopped'

        # make sure data is intact
        assert_read(container, test_msg)

        test_msg = 'EXEC_WORKS_AFTER_STOP'
        assert_execute(container, test_msg)

        rep2 = client.wait_success(replicas[1].stop())
        assert rep2.state == 'stopped'

        # now controller should be stopped, volume won't be available
        controller = get_controller_container(
                        admin_client, client, volume_name)
        con = client.wait_success(client.delete(controller))
        assert con.state == 'removed'

        print "wait_for container remove creation"
        client.wait_success(client.delete(c1))
        cleanup_items.remove(c1)

        # now a new controller should be started, use recent replicas
        # wait for volume to be in attached state again.

        c2 = client.create_container(
                name=test_name + "-2",
                imageUuid=TEST_IMAGE_UUID,
                networkMode=MANAGED_NETWORK,
                dataVolumes=[volume_name + ":/vol"],
                volumeDriver=VOLUME_DRIVER,
                attachStdin=True,
                attachStdout=True,
                tty=True,
                command='/bin/bash')
        cleanup_items.append(c2)
        print "wait_for new container creation"
        container = client.wait_success(c2, timeout=180)

        assert_read(container, test_msg)

        # TODO implement check of volume status, wait it to be UP

    finally:
        delete_all(client, cleanup_items)

        for volume in cleanup_vols:
            volume = client.wait_success(client.delete(volume))
            assert volume.state == "removed"
            volume = client.wait_success(volume.purge())
            assert volume.state == "purged"


def assert_execute(container, test_msg):
    execute = container.execute(attachStdin=True,
                                attachStdout=True,
                                command=['/bin/bash', '-c',
                                         'echo ' + test_msg +
                                         ' | tee /vol/test'],
                                tty=True)
    conn = ws.create_connection(execute.url + '?token=' + execute.token,
                                timeout=10)

    # Python is weird about closures
    closure_wrapper = {
        'result': ''
    }

    def exec_check():
        msg = conn.recv()
        closure_wrapper['result'] += base64.b64decode(msg)
        return test_msg == closure_wrapper['result'].rstrip()

    wait_for(exec_check,
             'Timeout waiting for exec msg %s' % test_msg)


def assert_read(container, test_msg):
    execute = container.execute(attachStdin=True,
                                attachStdout=True,
                                command=['/bin/bash', '-c',
                                         'cat /vol/test'],
                                tty=True)
    conn = ws.create_connection(execute.url + '?token=' + execute.token,
                                timeout=10)

    # Python is weird about closures
    closure_wrapper = {
        'result': ''
    }

    def exec_check():
        msg = conn.recv()
        closure_wrapper['result'] += base64.b64decode(msg)
        return test_msg == closure_wrapper['result'].rstrip()

    wait_for(exec_check,
             'Timeout waiting for exec msg %s' % test_msg)


def get_system_stack_name(volume_name):
    return STACK_NAME_PREFIX + volume_name


def get_replica_containers(admin_client, client, volume_name):
    stack_name = get_system_stack_name(volume_name)
    stack, replica_service = get_env_service_by_name(
                    client, stack_name, REPLICA)
    return get_service_containers_with_name(
                    admin_client,
                    replica_service,
                    stack_name + "-" + REPLICA)


def get_controller_container(admin_client, client, volume_name):
    stack_name = get_system_stack_name(volume_name)
    stack, replica_service = get_env_service_by_name(
                    client, stack_name, CONTROLLER)
    return get_service_containers_with_name(
                    admin_client,
                    replica_service,
                    stack_name + "-" + CONTROLLER)[0]
