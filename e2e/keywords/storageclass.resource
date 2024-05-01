*** Settings ***
Documentation    Storageclass Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/storageclass_keywords.py

*** Keywords ***
Create storageclass ${storageclass_id} with
    [Arguments]    &{config}
    ${storageclass_name} =    generate_name_with_suffix    storageclass    ${storageclass_id}
    create_storageclass   ${storageclass_name}    &{config}