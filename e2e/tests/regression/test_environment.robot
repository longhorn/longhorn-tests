*** Settings ***
Documentation    Environment Test Cases

Test Tags    regression    environment

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource

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
    And Restart all worker nodes

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
    And Restart all worker nodes
