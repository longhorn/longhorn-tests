*** Settings ***
Documentation    Environment Test Cases

Test Tags    regression    environment

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test IPv4 Only Environment
    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    # add ipv6.disable=1 to GRUB_CMDLINE_LINUX
    # then update grub
    Given Run command on node    0
    ...    sudo sed -i 's/^GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="ipv6.disable=1 /' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    And Run command on node    1
    ...    sudo sed -i 's/^GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="ipv6.disable=1 /' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    And Run command on node    2
    ...    sudo sed -i 's/^GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="ipv6.disable=1 /' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    # reboot to make updated grub take effect
    And Reboot node 0
    And Reboot node 1
    And Reboot node 2

    When Install Longhorn
    Then Wait for Longhorn components all running

    # re-enable ipv6 by removing ipv6.disable=1 in GRUB_CMDLINE_LINUX
    # then update grub
    And Run command on node    0
    ...    sudo sed -i 's/ipv6\.disable=1 //g' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    And Run command on node    1
    ...    sudo sed -i 's/ipv6\.disable=1 //g' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    And Run command on node    2
    ...    sudo sed -i 's/ipv6\.disable=1 //g' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    # reboot to make reverted grub take effect
    And Reboot node 0
    And Reboot node 1
    And Reboot node 2

Test RWX Fast Failover In Non-default Longhorn Namespace
    [Tags]    non-default-namespace
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12244
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' != 'manifest' and '${LONGHORN_INSTALL_METHOD}' != 'helm'
        Skip    Unsupported install method: ${LONGHORN_INSTALL_METHOD}
    END

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn    longhorn_namespace=longhorn-custom
    And Wait for Longhorn components all running
    And Setting rwx-volume-fast-failover is set to true

    Then Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Wait for deployment 0 pods stable
    And Write 128 MB data to file data.txt in deployment 0
    And Check deployment 0 data in file data.txt is intact

    And Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn
    And Wait for Longhorn components all running
