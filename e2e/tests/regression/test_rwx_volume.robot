*** Settings ***
Documentation    RWX Volume Test Cases

Test Tags    regression    rwx

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/host.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/metrics.resource
Resource    ../keywords/node.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
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
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    When Wait for sharemanager pod of deployment 0 running
    Then Assert sharemanager current image of deployment 0 matches spec image
    And Assert sharemanager pod container image of deployment 0 matches spec image

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

    Given setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn stable version
    And Create storageclass longhorn-test with    dataEngine=v1
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Wait for sharemanager pod of deployment 0 running

    # Record the pre-upgrade image — status.currentImage and spec.image are equal
    # on a freshly installed system; recording spec.image captures the stable-version image.
    ${old_sharemanager_image} =    get sharemanager spec image of deployment 0

    When Upgrade Longhorn to custom version

    # The share manager pod has not been restarted yet, so status.currentImage must
    # still reflect the pre-upgrade (old) image.
    Then Assert sharemanager current image of deployment 0 is ${old_sharemanager_image}

    # Restart the share manager pod by cycling the workload.
    When Scale down deployment 0 to detach volume
    And Wait for sharemanager pod of deployment 0 deleted
    And Scale up deployment 0 to attach volume
    And Wait for sharemanager pod of deployment 0 running

    # After the pod is recreated with the new image, status.currentImage must reflect
    # spec.image (the post-upgrade image).
    Then Assert sharemanager current image of deployment 0 matches spec image
    And Assert sharemanager pod container image of deployment 0 matches spec image

Test RWX Failover And Auto Salvage When Volume Is Faulted
    [Tags]    rwx-fast-failover    node-down
    [Documentation]    If the volume is faulted, we don't need to have RWX fast failover
    ...    Issue: https://github.com/longhorn/longhorn/issues/9089
    ...
    ...    1. Enable RWX fast failover setting
    ...    2. Deploy a workload which uses a RWX PVC
    ...    3. Reduce the number of replicas to 1. Delete 2 replicas not on the same node as the share manager pod
    ...    4. Record the CPU usage
    ...    5. Turn off the node of the share manager pod
    ...    6. Volume stay in faulted. Share manager pod is recreated but then error and deleted. the CPU usage is still small
    ...    7. Turn on the node of the share-manager pod
    ...    8. Volume is salvaged and should not be stuck in auto-salvage loop forever. Share manager pod is recreated and become running. CPU usage still is small
    Given Setting rwx-volume-fast-failover is set to true
    And Setting auto-salvage is set to true
    And Create storageclass longhorn-test with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Create statefulset 0     volume_type=RWX    sc_name=longhorn-test
    And Wait for volume of statefulset 0 healthy
    And Update volume of statefulset 0 replica count to 1
    And Delete replica of statefulset 0 volume on all replica node
    And Write 1 MB data to file data.bin in statefulset 0
    And Get Longhorn components resource usage

    When Power off volume node of statefulset 0
    Then Check volume of statefulset 0 kept in faulted
    And Check Longhorn components resource usage

    When Power on off nodes
    Then Wait for volume of statefulset 0 healthy
    And Check statefulset 0 data in file data.bin is intact
    And Wait for sharemanager pod of statefulset 0 running
    And Check Longhorn components resource usage

