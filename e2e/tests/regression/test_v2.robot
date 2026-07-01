*** Settings ***
Documentation    v2 Data Engine Test Cases

Test Tags    regression    v2

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/node.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/orphan.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/engine_frontend.resource
Resource    ../keywords/io.resource

Test Setup    Set up v2 test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Set up v2 test environment
    Set up test environment
    Enable v2 data engine and add block disks

Cleanup engine frontend test on node ${node_id}
    Make enginefrontend metadata directory mutable on node ${node_id}
    Clean enginefrontend files on node ${node_id}
    Cleanup test resources

*** Test Cases ***
Test V2 Volume Basic
    [Tags]  coretest
    [Documentation]    Test basic v2 volume operations
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    When Create volume 0 with    dataEngine=v2
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Check volume 0 data is intact
    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0

Test V2 Snapshot
    [Tags]    coretest
    [Documentation]    Test snapshot operations
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Create volume 0 with    dataEngine=v2
    When Attach volume 0
    And Wait for volume 0 healthy

    And Create snapshot 0 of volume 0

    And Write data 1 to volume 0
    And Create snapshot 1 of volume 0

    And Write data 2 to volume 0
    And Create snapshot 2 of volume 0

    Then Validate snapshot 0 is parent of snapshot 1 in volume 0 snapshot list
    And Validate snapshot 1 is parent of snapshot 2 in volume 0 snapshot list
    And Validate snapshot 2 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 2 CR of volume 0
    Then Wait for snapshot 2 to not be in volume 0 snapshot list
    And Check volume 0 data is data 2

    When Detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0 in maintenance mode
    And Wait for volume 0 healthy

    And Revert volume 0 to snapshot 1
    And Detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0
    And Wait for volume 0 healthy
    Then Check volume 0 data is data 1
    And Validate snapshot 1 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 1 CR of volume 0
    And Delete snapshot 0 CR of volume 0

    # delete a snapshot won't mark the snapshot as removed
    # but directly remove it from the snapshot list without purge
    Then Validate snapshot 1 is not in volume 0 snapshot list
    And Validate snapshot 0 is not in volume 0 snapshot list

    And Check volume 0 data is data 1

Degraded Volume Replica Rebuilding
    [Tags]    coretest    replica
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Disable node 2 scheduling
    And Create storageclass longhorn-test with    dataEngine=v2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached and degraded
    And Write 2048 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on node 0
        And Wait until volume of deployment 0 replica rebuilding completed on node 0
        And Delete replica of deployment 0 volume on node 1
        And Wait until volume of deployment 0 replica rebuilding completed on node 1
        And Wait for volume of deployment 0 attached and degraded
        And Wait for deployment 0 pods stable
        Then Check deployment 0 data in file data.txt is intact
    END

V2 Volume Should Block Trim When Volume Is Degraded
    [Tags]    cluster
    [Documentation]    Issues:
    ...    https://github.com/longhorn/longhorn-tests/pull/2114
    ...    https://github.com/longhorn/longhorn/issues/8430
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Setting auto-salvage is set to true
    And Create storageclass longhorn-test with    dataEngine=v2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0

        When Restart cluster
        And Wait for longhorn ready
        And Wait for volume of deployment 0 attached and degraded
        Then Trim deployment 0 volume should fail

        When Wait for workloads pods stable
        ...    deployment 0
        And Wait for volume of deployment 0 healthy
        And Check deployment 0 works
        Then Trim deployment 0 volume should pass
    END

V2 Volume Should Cleanup Resources When Instance Manager Is Deleted
    [Tags]    coretest
    [Documentation]    Verify that v2 volumes cleanup resources when their instance manager
    ...                is deleted. And ensure this process does not impact v1 volumes.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/9959

    When Create volume 0 with    dataEngine=v2
    And Create volume 1 with    dataEngine=v2
    And Create volume 2 with    dataEngine=v1
    And Attach volume 0 to node 0
    And Attach volume 1 to node 0
    And Attach volume 2 to node 0
    And Wait for volume 0 healthy
    And Wait for volume 1 healthy
    And Wait for volume 2 healthy
    And Write data to volume 0
    And Write data to volume 1
    And Write data to volume 2

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Cordon node 0
        And Delete v2 instance manager of volume 0

        Then Assert DM device for volume 0 not exist on node 0
        And Assert DM device for volume 1 not exist on node 0
        And Assert device for volume 0 not exist on node 0
        And Assert device for volume 1 not exist on node 0
        And Assert device for volume 2 does exist on node 0

        When Uncordon node 0
        And Wait for volume 0 healthy
        And Wait for volume 1 healthy
        And Wait for volume 2 healthy

        Then Assert DM device for volume 0 does exist on node 0
        And Assert DM device for volume 1 does exist on node 0
        And Assert device for volume 0 does exist on node 0
        And Assert device for volume 1 does exist on node 0
        And Assert device for volume 2 does exist on node 0
        And Check volume 0 data is intact
        And Check volume 1 data is intact
        And Check volume 2 data is intact
    END

