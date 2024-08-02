#!/bin/bash

sudo sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
  sudo setenforce  1
elif [[  ${selinux_mode} == "permissive" ]]; then
  sudo setenforce  0
fi

# Do not arbitrarily run "dnf update", as this will effectively move us up to the latest minor release.
sudo dnf group install -y "Development Tools"
sudo dnf install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools cryptsetup device-mapper
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

modprobe uio
modprobe uio_pci_generic
modprobe nvme-tcp
modprobe dm_crypt
touch /etc/modules-load.d/modules.conf
cat > /etc/modules-load.d/modules.conf <<EOF
uio
uio_pci_generic
nvme-tcp
dm_crypt
EOF

echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf

if [[ "${extra_block_device}" != true ]] && [[ -b "/dev/xvdh" ]]; then
  sudo mkfs.ext4 -E nodiscard /dev/xvdh
  sudo mkdir /var/lib/longhorn
  sudo mount /dev/xvdh /var/lib/longhorn
fi

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="agent --token ${k3s_cluster_secret} --selinux=${enable_selinux}" K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
  echo 'k3s agent did not install correctly'
  sleep 2
done

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/rocky/.ssh/authorized_keys
fi