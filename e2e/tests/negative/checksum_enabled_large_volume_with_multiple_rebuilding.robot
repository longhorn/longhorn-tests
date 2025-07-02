*** Settings ***
Documentation    Checksum enabled large volume with multiple rebuilding
...              - Issue: https://github.com/longhorn/longhorn/issues/4210

Test Tags    manual    negative    longhorn-4210


Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/snapshot.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Verify Large Volume Data Integrity During Replica Rebuilding with Recurring Jobs
    [Documentation]    -- Manual test plan --
    ...                - Enable the setting `Snapshot Data Integrity` and `Immediate Snapshot Data Integrity Check After Creating a Snapshot`
    ...                - Create a 50 Gi volume. write around 30 Gi data into it.
    ...                - Create a recurring job of snapshot & backup.
    ...                - Delete a replica and wait for the replica rebuilding.
    ...                - Check volume data is intact
    Given Set setting snapshot-data-integrity to enabled
    And Set setting snapshot-data-integrity-immediate-check-after-snapshot-creation to true
    And Create volume 0 with    size=50Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Write 30 GB data to volume 0
    And Create recurringjob for volume 0 with    task=backup    cron=*/3 * * * *
    And Create recurringjob for volume 0 with    task=snapshot    cron=*/3 * * * *
    When Delete volume 0 replica on node 0
    Then Wait until volume 0 replica rebuilding completed on node 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Compare Large Volume Rebuild Performance Before and After Enabling Snapshot Integrity
    [Documentation]    -- Manual test plan --
    ...                - Create a 50 Gi volume. write around 30 Gi data into it.
    ...                - Fail one of the replica (node down or network partition) and wait for the replica becomes failed.
    ...                - Power on node (or recover network)
    ...                - Rebuilding (record rebuild time)
    ...                - Enable `Snapshot Data Integrity` and `Immediate Snapshot Data Integrity Check After Creating a Snapshot`
    ...                - Create a 50 Gi volume. write around 30 Gi data into it.
    ...                - Take a snapshot
    ...                - Wait for N minutes. Or check if the snapshot checksum file is generated
    ...                - Fail one of the replica (node down or network partition) and wait for the replica becomes failed.
    ...                - Power on node (or recover network)
    ...                - Rebuilding (expect faster than without the two settings enabled)
    Given Create volume 0 with    size=50Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write 30 GB data to volume 0
    When Power off node 1 for 4 mins

    Then Wait for longhorn ready
    And Wait until volume 0 replica rebuilding started on node 1
    ${rebuild_time}=    Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy
    
    When Set setting snapshot-data-integrity to enabled
    And Set setting snapshot-data-integrity-immediate-check-after-snapshot-creation to true
    And Create snapshot 0 of volume 0
    And Validate snapshot 0 is in volume 0 snapshot list
    # Longhorn creates a snapshot A (data size 30 GiB) without a checksum during the first rebuild.
    # After creating snapshot 0 for volume 0, the snapshot A must be purged.
    # Once purged, snapshot 0 for volume 0 will generate a new checksum.
    And Purge volume 0 snapshot
    # The timeout for validating the snapshot checksum is set to 1200 seconds 
    # because this test involves writing 30 GB of data to the volume. 
    # Based on observations on AWS, generating the snapshot checksum 
    # in such cases can take up to approximately 18 minutes. 
    # If needed, this value can be adjusted further based on future test results or requirements.
    And Validate snapshot 0 checksum of volume 0 is calculated within 1200 seconds
    And Power off node 1 for 4 mins

    Then Wait for longhorn ready
    ${2nd_rebuild_time}=    Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy
    ${status}=    Evaluate    ${2nd_rebuild_time} <= ${rebuild_time}
    Run Keyword If    not ${status}
    ...    Fail    The 2nd replica rebuilding time ${2nd_rebuild_time}s > 1st ${rebuild_time}s
