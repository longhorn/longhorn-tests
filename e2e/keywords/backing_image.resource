*** Settings ***
Documentation    Backing Image Keywords

Library    ../libs/keywords/backing_image_keywords.py
Library    ../libs/keywords/node_keywords.py
Library    Collections
Library    OperatingSystem

*** Keywords ***
Create backing image ${backing_image_name} with
    [Arguments]    &{config}
    create_backing_image    ${backing_image_name}    &{config}

Verify all disk file status of backing image ${backing_image_name} are ready
    all_disk_file_status_are_ready    ${backing_image_name}

Wait for all disk file status of backing image ${backing_image_name} are ready
    wait_for_all_disk_file_status_are_ready    ${backing_image_name}

Verify disk file status of backing image ${backing_image_name} are expected
    [Arguments]    &{config}
    disk_file_status_match_expected    ${backing_image_name}    &{config}

Wait for disk file status of backing image ${backing_image_name} are expected
    [Arguments]    &{config}
    wait_for_disk_file_status_match_expected    ${backing_image_name}    &{config}
Wait for all disk file status of backing image ${backing_image_name} are failed
    wait_all_disk_file_status_are_at_state    ${backing_image_name}    failed

Wait for all disk file status of backing image ${backing_image_name} are failed-and-cleanup
    wait_all_disk_file_status_are_at_state    ${backing_image_name}    failed-and-cleanup

Verify clean up backing image ${backing_image_name} from a disk will fail
    Run Keyword And Expect Error    *    clean_up_backing_image_from_a_random_disk    ${backing_image_name}

Verify delete backing image ${backing_image_name} will fail
    Run Keyword And Expect Error    *    delete_backing_image    ${backing_image_name}

Clean up backing image ${backing_image_name} from a disk
    clean_up_backing_image_from_a_random_disk    ${backing_image_name}

Delete backing image ${backing_image_name}
    delete_backing_image    ${backing_image_name}

Delete backing image managers and wait for recreation
    delete_all_backing_image_managers_and_wait_for_recreation

Wait backing image managers running
    wait_all_backing_image_managers_running

No backimg image data source pod exist
    ${ds_count}=     get_backing_image_data_source_pod_count
    Should Be Equal    ${ds_count}     ${0}

Wait backimg image ${backing_image_name} data source pod created
    ${creation_time} =    wait_backing_image_data_source_pod_created    ${backing_image_name}
    [Return]    ${creation_time}

Wait backing image data source pod terminated
    wait_for_no_backing_image_data_source_pod_exist

Disk file message of backing image ${backing_image_name} should contain ${message}
    check_disk_file_map_contain_specific_message    ${backing_image_name}    ${message}

Remove backing image ${backing_image_name} files and set immutable on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    remove_backing_image_files_on_node    ${backing_image_name}    ${node_name}
    set_backing_image_folder_immutable_on_node    ${backing_image_name}    ${node_name}

Unset backing image ${backing_image_name} folder immutable on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    set_backing_image_folder_mutable_on_node    ${backing_image_name}    ${node_name}

Verify backing image manager log on node ${node_id} contain ${expect_log} after test start
    ${node_name} =    get_node_by_index    ${node_id}
    ${pod_name} =    get_backing_image_manager_pod_on_node    ${node_name}
    Log    ${pod_name}
    verify_pod_log_after_time_contains    ${pod_name}    ${expect_log}    ${test_start_time}

Wait for backing image manager on node ${node_id} unknown
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_backing_image_manager_on_node_unknown    ${node_name}

Wait for backing image manager on node ${node_id} terminated
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_backing_image_manager_on_node_terminated    ${node_name}

Backing image ${bi_name} should not have the removed disk in its DiskFileSpecMap
    # ${recorded_disk_uuid} come from `Record node ${node_id} default disk uuid` in node.resource
    ${disk_uuids} =    get_backing_image_disk_uuids    ${bi_name}
    List Should Not Contain Value    ${disk_uuids}    ${recorded_disk_uuid}
Download backing image ${backing_image_name}
    [Arguments]    &{config}
    ${download_bi_checksum} =    download_backing_image    ${backing_image_name}     &{config}
    Set Test Variable    ${download_bi_checksum}

Check downloaded backing image ${backing_image_name} data matches volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${sha512_checksum} =    get_volume_sha512sum    ${volume_name}
    Should Be Equal    ${download_bi_checksum}    ${sha512_checksum}

Check downloaded backing image ${backing_image_name} data matches source backingimage
    ${bi_checksum} =  get_backing_image_checksum    ${backing_image_name}
    Should Be Equal    ${download_bi_checksum}    ${bi_checksum}

Wait backimg image ${backing_image_name} download complete
    ${download_bi_checksum} =    wait_for_async_download_complete    ${backing_image_name}
    Set Test Variable    ${download_bi_checksum}

Check backing image ${backing_image_name} download file checksum matches
    ${bi_checksum} =  get_backing_image_checksum    ${backing_image_name}
    Should Be Equal    ${download_bi_checksum}    ${bi_checksum}

Get backing image ${backing_image_name} virtual size
    ${virtual_size} =    get_backing_image_virtual_size    ${backing_image_name}
    [Return]    ${virtual_size}
