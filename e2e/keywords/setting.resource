*** Settings ***
Documentation    Longhorn setting related keywords resources

Library    ../libs/steps.py


*** Keywords ***
Update the ${setting_name} setting to ${setting_value}
    update_setting_custom_resource   ${setting_name}   ${setting_value}
