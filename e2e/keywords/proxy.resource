*** Settings ***
Library    ../libs/keywords/proxy_keywords.py

*** Keywords ***
Deploy squid proxy server
    [Documentation]    Deploy Squid proxy server
    deploy_squid_proxy

Remove squid proxy server
    [Documentation]    Remove Squid proxy server
    remove_squid_proxy

Deploy Kyverno policy
    [Documentation]    Install Kyverno v1.12.0 and deploy proxy injection policy
    install_kyverno
    deploy_kyverno_proxy_policy

Remove Kyverno policy
    [Documentation]    Remove proxy injection policy and uninstall Kyverno
    remove_kyverno_proxy_policy
    uninstall_kyverno

Check backing image ${backing_image_name} data source pod has proxy env vars
    ${result} =    verify_proxy_env_in_backing_image_data_source_pod    ${backing_image_name}
    Should Be True    ${result}    Proxy env vars should be injected by Kyverno
