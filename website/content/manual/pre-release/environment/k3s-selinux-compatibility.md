---
title: Compatibility with k3s and SELinux
---
1. Set up a node with `CentOS` and make sure that the output of `sestatus` indicates that `SELinux` is enabled and set to `Enforcing`.
2. Run the `k3s` installation script.
3. Install `Longhorn`.
4. The system should come up successfully. The logs of the `Engine Image` pod should only say `installed`, and the system should be able to deploy a `Volume` successfully from the UI.

Note: There appears to be some problems with running `k3s` on `CentOS`, presumably due to the `firewalld` rules. This seems to be reported in rancher/k3s#977. I ended up disabling `firewalld` with `systemctl stop firewalld` in order to get `k3s` working.
