*** Settings ***
Documentation    Negative Test Cases for Volume Cloning

Test Tags    negative    clone

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
# Enough data that each copy runs long enough to be stopped on purpose.
${CLONE_DATA_SIZE_MB}    4096
# After attempts 1 to 4, a retry waits 30s, 1m, 2m and then 4m. A copy is seen as failed
# about 2 minutes after its source replica is lost. So attempt 4 is the first attempt that
# surely fails before its retry is due.
${CLONE_FAILED_ATTEMPTS}    4

*** Test Cases ***
Test Full-Copy Clone Is Retried After Its Copy Fails
    [Tags]    v2    longhorn-14530
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/14530
    ...    A full-copy clone whose copy fails must be retried until it completes.
    ...
    ...    The clone used to stay failed for good, for two reasons:
    ...    - The clone target replica kept the error of the failed copy when it started again.
    ...      Each retry read that old error back and failed without copying anything.
    ...    - A failed clone did not ask for its source volume to be attached for the retry.
    ...      When the clone failed before its retry was due, and nothing else used the source,
    ...      the source stayed detached and the retry never started.
    ...
    ...    1. Tag node 0 clone-source and node 1 clone-target.
    ...    2. Create volume 0 with 1 replica on node 0. Write 4 GiB of data, then detach it.
    ...    3. Create volume 1 as a full-copy clone of volume 0, with 1 replica on node 1.
    ...    4. For clone attempts 1 to 4: wait until the attempt copies data, delete the v2
    ...       instance manager on node 0, then wait until the attempt fails.
    ...       Every retry must copy data again, not just report the old error.
    ...    5. Attempt 4 fails before its retry is due, so volume 0 detaches.
    ...       When the retry is due, volume 0 must be attached again, and the clone completes.
    ...    6. Attach volume 1 and check that its data matches the data written to volume 0.
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    ${source_node_selector} =    Create List    clone-source
    ${target_node_selector} =    Create List    clone-target
    Given Set node 0 tags    clone-source
    And Set node 1 tags    clone-target
    And Create volume 0 with    size=5Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    ...    nodeSelector=${source_node_selector}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write ${CLONE_DATA_SIZE_MB} MB data to volume 0 at offset 0
    And Detach volume 0 from node 0
    And Wait for volume 0 detached

    When Create volume 1 from volume 0    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    ...    nodeSelector=${target_node_selector}
    FOR    ${attempt}    IN RANGE    1    ${{ ${CLONE_FAILED_ATTEMPTS} + 1 }}
        And Wait for volume 1 clone attempt ${attempt} copying data
        And Delete ${DATA_ENGINE} instance manager on node 0
        And Wait for volume 1 clone attempt ${attempt} failed
    END

    # The last attempt failed before its retry was due. Nothing else uses volume 0, so it detaches.
    Then Wait for volume 0 detached
    # When the retry is due, volume 0 must be attached again for the clone.
    And Wait for volume 0 attached
    And Wait for volume 1 clone status to be completed

    When Wait for volume 1 detached
    And Attach volume 1 to node 1
    And Wait for volume 1 healthy
    Then Check ${CLONE_DATA_SIZE_MB} MB data of volume 1 at offset 0 matches recorded data of volume 0
