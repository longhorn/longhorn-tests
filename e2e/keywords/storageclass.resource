*** Settings ***
Documentation    Storageclass Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/storageclass_keywords.py

*** Keywords ***
Create storageclass ${storageclass_name} with
    [Arguments]    &{config}
    create_storageclass   ${storageclass_name}    &{config}


Delete storageclass ${storageclass_name}
    delete_storageclass    ${storageclass_name}

Set storageclass ${storageclass_name} as default
    set_storageclass_default_state    ${storageclass_name}    ${True}

Remove default from storageClass ${storageclass_name}
    set_storageclass_default_state    ${storageclass_name}    ${False}

Assert storageClass ${storageclass_name} is default storageclass
    assert_storageclass_is_default    ${storageclass_name}    ${True}