Test V2 Data Engine Selective Activation
    [Tags]    replica
    # create volumes with 2 replicas on node 0 and node 1
    # there is no replica on node 2
    Given Create volume 0 attached to node 0 with 2 replicas excluding node 2    dataEngine=v2
    And Create volume 1 attached to node 0 with 2 replicas excluding node 2    dataEngine=v1

    When Label node 2 with node.longhorn.io/disable-v2-data-engine=true
    Then Check v2 instance manager is not running on node 2
    And Check v1 instance manager is running on node 2

    When Label node 2 with node.longhorn.io/disable-v2-data-engine-
    Then Check v2 instance manager is running on node 2

    When Update volume 0 replica count to 3
    And Wait for volume 0 healthy
    Then Volume 0 should have running replicas on node 2

Test V2 Data Engine Selective Activation During Replica Rebuilding
    [Tags]    replica
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Create volume 0 attached to node 0 with 2 replicas excluding node 2    dataEngine=v2
    And Wait for volume 0 healthy
    And Write data to volume 0

    When Label node 2 with node.longhorn.io/disable-v2-data-engine=true
    And Delete volume 0 replica on node 0
    And Wait until volume 0 replicas rebuilding completed
    And Delete volume 0 replica on node 1
    And Wait until volume 0 replicas rebuilding completed
    Then Volume 0 should have 0 replicas on node 2
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test V2 Data Engine Selective Activation With Existing Engine And Replica
    [Tags]    replica
    # create a volume with replicas on node 0 and node 1
    # and attach it to node 2
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Create volume 0 attached to node 2 with 2 replicas excluding node 2    dataEngine=v2

    When Run command and expect output
    ...    kubectl label node ${NODE_0} node.longhorn.io/disable-v2-data-engine=true
    ...    cannot disable v2 data engine

    When Run command and expect output
    ...    kubectl label node ${NODE_2} node.longhorn.io/disable-v2-data-engine=true
    ...    cannot disable v2 data engine

Check Block Device Is Not In Use Before Creating Disk
    [Documentation]    Issue:
    ...    https://github.com/longhorn/longhorn/issues/12179
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    When Create 1 Gi block type device block-device-check on node 0
    And Run command on node    0
    ...    sudo mkfs.xfs ${mount_path}
    And Add block device block-device-check on node 0 should result in unschedulable state
    And Disable disk block-device-check scheduling without ready check on node 0
    And Delete disk block-device-check on node 0

    When Run command on node    0
    ...    sudo wipefs -a ${mount_path}
    And Add block device block-device-check on node 0 should success

Test Default Block Disks Delete And Re-add
    [Tags]    block-disk
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12637
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    # Run at least 3 loops to ensure stability when default block disks
    # are deleted and re-added multiple times
    IF    ${LOOP_COUNT} < 3
        ${loop_count}=    Set Variable    3
    ELSE
        ${loop_count}=    Set Variable    ${LOOP_COUNT}
    END

    FOR    ${i}    IN RANGE    ${loop_count}
        Given Disable default block disks on all worker nodes
        When Delete default block disks on all worker nodes
        Then Add default block disks on all worker nodes
    END
    Given Create volume 0 with    size=2Gi    numberOfReplicas=3    dataEngine=v2
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    When Write data to volume 0
    Then Check volume 0 data is intact

Test V2 Volume Engine Live Switchover
    [Tags]    v2
    [Documentation]    Test v2 volume cross-node initiator and target support with live switchover.
    ...                Verify data integrity is maintained when engine moves across nodes
    ...                while volume and enginefront remain on the original node.
    ...
    ...                Related issue:
    ...                https://github.com/longhorn/longhorn/issues/7124
    ...
    ...                Manual test steps:
    ...                https://github.com/longhorn/longhorn/issues/7124#issuecomment-4349501341
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Create storageclass longhorn-test with    dataEngine=v2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    ...    args=apk add --no-cache fio && sleep infinity
    ...    node_selector={"kubernetes.io/hostname":"${NODE_0}"}
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    And Mark volume monitoring start time for deployment 0

    When Start fio randwrite with crc32c verify in deployment 0
    Then Volume of deployment 0 engine CR and enginefrontend CR should be on same node

    # Test 1: Move engine to node 1
    When Update volume of deployment 0 engineNodeID to node 1
    Then Volume of deployment 0 should be attached to node 0
    And Volume of deployment 0 engine CR should be on node 1
    And Volume of deployment 0 enginefrontend CR should be on node 0
    # Sleep to test I/O stability after engine live switchover
    And Sleep    3 minutes

    # Test 2: Move engine to node 2
    When Update volume of deployment 0 engineNodeID to node 2
    Then Volume of deployment 0 should be attached to node 0
    And Volume of deployment 0 engine CR should be on node 2
    And Volume of deployment 0 enginefrontend CR should be on node 0
    # Sleep to test I/O stability after engine live switchover
    And Sleep    3 minutes

    # Test 3: Move engine back to node 0
    When Update volume of deployment 0 engineNodeID to node 0
    Then Volume of deployment 0 should be attached to node 0
    And Volume of deployment 0 engine CR should be on node 0
    And Volume of deployment 0 enginefrontend CR should be on node 0
    # Sleep to test I/O stability after engine live switchover
    And Sleep    3 minutes

    When Stop fio in deployment 0
    Then Verify fio crc32c data in deployment 0 have no errors
    And Check deployment 0 pods did not restart
    And Volume of deployment 0 should never have detached during test

