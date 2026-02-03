*** Settings ***
Documentation    RWX Volume Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/variables.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***

Test RWX Volume Does Not Cause Process Uninterruptible Sleep
    [Tags]    volume    rwx
    [Documentation]    Test that RWX volume with multiple pods writing to the same file
    ...                does not cause processes to enter uninterruptible sleep state.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11907
    ...
    ...                Steps:
    ...                1. Create a RWX volume
    ...                2. Create a deployment with 2 replicas, both writing to the same file
    ...                3. Wait for pods to run and perform I/O for several minutes
    ...                4. Check that no processes are in uninterruptible sleep state (Ds+)
    ...                5. Verify that the volume remains accessible and workload continues

    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0 with 2 replicas for rwx file writing
    And Wait for volume of deployment 0 healthy

    # Let the workload run for a period to allow the issue to potentially manifest
    # The issue description mentions it takes several minutes to reproduce
    When Sleep    180

    # Check that no processes are in uninterruptible sleep state
    # We check for processes related to the writing operation (echo command)
    Then Check no uninterruptible sleep processes on deployment 0 nodes    pattern=echo

    # Verify the deployment is still running and accessible
    And Wait for deployment 0 pods stable
    And Check deployment 0 works
