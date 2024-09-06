#!/bin/bash

sudo sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
  sudo setenforce  1
elif [[  ${selinux_mode} == "permissive" ]]; then
  sudo setenforce  0
fi

# Do not arbitrarily run "dnf update", as this will effectively move us up to the latest minor release.
sudo dnf group install -y "Development Tools"
sudo dnf install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools cryptsetup device-mapper jq nmap-ncat
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

modprobe uio
modprobe uio_pci_generic
modprobe vfio_pci
modprobe nvme-tcp
modprobe dm_crypt
touch /etc/modules-load.d/modules.conf
cat > /etc/modules-load.d/modules.conf <<EOF
uio
uio_pci_generic
vfio_pci
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

RKE_SERVER_IP=`echo ${rke2_server_url} | sed 's#https://##' | awk -F ":" '{print $1}'`
RKE_SERVER_PORT=`echo ${rke2_server_url} | sed 's#https://##' | awk -F ":" '{print $2}'`

while ! nc -z $${RKE_SERVER_IP} $${RKE_SERVER_PORT}; do   
  sleep 10 #
done

curl -sfL https://get.rke2.io | sudo INSTALL_RKE2_TYPE="agent" INSTALL_RKE2_VERSION="${rke2_version}" sh -

sudo mkdir -p /etc/rancher/rke2

sudo tee -a /etc/rancher/rke2/config.yaml >/dev/null <<EOF
server: ${rke2_server_url}
token: ${rke2_cluster_secret}
EOF

sudo systemctl enable rke2-agent.service
sudo systemctl start rke2-agent.service

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/rocky/.ssh/authorized_keys
fi

exit $?