Test V2 Instance Manager Pod Recreate Loop When Engine Frontend Recovery Blocks GRPC Startup
    [Documentation]    issue: https://github.com/longhorn/longhorn/issues/13185
    ...    Verify instance manager pod can recover from multiple stale enginefrontend.json
    ...    that blocks GRPC startup, preventing pod recreate loop.
    ...
    ...    Test Flow:
    ...    1. Create five v2 volumes
    ...    2. Attach them to node 0
    ...    3. Make node 0 enginefrontend directory immutable
    ...    4. Delete all v2 volumes
    ...    5. Restore directory to mutable
    ...    5. Delete the v2 instance manager on node 0
    ...    6. Verify instance manager on node 0 running well (with 5 stale files)
    ...    7. Create new v2 volume and verify it works
    [Teardown]    Cleanup engine frontend test on node 0
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    FOR    ${i}    IN RANGE    5
        Given Create volume ${i} with    dataEngine=v2
        And Attach volume ${i} to node 0
        And Wait for volume ${i} healthy
    END

    When Make enginefrontend metadata directory immutable on node 0
    FOR    ${i}    IN RANGE    5
        And Detach volume ${i}
        And Wait for volume ${i} detached
        And Delete volume ${i}
        And Wait for volume ${i} deleted
    END

    When Make enginefrontend metadata directory mutable on node 0
    Then Delete v2 instance manager on node 0
    And Wait for node 0 block disk unschedulable
    And Wait for node 0 block disk schedulable

    When Create volume test-vol with    dataEngine=v2
    And Attach volume test-vol to node 0
    And Wait for volume test-vol healthy
    And Write data to volume test-vol
    Then Check volume test-vol data is intact

V2 Replica Migration Should Not Cause IO Stall
    [Documentation]    issue: https://github.com/longhorn/longhorn/issues/13309
    ...    Test steps:
    ...    1. Create v2 SC with dataLocality: best-effort, numberOfReplicas: 2
    ...    2. Create deployment using the volume, running an fsync writer logging per-write timing
    ...    3. Cordon volume attached node
    ...    4. Delete replica on volume attached node
    ...    5. Wait for volume healthy
    ...    6. Check no IO stall observed (max latency < 3 sec)
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Create storageclass longhorn-test with
    ...    dataEngine=v2
    ...    dataLocality=best-effort
    ...    numberOfReplicas=2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    When Start fsync writer on deployment 0
    And Cordon deployment 0 volume node
    Then Delete replica of deployment 0 volume on volume node
    And Wait for volume of deployment 0 attached and degraded
    And Wait for volume of deployment 0 healthy
    And Assert no IO stall greater than 3 seconds

