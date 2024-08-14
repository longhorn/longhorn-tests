#!/bin/bash

sudo yum update -y
sudo yum group install -y "Development Tools"
sudo yum install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools cryptsetup
sudo systemctl -q enable iscsid
sudo systemctl start iscsid
# disable nm-cloud-setup otherwise k3s-agent service won’t start.
sudo systemctl disable nm-cloud-setup.service nm-cloud-setup.timer

modprobe uio
modprobe uio_pci_generic
modprobe vfio_pci
modprobe nvme-tcp
touch /etc/modules-load.d/modules.conf
cat > /etc/modules-load.d/modules.conf <<EOF
uio
uio_pci_generic
vfio_pci
nvme-tcp
EOF

echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf

if [[ "${extra_block_device}" != true ]] && [[ -b "/dev/xvdh" ]]; then
  mkfs.ext4 -E nodiscard /dev/xvdh
  mkdir /var/lib/longhorn
  mount /dev/xvdh /var/lib/longhorn
fi

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="agent --token ${k3s_cluster_secret} --selinux=true" K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
  echo 'k3s agent did not install correctly'
  sleep 2
done

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
fi
