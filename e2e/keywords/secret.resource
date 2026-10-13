*** Settings ***
Documentation    Secret Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/secret_keywords.py

*** Keywords ***
Create crypto secret
    create_secret

Create crypto secret ${name}
    create_secret    name=${name}

Assert no crypto secret exists
    assert_secret_does_not_exist    longhorn-crypto