Test CPU Manager Policy And Data Engine Number Of CPU Cores
    [Documentation]    Verify that Longhorn v2 data engine respects the Kubernetes CPU manager policy.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/13248
    ...
    ...                When the cluster CPU manager policy is `none` (default):
    ...                - Setting data-engine-number-of-cpu-cores must be rejected.
    ...                - data-engine-cpu-mask (e.g. 0x3) is accepted and spdk_tgt honours it.
    ...                - /proc/self/status Cpus_allowed_list is unrestricted (a range like 0-N).
    ...
    ...                When the cluster CPU manager policy is `static`:
    ...                - data-engine-number-of-cpu-cores can be set to 1.
    ...                - spdk_tgt no longer shows the explicit cpu-mask 0x3.
    ...                - Cpus_allowed_list becomes a single CPU index (not a range).
    ...
    ...                When reverting back to `none` policy:
    ...                - v2 instance manager pods should not unexpectedly restart.
    ...                - The v2 deployment should remain healthy.
    ...                - data-engine-number-of-cpu-cores persists and still takes effect after
    ...                  v2 data engine disable/re-enable cycle.
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only runs on v2 data engine
    END

    # --- Phase 1: cpu-manager-policy=none (default) ---

    # Step 2: data-engine-number-of-cpu-cores must be rejected when policy is none
    Then Set setting data-engine-number-of-cpu-cores to 1 will fail

    # Step 3: data-engine-cpu-mask is accepted
    And Setting data-engine-cpu-mask is set to 0x3

    # Step 4 & 5: check spdk_tgt cpu-mask and Cpus_allowed_list via a v2 instance manager pod
    ${im_pod} =    Get v2 instance manager pod name on node 0

    # Step 4: spdk_tgt should be started with the cpu-mask 0x3
    And Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and wait for output
    ...    pgrep -af ^spdk_tgt
    ...    0x3

    # Step 5: Cpus_allowed_list should be unrestricted (range like 0-N) since cpu-manager-policy=none
    And Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and wait for output
    ...    awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status
    ...    ^[0-9]+-[0-9]+$

    # --- Phase 2: switch cluster to cpu-manager-policy=static ---

    # Step 6: SSH into each worker node and set cpu-manager-policy=static, then restart the agent
    When Set cpu-manager-policy to static on all worker nodes

    # Step 7: Wait for the Kubernetes cluster to recover
    Then Wait for k8s cluster ready

    # Step 8: Wait for Longhorn to be fully operational again
    And Wait for longhorn ready

    # Step 9: Now data-engine-number-of-cpu-cores can be set to 1
    And Setting data-engine-number-of-cpu-cores is set to 1

    # Step 10: Wait for the v2 instance managers to restart after the setting change
    And Wait for v2 instance manager pods restarted

    # Step 11 & 12: re-resolve the pod name after the restart, then check cpu pinning
    ${im_pod} =    Get v2 instance manager pod name on node 0

    # Step 11: spdk_tgt should no longer carry the explicit 0x3 cpu-mask
    Then Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and not expect output
    ...    pgrep -af ^spdk_tgt
    ...    0x3

    # Step 12: Cpus_allowed_list should now be a single CPU index (not a range, not a list)
    # because data-engine-cpu-core-number=1 pins the process to exactly one CPU
    And Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and not expect output
    ...    awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status
    ...    ^[0-9]+-[0-9]+$
    # Also verify it is not a comma-separated list of CPUs (e.g. 1,3 or 0,1)
    And Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and not expect output
    ...    awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status
    ...    ^[0-9]+(,[0-9]+)+$

    # Step 13: v2 workload I/O must still work correctly
    And Create storageclass longhorn-test with    dataEngine=v2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Check deployment 0 works

    # --- Phase 3: revert cluster to cpu-manager-policy=none ---

    # Step 14: Revert cpu-manager-policy to none on all worker nodes
    When Set cpu-manager-policy to none on all worker nodes

    # Step 15: Wait for k8s cluster and longhorn ready
    # v2 instance manager pods should not have unexpected restarts after the policy revert
    Then Wait for k8s cluster ready
    And Wait for longhorn ready
    And Check v2 instance manager pods did not restart

    # Step 16: Check the v2 deployment still works after policy revert
    And Check deployment 0 works

    # Step 17: Check data-engine-number-of-cpu-cores still takes effect
    ${im_pod} =    Get v2 instance manager pod name on node 0
    Then Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and not expect output
    ...    pgrep -af ^spdk_tgt
    ...    0x3
    And Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and not expect output
    ...    awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status
    ...    ^[0-9]+-[0-9]+$
    And Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and not expect output
    ...    awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status
    ...    ^[0-9]+(,[0-9]+)+$

    # Step 18: Delete the v2 deployment, block disks and disable v2 data engine
    When Delete deployment 0
    And Delete persistentvolumeclaim 0
    And Disable default block disks on all worker nodes
    And Delete default block disks on all worker nodes
    And Setting v2-data-engine is set to false

    # Step 19: Re-enable v2 data engine, add block disks back, and create a new v2 deployment
    And Enable v2 data engine and add block disks
    And Wait for longhorn ready
    And Create persistentvolumeclaim 1    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 1 healthy

    # Step 20: Check the deployment works
    Then Check deployment 1 works

    # Step 21: Check data-engine-number-of-cpu-cores still takes effect after disable/re-enable cycle
    ${im_pod} =    Get v2 instance manager pod name on node 0
    Then Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and not expect output
    ...    pgrep -af ^spdk_tgt
    ...    0x3
    # Because cpu-manager-policy is no longer static,
    # it will not pin the CPU for the instance manager pod even though
    # the setting data-engine-number-of-cpu-cores is set to a positive value.
    # Therefore, the Cpus_allowed_list will remain 0-3.
    # ref: https://github.com/longhorn/longhorn/issues/13248#issuecomment-4888635428
    And Run command in pod ${LONGHORN_NAMESPACE}/${im_pod} and wait for output
    ...    awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status
    ...    ^[0-9]+-[0-9]+$