Test ShareManager NodeSelector Helm Chart Parameter
    [Tags]    sharemanager    uninstall
    [Documentation]    Verify that the persistence.shareManagerNodeSelector helm chart value
    ...                is propagated to the default "longhorn" storage class, and that it
    ...                causes the share manager pod to be scheduled only onto the labelled node.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/9324
    ...
    ...                Manual test steps:
    ...                1. Install Longhorn via Helm with the following values:
    ...                   persistence.shareManagerNodeSelector.enable=true
    ...                   persistence.shareManagerNodeSelector.selector="storage:true"
    ...                2. Check the setting is applied to the default storage class "longhorn":
    ...                   parameters.shareManagerNodeSelector should be "storage:true"
    ...                3. Label a node with storage=true
    ...                4. Create a workload using RWX PVC
    ...                5. Check share manager pod is running on the labelled node
    ${LONGHORN_INSTALL_METHOD} =    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' != 'helm'
        Skip    This test only runs when LONGHORN_INSTALL_METHOD is helm
    END

    Given setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn
    ...    custom_cmd=yq -i '.persistence.shareManagerNodeSelector.enable = true | .persistence.shareManagerNodeSelector.selector = "storage:true"' values.yaml

    Then Run command and expect output
    ...    kubectl get storageclass longhorn -o jsonpath='{.parameters.shareManagerNodeSelector}'
    ...    storage:true

    Given Label node 2 with storage=true
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    Then Wait for sharemanager pod of deployment 0 to be running on node ${NODE_2}

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn

Test ShareManager Tolerations Helm Chart Parameter
    [Tags]    sharemanager    uninstall
    [Documentation]    Verify that the persistence.shareManagerTolerations helm chart value
    ...                is propagated to the default "longhorn" storage class, and that it
    ...                causes the share manager pod to only tolerate the taint on the node
    ...                that has a matching toleration, and not be scheduled onto other
    ...                tainted nodes.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/9324
    ...
    ...                Manual test steps:
    ...                1. Install Longhorn via Helm with the following values:
    ...                   persistence.shareManagerTolerations.enable=true
    ...                   persistence.shareManagerTolerations.tolerations="lh-share-manager=allowed:NoSchedule"
    ...                2. Check the setting is applied to the default storage class "longhorn":
    ...                   parameters.shareManagerTolerations should be "lh-share-manager=allowed:NoSchedule"
    ...                3. Taint NODE_0 and NODE_1 with lh-share-manager=blocked:NoSchedule
    ...                4. Taint NODE_2 with lh-share-manager=allowed:NoSchedule
    ...                5. Create a workload using RWX PVC
    ...                6. Check share manager pod is running on NODE_2, and not on NODE_0 or NODE_1
    ${LONGHORN_INSTALL_METHOD} =    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' != 'helm'
        Skip    This test only runs when LONGHORN_INSTALL_METHOD is helm
    END

    Given setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn
    ...    custom_cmd=yq -i '.persistence.shareManagerTolerations.enable = true | .persistence.shareManagerTolerations.tolerations = "lh-share-manager=allowed:NoSchedule"' values.yaml

    Then Run command and expect output
    ...    kubectl get storageclass longhorn -o jsonpath='{.parameters.shareManagerTolerations}'
    ...    lh-share-manager=allowed:NoSchedule

    TRY
        Given Taint node 0 with lh-share-manager=blocked:NoSchedule
        And Taint node 1 with lh-share-manager=blocked:NoSchedule
        And Taint node 2 with lh-share-manager=allowed:NoSchedule

        And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn
        And Create deployment 0 with persistentvolumeclaim 0
        ...    tolerations=[{"key": "lh-share-manager", "operator": "Equal", "value": "allowed", "effect": "NoSchedule"}]
        And Wait for volume of deployment 0 healthy

        Then Wait for sharemanager pod of deployment 0 to be running on node ${NODE_2}
    FINALLY
        # Clean up the lh-share-manager taints added by this test, otherwise the
        # longhorn-uninstall helm pre-delete hook job pod (which has no
        # toleration for the lh-share-manager taint) would be stuck Pending
        # forever since all worker nodes are tainted.
        And Taint node 0 with lh-share-manager=blocked:NoSchedule-
        And Taint node 1 with lh-share-manager=blocked:NoSchedule-
        And Taint node 2 with lh-share-manager=allowed:NoSchedule-
        And Setting deleting-confirmation-flag is set to true
        And Uninstall Longhorn
        And Check Longhorn CRD removed
        And Install Longhorn
    END
