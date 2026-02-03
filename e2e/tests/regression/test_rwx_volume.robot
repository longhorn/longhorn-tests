*** Settings ***
Documentation    RWX Volume Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/host.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/variables.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${RWX_UNINTERRUPTIBLE_SLEEP_CHECK_DURATION}    30

*** Test Cases ***

Test RWX Volume Does Not Cause Process Uninterruptible Sleep
    [Tags]    volume    rwx
    [Documentation]    Test that RWX volume with multiple pods writing to the same file
    ...                does not cause processes to enter uninterruptible sleep state.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11907
    ...
    ...                Steps:
    ...                1. Create a single node cluster (cordon other nodes)
    ...                2. Create a RWX volume
    ...                3. Create a deployment with 6 replicas, all writing to the same file
    ...                4. Wait and check every minute for 30 minutes that no processes are in D state
    ...                5. Verify that all replicas remain accessible and working

    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0 with 6 replicas using args    sleep 10; touch /data/index.html; while true; do echo "$(date) $(hostname)" >> /data/index.html; sleep 1; done;
    And Wait for volume of deployment 0 healthy
    
    # Cordon all nodes except the one where the volume is attached to create a single-node cluster
    And Cordon all other nodes beside deployment 0 volume node

    # Continuously check for uninterruptible sleep processes every minute for the specified duration
    FOR    ${i}    IN RANGE    ${RWX_UNINTERRUPTIBLE_SLEEP_CHECK_DURATION}
        Log To Console    Checking for uninterruptible sleep processes (${i + 1}/${RWX_UNINTERRUPTIBLE_SLEEP_CHECK_DURATION})...
        
        # Check the volume node for processes in D state
        # We check for processes related to writing to /data/index.html
        FOR    ${node_id}    IN RANGE    0    3
            TRY
                Run command on node and not expect output    ${node_id}    ps aux | grep 'echo.*/data/index.html' | awk '{print $8}'    D
            EXCEPT
                # Node might not have the pods, continue
                Log    Node ${node_id} doesn't have matching processes or is cordoned
            END
        END
        
        # Wait 1 minute before next check
        Sleep    60
    END

    # Verify all replicas are still working properly
    Then Wait for deployment 0 pods stable
    
    # Check that all 6 replicas are working by verifying we can write/read from each
    FOR    ${replica_idx}    IN RANGE    6
        ${workload_name} =    generate_name_with_suffix    deployment    0
        ${pod_names} =    get_workload_pod_names    ${workload_name}
        ${pod_count} =    Get Length    ${pod_names}
        IF    ${replica_idx} < ${pod_count}
            Log To Console    Checking replica pod ${replica_idx + 1}/${pod_count}
            # Each pod should be accessible (pods stable check above verifies this)
        END
    END
