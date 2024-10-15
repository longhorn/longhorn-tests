*** Settings ***
Documentation    Backing Image Keywords

Library    ../libs/keywords/backing_image_keywords.py

*** Keywords ***
Create backing image ${backing_image_name} with
    [Arguments]    &{config}
    create_backing_image    ${backing_image_name}    &{config}

Verify all disk file status of backing image ${backing_image_name} are ready
    all_disk_file_status_are_ready    ${backing_image_name}

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
