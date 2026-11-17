*** Settings ***
Documentation    Negative Test Cases

Test Tags   v2-upgrade    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/node.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/secret.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Check v2 upgrade test prerequisites
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

Prepare v2 upgrade environment
    [Arguments]    ${interrupt_mode}=${False}
    Check v2 upgrade test prerequisites

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn stable version
    IF    ${interrupt_mode}
        Setting data-engine-interrupt-mode-enabled is set to {"v2":"true"}
    END
    And Enable v2 data engine and add block disks
    And Wait for longhorn ready
    And Setting replica-replenishment-wait-interval is set to 3600
    And Set default backupstore

Prepare attached v2 volume ${volume_id} with ${replica_count} replicas
    Create volume ${volume_id} with    dataEngine=v2    numberOfReplicas=${replica_count}
    Attach volume ${volume_id} to node 0
    Wait for volume ${volume_id} healthy
    Write data to volume ${volume_id}

Wait for instance manager upgrade relocation node for volume name ${volume_name} on node ${node_name}
    ${relocation_node}=    wait_for_instance_manager_upgrade_relocation_for_volume_name    ${volume_name}    ${node_name}
    [Return]    ${relocation_node}

*** Test Cases ***
Test System V2 Upgrade With Instance Manager Upgrade
    # This test takes longer because of the larger number of volumes in the cluster.
    [Documentation]    Verify that attached v2 volumes stay healthy during system upgrade
    ...    when the target version supports v2 instance manager upgrade.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create one v2 volume on each worker node, wait for each volume to become healthy, and write data to each volume.
    ...    4. Upgrade Longhorn to the custom version under test and wait for Longhorn to become ready again.
    ...    5. Verify all instance managers are running with the default target image.
    ...    6. Verify all upgraded attached v2 volumes remain healthy and their data stays intact.
    Given Prepare v2 upgrade environment
    ${worker_nodes}=    get_worker_nodes
    ${worker_count}=    Get Length    ${worker_nodes}

    FOR    ${i}    IN RANGE    ${worker_count}
        And Create volume vol${i} with    dataEngine=v2
        And Attach volume vol${i} to node ${i}
        And Wait for volume vol${i} healthy
        And Write data to volume vol${i}
    END

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed

    FOR    ${i}    IN RANGE    ${worker_count}
        And Wait for volume vol${i} healthy
        And Check volume vol${i} data is intact
    END


Test System V2 Upgrade With Instance Manager Live Upgrade
    [Documentation]    Verify that a single v2 volume maintains I/O and stays attached during instance manager live upgrade.
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create one v2 RWO PVC with 3 replicas and a deployment on node 0.
    ...    3. Start volume monitoring and continuous fio writes with CRC32C verification.
    ...    4. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade while fio is running.
    ...    5. Wait for all v2 instance managers to use the default target image and finish upgrading.
    ...    6. Verify the volume is healthy and its attachment and enginefrontend remain on node 0.
    ...    7. Continue I/O for 3 minutes after upgrade, stop fio, and verify data integrity.
    ...    8. Verify the workload pod did not restart and the volume never detached during the test.
    Given Prepare v2 upgrade environment
    And Create storageclass longhorn-test with    dataEngine=v2    numberOfReplicas=3
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    ...    args=apk add --no-cache fio && sleep infinity
    ...    node_selector={"kubernetes.io/hostname":"${NODE_0}"}
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    And Mark volume monitoring start time for deployment 0

    When Start fio write with crc32c verify in deployment 0
    Then Volume of deployment 0 engine CR and enginefrontend CR should be on same node

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume of deployment 0 healthy
    And Volume of deployment 0 should be attached to node 0
    And Volume of deployment 0 enginefrontend CR should be on node 0
    And Sleep    3 minutes

    When Stop fio in deployment 0
    Then Verify fio crc32c data in deployment 0 have no errors
    And Check deployment 0 pods did not restart
    And Volume of deployment 0 should never have detached during test


Test System V2 Upgrade With Instance Manager Upgrade With Single Interrupt Mode Volume
    [Documentation]    Verify that a single attached v2 volume stays healthy during live instance manager upgrade in interrupt mode.
    ...    Test steps
    ...    1. Install the stable Longhorn version and enable interrupt mode before enabling the v2 data engine.
    ...    2. Add block disks, create one attached v2 volume with 3 replicas, and write data to it.
    ...    3. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade.
    ...    4. Wait for all v2 instance managers to use the default target image and finish upgrading.
    ...    5. Verify the volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment    interrupt_mode=${True}
    And Prepare attached v2 volume 0 with 3 replicas

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact


