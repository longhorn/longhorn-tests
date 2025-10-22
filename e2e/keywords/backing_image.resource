*** Settings ***
Documentation    Backing Image Keywords

Library    ../libs/keywords/backing_image_keywords.py
Library    ../libs/keywords/node_keywords.py

*** Keywords ***
Create backing image ${backing_image_name} with
    [Arguments]    &{config}
    create_backing_image    ${backing_image_name}    &{config}

Verify all disk file status of backing image ${backing_image_name} are ready
    all_disk_file_status_are_ready    ${backing_image_name}

Wait for all disk file status of backing image ${backing_image_name} are ready
    wait_for_all_disk_file_status_are_ready    ${backing_image_name}

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

Wait backimg image data source pod terminated
    ${ds_count}=     get_backing_image_data_source_pod_count
    Should Be Equal    ${ds_count}     ${0}

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
