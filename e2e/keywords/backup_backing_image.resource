*** Settings ***
Documentation    Backup Backing Image Keywords

Library    ../libs/keywords/backup_backing_image_keywords.py

*** Keywords ***
Create backup backing image ${backup_backing_image_name} for backing image ${backing_image_name}
    create_backup_backing_image    ${backing_image_name}    ${backup_backing_image_name}

Wait for backing image backup ${backup_backing_image_name} ready
    wait_for_backup_backing_image_ready    ${backup_backing_image_name}

Wait for backing image backup for backing image ${backing_image_name} ready
    wait_for_backup_backing_image_for_backing_image_ready    ${backing_image_name}