Test System V2 Upgrade With Instance Manager Upgrade With Single Encrypted RWO Volume
    [Documentation]    Verify that a single encrypted v2 RWO volume stays healthy during live instance manager upgrade.
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create a crypto secret and one encrypted v2 RWO PVC with 3 replicas.
    ...    3. Create a deployment using the PVC and write data through the workload.
    ...    4. Upgrade Longhorn to the custom version while the volume remains attached and enable instance manager automatic upgrade.
    ...    5. Wait for all v2 instance managers to use the default target image and finish upgrading.
    ...    6. Verify the volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment
    And Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=v2    numberOfReplicas=3
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Check deployment 0 data in file data.txt is intact


Test System V2 Upgrade With Instance Manager Upgrade with RWX Volume
    [Documentation]    Verify that a v2 RWX volume stays healthy during system upgrade
    ...    when the target version supports v2 instance manager upgrade.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create a v2 RWX storage class, provision an RWX PVC and deployment, then write data through the workload.
    ...    4. Upgrade Longhorn to the custom version under test and wait for Longhorn to become ready again.
    ...    5. Verify all instance managers are running with the default target image.
    ...    6. Verify the upgraded RWX volume remains healthy and its data stays intact.
    Given Prepare v2 upgrade environment

    When Create storageclass longhorn-test-rwx with    dataEngine=v2    numberOfReplicas=3
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test-rwx
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Check deployment 0 data in file data.txt is intact


Test System V2 Upgrade With RWO Volume Expansion
    [Documentation]    Verify that attached v2 RWO volumes can be expanded
    ...    while their instance managers are being upgraded during a Longhorn system upgrade.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create a v2 RWO PVC (2GiB) with pod and write file data to it.
    ...    4. Upgrade Longhorn, enable v2 instance manager automatic upgrade.
    ...    5. Wait for the RWO volume's instance manager upgrade to start (engine relocation begins).
    ...    6. Trigger volume expansion from 2GiB to 3Gi while the instance manager upgrade is in progress.
    ...    7. Wait for all instance manager upgrades to complete.
    ...    8. Verify the volume reaches the expanded size, becomes healthy, and file data remains intact.
    Given Prepare v2 upgrade environment
    And Create storageclass longhorn-test-rwo with    dataEngine=v2    numberOfReplicas=3
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test-rwo    storage_size=2GiB
    And Create pod 0 using persistentvolumeclaim 0
    And Wait for pod 0 running
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Write 100 MB data to file data.txt in pod 0

    # Get volume name and engine node before upgrade
    ${claim_name}=    generate_name_with_suffix    claim    0
    ${volume_name}=    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    ${source_engine_node}=    get_volume_node    ${volume_name}

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true

    # Wait for volume's IM upgrade to start (engine relocation begins)
    And Wait for instance manager upgrade relocation node for volume name ${volume_name} on node ${source_engine_node}

    # Now expand while IM upgrade is in progress
    When Expand persistentvolumeclaim 0 size to 3Gi

    # Wait for instance manager upgrades to complete before checking sizes
    # (during migration there are 2 engines which causes size check to fail)
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed

    # Verify volume expanded and data is intact
    Then Wait for volume of persistentvolumeclaim 0 size to be 3Gi
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Check pod 0 data in file data.txt is intact


