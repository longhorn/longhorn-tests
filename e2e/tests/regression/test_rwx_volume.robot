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
    ...                does not cause processes to get stuck in uninterruptible sleep state.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11907
    ...
    ...                Steps:
    ...                1. Create a single node cluster (cordon nodes 0 and 1)
    ...                2. Create a RWX volume
    ...                3. Create a deployment with 6 replicas, all writing to the same file
    ...                4. Check every minute for 30 minutes that no processes are stuck in D state
    ...                   (A process is considered stuck if it remains in D state for 30+ seconds)
    ...                5. Verify that all replicas remain accessible and working

    # Create a single-node environment by cordoning nodes 0 and 1
    Given Cordon node 0
    And Cordon node 1
    
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    nfsOptions=vers=4.0,noresvport,softerr,timeo=600,retrans=5    numberOfReplicas=1
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0    replicaset=6    args=sleep 10; touch /data/index.html; while true; do echo "$(date) $(hostname)" >> /data/index.html; sleep 1; done;
    And Wait for volume of deployment 0 healthy

    # Continuously check for uninterruptible sleep processes every minute for the specified duration
    ${UNEXPECTED_D_STATE} =    Set Variable    ${False}
    ${i} =    Set Variable    ${0}
    WHILE    ${i} < ${RWX_UNINTERRUPTIBLE_SLEEP_CHECK_DURATION}
        ${current_check} =    Evaluate    ${i} + 1
        Log To Console    Checking for uninterruptible sleep processes (${current_check}/${RWX_UNINTERRUPTIBLE_SLEEP_CHECK_DURATION})...
        
        # Check node 2 (the only schedulable node) for processes in D state
        # We check for processes related to writing to /data/index.html
        ${has_d_state} =    Run command on node 2 and get output    pgrep -f 'echo.*/data/index.html' | xargs -r ps --no-headers -o pid,stat,command -p    D
        
        IF    ${has_d_state}
            Log To Console    D-state process detected, rechecking to see if stuck...
            ${UNEXPECTED_D_STATE} =    Set Variable    ${True}
            # Don't increment i, recheck on next iteration
        ELSE
            ${UNEXPECTED_D_STATE} =    Set Variable    ${False}
            ${i} =    Evaluate    ${i} + 1
        END
        
        # Wait 1 minute before next check
        Sleep    60
    END
    
    # If we found D-state in the last check, it's considered stuck
    IF    ${UNEXPECTED_D_STATE}
        ${error_output} =    Run command on node 2 and get output string    pgrep -f 'echo.*/data/index.html' | xargs -r ps --no-headers -o pid,stat,command -p
        Log To Console    Process stuck in D-state detected: ${error_output}
        Sleep    ${RETRY_COUNT}
        Fail    Process stuck in uninterruptible sleep (D state) detected on node 2: ${error_output}
    END

    # Verify all replicas are still working properly
    Then Wait for deployment 0 pods stable
    And Check all deployment 0 replica pods are working
