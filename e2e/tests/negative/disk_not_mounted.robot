*** Settings ***
Documentation    Disk Not Mounted Test Cases

Test Tags    negative    disk

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource
Resource    ../keywords/io.resource
Resource    ../keywords/host.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Disk Keeps Its Identity When Data Path Is Not Mounted
    [Documentation]    Verify that a filesystem disk whose data path is temporarily not mounted
    ...                (e.g. a slow-to-mount device after a node reboot) keeps its recorded disk UUID,
    ...                Longhorn writes nothing into the unmounted path, and the failed replica is reused
    ...                once the device is mounted again.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/14102
    ...
    ...                Test Flow:
    ...                1. Add a filesystem disk to node 0 (backed by a Longhorn volume) as its only
    ...                   schedulable disk, and record its disk UUID.
    ...                2. Create a 3 replica volume attached to node 1, write data, and record the replica on node 0.
    ...                3. Unmount the data path. The replica fails and the volume becomes degraded.
    ...                4. The disk becomes not ready, keeps its disk UUID, and the path stays empty.
    ...                5. Mount the device again. The disk becomes ready with the same UUID, the same replica
    ...                   is reused, and the data is intact.
    ...
    ...                Not covered: asserting that only a delta is transferred (no keyword exists yet).
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Test only validates filesystem disks, which are v1 only
    END
    ${disk_name} =    Generate random disk name    prefix=unmount-disk
    ${mount_path} =    Set Variable    /var/lib/longhorn/${disk_name}

    Given Create 1 Gi filesystem type disk ${disk_name} on node 0
    And Disable node 0 default disk
    And Wait for disk ${disk_name} on node 0 schedulable
    And Record disk ${disk_name} uuid on node 0

    And Create volume 0 with    size=100Mi    numberOfReplicas=3    dataEngine=v1
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Write 50 Mi data to volume 0
    And Record volume 0 replica name on node 0

    When Force unmount dm disk at ${mount_path} on node 0
    Then Wait for volume 0 degraded
    And Wait for disk ${disk_name} on node 0 Ready condition to be False    DiskFilesystemChanged
    And Check disk ${disk_name} on node 0 still has the recorded uuid
    And Check unmounted disk path ${mount_path} on node 0 stays empty

    When Run command on node    0    mount /dev/longhorn/${disk_name} ${mount_path}
    Then Wait for disk ${disk_name} on node 0 Ready condition to be True
    And Check disk ${disk_name} on node 0 still has the recorded uuid
    And Wait for volume 0 healthy
    And Check volume 0 replica reused on node 0
    And Check volume 0 data is intact
