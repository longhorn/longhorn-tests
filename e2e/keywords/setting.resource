*** Settings ***
Documentation    Setting Keywords

Library    ../libs/keywords/setting_keywords.py

*** Keywords ***
Set setting ${setting_key} to ${setting_value}
    update_setting    ${setting_key}    ${setting_value}

Set setting ${setting_key} to ${setting_value} will fail
    Run Keyword And Expect Error    *    update_setting    ${setting_key}    ${setting_value}    retry=False