Test System V2 Upgrade With RWX Volume Expansion
    [Documentation]    Verify that attached v2 RWX volumes can be expanded
    ...    while their instance managers are being upgraded during a Longhorn system upgrade.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create a v2 RWX PVC (2GiB) with deployment and write file data to it.
    ...    4. Upgrade Longhorn, enable v2 instance manager automatic upgrade.
    ...    5. Get the RWX backing Longhorn volume name.
    ...    6. Wait for that volume's instance manager upgrade to start (engine relocation begins).
    ...    7. Trigger volume expansion from 2GiB to 3Gi while the instance manager upgrade is in progress.
    ...    8. Wait for all instance manager upgrades to complete.
    ...    9. Verify the volume reaches the expanded size, becomes healthy, and file data remains intact.
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Log To Console    Running RWX volume expansion upgrade iteration ${i+1}/${LOOP_COUNT}
        Given Prepare v2 upgrade environment
        And Create storageclass longhorn-test-rwx with    dataEngine=v2    numberOfReplicas=3
        And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test-rwx    storage_size=2GiB
        And Create deployment 0 with persistentvolumeclaim 0
        And Wait for volume of persistentvolumeclaim 0 healthy
        And Write 100 MB data to file data.txt in deployment 0

        # Get RWX backing volume name and engine node before upgrade
        ${claim_name}=    generate_name_with_suffix    claim    0
        ${volume_name}=    get_volume_name_from_persistentvolumeclaim    ${claim_name}
        ${source_engine_node}=    get_volume_node    ${volume_name}

        When Upgrade Longhorn to custom version
        Then Wait for longhorn ready
        And Setting allow-instance-manager-automatic-upgrade is set to true

        # Wait for RWX volume's IM upgrade to start (engine relocation begins)
        And Wait for instance manager upgrade relocation node for volume name ${volume_name} on node ${source_engine_node}

        # Now expand while IM upgrade is in progress
        When Expand deployment 0 volume to 3Gi

        # Wait for instance manager upgrades to complete before checking sizes
        # (during migration there are 2 engines which causes size check to fail)
        And Wait for all v2 instance managers running with default image
        And Wait for all v2 instance manager upgrades completed

        # Verify volume expanded and data is intact
        Then Wait for deployment 0 volume size expanded
        And Wait for volume of persistentvolumeclaim 0 healthy
        And Check deployment 0 data in file data.txt is intact

        # Clean up before uninstalling Longhorn in the next iteration.
        And Delete deployment 0
        And Delete persistentvolumeclaim 0
        And Delete storageclass longhorn-test-rwx
    END


Test System V2 Upgrade With Instance Manager Upgrade DR Volume
    [Documentation]    Verify that a v2 DR volume continues to function across system upgrade
    ...    with instance manager upgrade by completing both the initial restore and a
    ...    post-upgrade incremental restore from the source volume.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create 1 attached v2 source volume, wait for it to become healthy, and write data to it.
    ...    4. Create a backup for the source volume, create a v2 DR volume from that backup, and wait for the initial DR restore to complete.
    ...    5. Upgrade Longhorn to the custom version under test and wait for Longhorn to become ready again.
    ...    6. Verify all instance managers are running with the default target image.
    ...    7. Write more data to the source volume, create another backup, and verify the DR volume completes the post-upgrade incremental restore.
    Given Prepare v2 upgrade environment
    And Prepare attached v2 volume 0 with 3 replicas
    And Create backup 0 for volume 0
    And Wait for backup 0 of volume 0 to exist in backup list
    And Create DR volume 1 from backup 0 of volume 0    dataEngine=v2
    And Wait for volume 1 restoration from backup 0 of volume 0 completed

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

    When Write data 1 to volume 0
    And Volume 0 backup 1 should be able to create
    And Wait for volume 1 restoration from backup 1 of volume 0 start
    Then Wait for volume 1 restoration from backup 1 of volume 0 completed
    And Activate DR volume 1
    And Attach volume 1 to healthy node
    And Wait for volume 1 healthy
    And Check volume 1 data is backup 1 of volume 0


Test System V2 Upgrade With Instance Manager Upgrade Blocked By Strict Local Volume
    [Documentation]    Verify that the v2 instance manager upgrade on a node is blocked by a
    ...    single replica strict-local volume on that node, and succeeds once the volume is deleted.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/14469
    ...
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create a single replica strict-local volume on node 0, and a normal 3-replica volume, and write data to them.
    ...    3. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade.
    ...    4. Verify the v2 instance manager upgrade on node 0 fails with the error "upgrade requirement unsupported".
    ...    5. Verify the v2 instance manager upgrades on the other nodes succeed.
    ...    6. Delete the single replica strict-local volume.
    ...    7. Verify the v2 instance manager upgrade on node 0 succeeds.
    ...    8. Verify the 3-replica volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment
    And Create volume 0 with    dataEngine=v2    numberOfReplicas=1    dataLocality=strict-local
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Prepare attached v2 volume 1 with 3 replicas

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for v2 instance manager upgrade on node 0 failed
    And Run command and wait for output
    ...    kubectl get instancemanagerupgrades.longhorn.io -n longhorn-system -l longhorn.io/node=${NODE_0} -o jsonpath='{.items[0].status.errorMsg}'
    ...    upgrade requirement unsupported
    And Wait for v2 instance manager upgrade on node 1 completed
    And Wait for v2 instance manager upgrade on node 2 completed

    When Delete volume 0
    And Wait for volume 0 deleted
    Then Wait for v2 instance manager upgrade on node 0 completed
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume 1 healthy
    And Check volume 1 data is intact
    And Check volume 1 works


