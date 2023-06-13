#!/bin/bash

sudo sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
  sudo setenforce  1
  # k3s-selinux does not have the same fix applied as rke2-selinux.
  echo '(allow iscsid_t self (capability (dac_override)))' > local_longhorn.cil && sudo semodule -vi local_longhorn.cil
elif [[  ${selinux_mode} == "permissive" ]]; then
  sudo setenforce  0
fi

# Do not arbitrarily run "dnf update", as this will effectively move us up to the latest minor release.
sudo dnf group install -y "Development Tools"
sudo dnf install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

if [ -b "/dev/xvdh" ]; then
  sudo mkfs.ext4 -E nodiscard /dev/xvdh
  sudo mkdir /var/lib/longhorn
  sudo mount /dev/xvdh /var/lib/longhorn
fi

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="agent --token ${k3s_cluster_secret}" K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
  echo 'k3s agent did not install correctly'
  sleep 2
done
