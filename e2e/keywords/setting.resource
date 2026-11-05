*** Settings ***
Documentation    Setting Keywords

Library    ../libs/keywords/setting_keywords.py

*** Keywords ***
Save original registry secret setting
    ${original_registry_secret} =    Get setting registry-secret
    Set Test Variable    ${original_registry_secret}

Get setting ${setting_key}
    ${value} =    get_setting    ${setting_key}
    RETURN    ${value}

Set setting ${setting_key} to ${setting_value} will fail
    Run Keyword And Expect Error    *    update_setting    ${setting_key}    ${setting_value}    retry=False

Setting ${setting_key} is set to ${setting_value}
    update_setting    ${setting_key}    ${setting_value}

Update Setting To Invalid Value And Verify
    [Arguments]    ${setting_key}    ${setting_value}
    ${expected_value} =    get_setting    ${setting_key}
    Run Keyword And Expect Error    *    update_setting    ${setting_key}    ${setting_value}    retry=False
    ${current_value} =    get_setting    ${setting_key}
    Should Be Equal    ${current_value}    ${expected_value}

Update Setting To Valid Value And Verify
    [Arguments]    ${setting_key}    ${setting_value}    ${expected_value}
    update_setting    ${setting_key}    ${setting_value}
    ${value} =    get_setting    ${setting_key}
    Should Be Equal    ${value}    ${expected_value}

Setting ${setting_key} should be ${setting_value}
    ${current_value} =    get_setting    ${setting_key}
    Should Be Equal    ${current_value}    ${setting_value}