Test System V2 Upgrade With Instance Manager Upgrade Blocked By Sharded Volume
    [Documentation]    Verify that the v2 instance manager upgrade on a node is blocked by
    ...    a sharded volume on that node, and succeeds once the volume is deleted.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/14469
    ...
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create a sharded volume on node 0, and a normal 3-replica volume, and write data to them.
    ...    3. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade.
    ...    4. Verify the v2 instance manager upgrade on node 0 fails with the error "upgrade requirement unsupported".
    ...    5. Verify the v2 instance manager upgrades on the other nodes fail as well, since the shards are on all nodes.
    ...    6. Delete the sharded volume.
    ...    7. Verify the v2 instance manager upgrades on all nodes succeed.
    ...    8. Verify the 3-replica volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment
    ${dataLayout} =    Create Dictionary
    ...    type=sharded
    ...    mode=erasureCoding
    ...    dataChunks=2
    ...    parityChunks=1
    ...    stripSizeKB=64
    And Create volume 0 with    dataEngine=v2    numberOfReplicas=1    dataLayout=${dataLayout}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Prepare attached v2 volume 1 with 3 replicas

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for v2 instance manager upgrade on node 0 failed
    And Run command and wait for output
    ...    kubectl get instancemanagerupgrades.longhorn.io -n longhorn-system -l longhorn.io/node=${NODE_0} -o jsonpath='{.items[0].status.errorMsg}'
    ...    upgrade requirement unsupported
    # The shards of the sharded volume are on the other 2 nodes as well, so the
    # v2 instance manager upgrades on all nodes are expected to fail
    And Wait for v2 instance manager upgrade on node 1 failed
    And Wait for v2 instance manager upgrade on node 2 failed

    When Delete volume 0
    And Wait for volume 0 deleted
    Then Wait for v2 instance manager upgrade on node 0 completed
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume 1 healthy
    And Check volume 1 data is intact
    And Check volume 1 works


Test System V2 Upgrade With Instance Manager Upgrade Aborted By Node Power Off
    [Documentation]    Verify that the v2 instance manager upgrade on a node is aborted when
    ...    the node is powered off during the upgrade, and succeeds after the node is powered on.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/14469
    ...
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create an attached 3-replica volume on node 0 and write data to it.
    ...    3. Upgrade Longhorn to the custom version.
    ...    4. Set instance-manager-upgrade-timeout to 10 minutes and enable instance manager automatic upgrade.
    ...    5. Wait for the v2 instance manager upgrade on node 0 to be relocating engines.
    ...    6. Power off node 0 and wait for the upgrade on node 0 to be aborted by the timeout.
    ...    7. Power on node 0 and wait for the v2 instance manager on node 0 to be running.
    ...    8. Verify the v2 instance manager on node 0 still runs the stable image.
    ...    9. Wait for the v2 instance manager upgrade on node 0 to be completed.
    ...    10. Verify the volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment
    And Prepare attached v2 volume 0 with 3 replicas
    ${stable_image} =    Get v2 instance manager image on node 0

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting instance-manager-upgrade-timeout is set to {"v2":"10"}
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for v2 instance manager upgrade on node 0 relocating-engines

    When Power off node 0
    Then Wait for v2 instance manager upgrade on node 0 aborted

    When Power on node 0
    And Wait for longhorn ready
    Then Wait for v2 instance manager image to be ${stable_image} on node 0
    And Wait for v2 instance manager upgrade on node 0 completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact
    And Check volume 0 works


