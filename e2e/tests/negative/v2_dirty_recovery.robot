*** Settings ***
Documentation    Negative Test Cases for v2 blobstore dirty recovery
...    Ref: https://github.com/longhorn/longhorn/issues/12837
...
...    The main purpose is to trigger blobstore dirty recovery: when spdk_tgt stops without
...    unloading the lvstore cleanly, the lvstore of every v2 disk is left dirty, and spdk_tgt
...    has to recover it when the disk is loaded again. Force-stopping all worker nodes (aws)
...    leaves the lvstore dirty in practice, but does not guarantee it, so the test checks the
...    instance manager logs to make sure dirty recovery really ran.

Test Tags    negative    v2    v2-dirty-recovery

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/volume.resource

Test Setup    Set up v2 dirty recovery test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Set up v2 dirty recovery test environment
    Skip If    '${DATA_ENGINE}' != 'v2'    Dirty blobstore recovery only applies to the v2 data engine
    Set up test environment

Wait for volume ${volume_id} device recreated on node ${node_id}
    # After all worker nodes power off, longhorn-manager is down too, so the volume CR
    # keeps reporting attached and healthy until the manager reconciles it again. The
    # volume device (nvme -> linear dm -> /dev/longhorn/<volume>) only lives in kernel
    # memory and devtmpfs, so it is gone after the reboot and shows up again only after
    # the volume is reattached in this boot. Wait for it before trusting the volume CR.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run command on node ${node_id} and wait for output
    ...    test -b /dev/longhorn/${volume_name} && echo device-recreated
    ...    device-recreated

*** Test Cases ***
Test V2 Volume Data Should Be Intact After Dirty Recovery
    [Documentation]    Use single replica strict-local volumes, so a recovery error cannot be
    ...    hidden by rebuilding the replica from another node.
    ...
    ...    - Given on every node, create a strict-local volume with 1 replica, write data,
    ...      create a snapshot and overwrite part of the data, so reading the volume reads
    ...      clusters of both the snapshot and the volume head.
    ...    - And on every node, create another strict-local volume and keep writing to it,
    ...      so there are writes in flight when the nodes power off.
    ...    - When force-stop all worker nodes at the same time to trigger dirty recovery,
    ...      and power them on.
    ...    - Then the data of every idle volume is intact and its snapshot is still the
    ...      parent of the volume head.
    ...    - And every busy volume still works.
    ...    - And every v2 instance manager log shows that batched dirty recovery completed.
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        FOR    ${node_id}    IN RANGE    3
            ${busy_volume_id} =    Evaluate    ${node_id} + 3
            Given Create volume ${node_id} with    numberOfReplicas=1    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
            And Attach volume ${node_id} to node ${node_id}
            And Wait for volume ${node_id} healthy
            And Write data 0 512 MB to volume ${node_id}
            And Create snapshot 0 of volume ${node_id}
            And Write data 1 256 MB to volume ${node_id}

            And Create volume ${busy_volume_id} with    numberOfReplicas=1    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
            And Attach volume ${busy_volume_id} to node ${node_id}
            And Wait for volume ${busy_volume_id} healthy
            And Keep writing data to volume ${busy_volume_id}
        END

        When Get test start time
        And Restart all worker nodes
        And Wait for longhorn ready

        FOR    ${node_id}    IN RANGE    3
            ${busy_volume_id} =    Evaluate    ${node_id} + 3
            Then Wait for volume ${node_id} device recreated on node ${node_id}
            And Wait for volume ${node_id} healthy
            And Check volume ${node_id} data is intact
            And Validate snapshot 0 is parent of volume-head in volume ${node_id} snapshot list
            And Wait for volume ${busy_volume_id} device recreated on node ${node_id}
            And Wait for volume ${busy_volume_id} healthy
            And Check volume ${busy_volume_id} works
            And Verify v2 instance manager log on node ${node_id} contain Batched blobstore recovery completed after test start
        END

        FOR    ${volume_id}    IN RANGE    6
            And Detach volume ${volume_id} from attached node
            And Wait for volume ${volume_id} detached
            And Delete volume ${volume_id}
        END
    END
