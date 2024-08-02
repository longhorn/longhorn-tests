#!/bin/bash

sudo systemctl stop firewalld
sudo systemctl disable firewalld

sudo yum update -y
sudo yum group install -y "Development Tools"
sudo yum install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools cryptsetup device-mapper nc
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
  mkfs.ext4 -E nodiscard /dev/xvdh
  mkdir /var/lib/longhorn
  mount /dev/xvdh /var/lib/longhorn
fi

RKE_SERVER_IP=`echo ${rke2_server_url} | sed 's#https://##' | awk -F ":" '{print $1}'`
RKE_SERVER_PORT=`echo ${rke2_server_url} | sed 's#https://##' | awk -F ":" '{print $2}'`

while ! nc -z $${RKE_SERVER_IP} $${RKE_SERVER_PORT}; do
  sleep 10 #
done

curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" INSTALL_RKE2_VERSION="${rke2_version}" sh -

mkdir -p /etc/rancher/rke2

cat << EOF > /etc/rancher/rke2/config.yaml
server: ${rke2_server_url}
token: ${rke2_cluster_secret}
EOF

systemctl enable rke2-agent.service
systemctl start rke2-agent.service

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
fi

exit $?
