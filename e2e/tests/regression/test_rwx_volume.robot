*** Settings ***
Documentation    RWX Volume Test Cases

Test Tags    regression    rwx

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/host.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/variables.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/setting.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${RWX_UNINTERRUPTIBLE_SLEEP_CHECK_DURATION}    30

*** Test Cases ***

Test RWX Volume Does Not Cause Process Uninterruptible Sleep
    [Tags]    volume
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
    And Check deployment 0 pods not restarted
    And Check deployment 0 pods not recreated

Test ShareManager Status Current Image After Fresh Install
    [Tags]    sharemanager
    [Documentation]    Verify that status.currentImage in the ShareManager CR is correctly set
    ...                after a fresh Longhorn installation.
    ...
    ...                - Issue: https://github.com/longhorn/longhorn/issues/11203
    ...                Steps:
    ...                - 1. Create a RWX storage class and PVC
    ...                - 2. Create a deployment consuming the RWX PVC
    ...                - 3. Wait for the volume to become healthy and the share manager pod to be running
    ...                - 4. Assert that the ShareManager CR status.currentImage matches spec.image
    ...                - 5. Assert that the share manager pod container image matches spec.image
    Given Create Storageclass longhorn-test With    dataEngine=${DATA_ENGINE}
    And Create Persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create Deployment 0 With Persistentvolumeclaim 0
    And Wait For Volume of deployment 0 Healthy
    When Wait For Sharemanager Pod Of deployment 0 Running
    Then Assert Sharemanager Current Image Of deployment 0 Matches Spec Image
    And Assert Sharemanager Pod Container Image Of deployment 0 Matches Spec Image

Test ShareManager Status Current Image After Upgrade
    [Tags]    upgrade    sharemanager
    [Documentation]    Verify that status.currentImage is preserved after a Longhorn upgrade
    ...                and is updated only once the share manager pod is restarted.
    ...
    ...                - Issue: https://github.com/longhorn/longhorn/issues/11203
    ...
    ...                - 1. Uninstall Longhorn and install the stable version
    ...                - 2. Create a RWX PVC and a deployment consuming it
    ...                - 3. Wait for the volume to become healthy and the share manager pod to be running
    ...                - 4. Record the pre-upgrade ShareManager spec.image as the old image
    ...                - 5. Upgrade Longhorn to the custom version
    ...                - 6. Assert that status.currentImage still reflects the old image
    ...                     (share manager pod has not been restarted yet)
    ...                - 7. Scale down the deployment to trigger share manager pod termination
    ...                - 8. Wait for the share manager pod to be fully deleted
    ...                - 9. Scale up the deployment to trigger share manager pod recreation
    ...                - 10. Wait for the new share manager pod to be running
    ...                - 11. Assert that status.currentImage now matches spec.image (new version)
    ...                - 12. Assert that the share manager pod container image matches spec.image
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 volume doesn't support live upgrade
    END

    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    LONGHORN_STABLE_VERSION not set - required for upgrade test
    END

    Given Setting deleting-confirmation-flag Is Set To true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn stable version
    And Create Storageclass longhorn-test With    dataEngine=v1
    And Create Persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create Deployment 0 With Persistentvolumeclaim 0
    And Wait For Volume of deployment 0 Healthy
    And Wait For Sharemanager Pod Of deployment 0 Running

    # Record the pre-upgrade image — status.currentImage and spec.image are equal
    # on a freshly installed system; recording spec.image captures the stable-version image.
    ${old_sharemanager_image} =    Get Sharemanager Spec Image Of deployment 0

    When Upgrade Longhorn To Custom Version

    # The share manager pod has not been restarted yet, so status.currentImage must
    # still reflect the pre-upgrade (old) image.
    Then Assert Sharemanager Current Image Of deployment 0 Is ${old_sharemanager_image}

    # Restart the share manager pod by cycling the workload.
    When Scale Down Deployment 0 To Detach Volume
    And Wait For Sharemanager Pod Of deployment 0 Deleted
    And Scale Up Deployment 0 To Attach Volume
    And Wait For Sharemanager Pod Of deployment 0 Running

    # After the pod is recreated with the new image, status.currentImage must reflect
    # spec.image (the post-upgrade image).
    Then Assert Sharemanager Current Image Of deployment 0 Matches Spec Image
    And Assert Sharemanager Pod Container Image Of deployment 0 Matches Spec Image

