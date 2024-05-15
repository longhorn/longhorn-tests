*** Settings ***
Documentation    Storageclass Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/storageclass_keywords.py

*** Keywords ***
Create storageclass ${storageclass_name} with
    [Arguments]    &{config}
    create_storageclass   ${storageclass_name}    &{config}