Test System V2 Upgrade With Instance Manager Upgrade Temporary Node Power Off
    [Documentation]    Verify that the v2 instance manager upgrade on a node relocates the engine to
    ...    another temporary node and completes when the original temporary node is powered off.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/14469
    ...
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create an attached 3-replica volume on node 0 and write data to it.
    ...    3. Upgrade Longhorn to the custom version.
    ...    4. Set instance-manager-upgrade-timeout to 10 minutes and enable instance manager automatic upgrade.
    ...    5. Wait for the v2 instance manager upgrade on node 0 to be relocating engines.
    ...    6. Power off the temporary node of the volume engine in the upgrade.
    ...    7. Wait for the temporary node of the upgrade to move to another node.
    ...    8. Verify the v2 instance manager upgrade on node 0 is waiting for healthy volumes, since the powered-off node holds a replica of the volume.
    ...    9. Power on the original temporary node and wait for its v2 instance manager to be running.
    ...    10. Wait for all v2 instance manager upgrades to be completed.
    ...    11. Verify the volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment
    And Prepare attached v2 volume 0 with 3 replicas

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting instance-manager-upgrade-timeout is set to {"v2":"10"}
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for v2 instance manager upgrade on node 0 relocating-engines

    # the volume engine is relocated to node 1 or node 2, if the temporary node
    # is powered off, the engine must be relocated to the other one
    ${temporary_node} =    Run command
    ...    kubectl get instancemanagerupgrades.longhorn.io -n longhorn-system -l longhorn.io/node=${NODE_0} -o jsonpath='{.items[0].status.engines.*.temporaryNodeID}'
    ${new_temporary_node} =    Set Variable If    '${temporary_node}' == '${NODE_1}'    ${NODE_2}    ${NODE_1}
    When Power off node ${temporary_node}
    Then Run command and wait for output
    ...    kubectl get instancemanagerupgrades.longhorn.io -n longhorn-system -l longhorn.io/node=${NODE_0} -o jsonpath='{.items[0].status.engines.*.temporaryNodeID}'
    ...    ${new_temporary_node}
    # The upgrade can't complete while the temporary node is powered off: the volume
    # has a replica can't be rebuilt on another node since there are only 3 nodes.
    # The volume stays degraded,
    # so the upgrade waits for healthy volumes until the node is powered on again.
    And Wait for v2 instance manager upgrade on node 0 waiting-for-healthy-volumes

    When Power on node ${temporary_node}
    And Wait for longhorn ready
    Then Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact
    And Check volume 0 works


Test System V2 Upgrade With Instance Manager Upgrade With Replica Deletion In Each State
    [Documentation]    Verify that deleting the replica on the upgrading node in each state of the
    ...    v2 instance manager upgrade does not break the upgrade or the volume.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/14469
    ...
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create an attached 3-replica volume on node 0 and write data to it.
    ...    3. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade.
    ...    4. For each upgrade state relocating-engines, waiting-for-source-im
    ...       and waiting-for-healthy-volumes on node 0:
    ...       a. Wait for the v2 instance manager upgrade on node 0 to be in the state.
    ...       b. Delete the replica on node 0.
    ...       c. Wait for the replica rebuilding on node 0 to complete.
    ...       d. Wait for the volume to be healthy.
    ...    5. Wait for all v2 instance manager upgrades to complete.
    ...    6. Verify the volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment
    And Prepare attached v2 volume 0 with 3 replicas

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true

    # A normal successful transition is:
    # pending -> relocating-engines -> waiting-for-source-im -> restoring-engines -> waiting-for-healthy-volumes -> completed
    # The pending and restoring-engines states are skipped because they could be too fast for the test code to catch
    When Wait for v2 instance manager upgrade on node 0 relocating-engines
    Then Delete volume 0 replica on node 0
    And Wait until volume 0 replica rebuilding completed on node 0
    And Wait for volume 0 healthy

    When Wait for v2 instance manager upgrade on node 0 waiting-for-source-im
    Then Delete volume 0 replica on node 0

    When Wait for v2 instance manager upgrade on node 0 waiting-for-healthy-volumes
    Then Delete volume 0 replica on node 0
    And Wait until volume 0 replica rebuilding completed on node 0
    And Wait for volume 0 healthy

    Then Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact
    And Check volume 0 works


Test System V2 Upgrade With Instance Manager Upgrade Disabled During Upgrade
    [Documentation]    Verify that disabling allow-instance-manager-automatic-upgrade during the
    ...    v2 instance manager upgrade of a node lets that upgrade complete, but no upgrade starts on other nodes.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/14469
    ...
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create an attached 3-replica volume on node 0 and write data to it.
    ...    3. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade.
    ...    4. Wait for a v2 instance manager upgrade to be created on a node (node A).
    ...    5. Disable instance manager automatic upgrade.
    ...    6. Wait for the v2 instance manager upgrade on node A to complete.
    ...    7. Verify no v2 instance manager upgrade starts on other nodes for 3 minutes.
    ...    8. Verify the v2 instance manager image on node A is upgraded, and kept on other nodes.
    ...    9. Verify the volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment
    And Prepare attached v2 volume 0 with 3 replicas
    ${stable_image} =    Get v2 instance manager image on node 0

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for v2 instance manager upgrade to start
    ${node_a} =    Run command
    ...    kubectl get instancemanagerupgrades.longhorn.io -n longhorn-system -o jsonpath='{.items[0].spec.nodeID}'
    And Setting allow-instance-manager-automatic-upgrade is set to false
    And Wait for v2 instance manager upgrade on node ${node_a} completed

    ${default_image} =    Run command
    ...    kubectl get settings.longhorn.io default-instance-manager-image -n longhorn-system -o jsonpath='{.value}'
    # node A is upgraded, no v2 instance manager upgrade should be created on
    # other nodes, and their instance managers keep the original image
    FOR    ${node}    IN    ${NODE_0}    ${NODE_1}    ${NODE_2}
        IF    '${node}' != '${node_a}'
            Run Keyword And Expect Error    *    Wait for v2 instance manager upgrade to start on node ${node}    timeout=180
            Wait for v2 instance manager image to be ${stable_image} on node ${node}
        ELSE
            Wait for v2 instance manager image to be ${default_image} on node ${node}
        END
    END

    And Wait for volume 0 healthy
    And Check volume 0 data is intact
    And Check volume 0 works


Test System V2 Upgrade With Instance Manager Upgrade Timeout
    [Documentation]    Verify that the v2 instance manager upgrade on a node fails when the upgrade
    ...    times out, and that the failed upgrade is retried and succeeds after the timeout is relaxed.
    ...    A failed upgrade is only retried after the upgrades on the other nodes completed.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/14469
    ...
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create an attached 3-replica volume on node 0 and write data to it.
    ...    3. Upgrade Longhorn to the custom version.
    ...    4. Enable instance manager automatic upgrade and wait for a v2 instance manager upgrade to start.
    ...    5. Get the node currently being upgraded and set instance-manager-upgrade-timeout to 1.
    ...    6. Wait for the upgrade on the current node to fail.
    ...    7. Set instance-manager-upgrade-timeout to 60.
    ...    8. Wait for the upgrades on the other nodes to complete.
    ...    9. Wait for the upgrade on the current node to complete.
    ...    10. Verify the volume is healthy and the data is intact.
    Given Prepare v2 upgrade environment
    And Prepare attached v2 volume 0 with 3 replicas

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready

    When Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for v2 instance manager upgrade to start
    ${current_node} =    Run command
    ...    kubectl get instancemanagerupgrades.longhorn.io -n longhorn-system -o jsonpath='{.items[0].spec.nodeID}'
    And Setting instance-manager-upgrade-timeout is set to {"v2":"1"}
    Then Wait for v2 instance manager upgrade on node ${current_node} failed

    When Setting instance-manager-upgrade-timeout is set to {"v2":"60"}
    FOR    ${node}    IN    ${NODE_0}    ${NODE_1}    ${NODE_2}
        IF    '${node}' != '${current_node}'
            Wait for v2 instance manager upgrade on node ${node} completed
        END
    END
    Then Wait for v2 instance manager upgrade on node ${current_node} completed

    And Wait for volume 0 healthy
    And Check volume 0 data is intact
    And Check volume 0 works


Test System V2 Upgrade With Instance Manager Upgrade Longhorn Manager Pod Deletion In Each State
    [Documentation]    Verify that the v2 instance manager upgrade on a node eventually succeeds
    ...    when the longhorn-manager pod on the node is deleted in each state of the upgrade.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/14469
    ...
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create an attached 3-replica volume on node 0 and write data to it.
    ...    3. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade.
    ...    4. For each upgrade state relocating-engines, waiting-for-source-im
    ...       and waiting-for-healthy-volumes on node 0:
    ...       a. Wait for the v2 instance manager upgrade on node 0 to be in the state.
    ...       b. Delete the longhorn-manager pod on node 0.
    ...    5. Wait for all v2 instance manager upgrades to complete.
    Given Prepare v2 upgrade environment
    And Prepare attached v2 volume 0 with 3 replicas

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true

    # The pending and restoring-engines states are skipped because they could be too fast for the test code to catch
    FOR    ${state}    IN    relocating-engines    waiting-for-source-im    waiting-for-healthy-volumes
        Wait for v2 instance manager upgrade on node 0 ${state}
        Delete Longhorn DaemonSet longhorn-manager pod on node 0
    END

    Then Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
