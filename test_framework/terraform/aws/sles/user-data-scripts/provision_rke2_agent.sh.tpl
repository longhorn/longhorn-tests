#!/bin/bash

set -e

sudo systemctl restart guestregister # Sometimes registration fails on first boot.
sudo zypper ref
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi nfs-client cryptsetup device-mapper samba
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

if [[ "${extra_block_device}" != true ]]; then
  if [[ -b "/dev/nvme1n1" ]]; then
    mkfs.ext4 -E nodiscard /dev/nvme1n1
    mkdir /mnt/sda1
    mount /dev/nvme1n1 /mnt/sda1

    mkdir /mnt/sda1/local
    mkdir /opt/local-path-provisioner
    mount --bind /mnt/sda1/local /opt/local-path-provisioner

    mkdir /mnt/sda1/longhorn
    mkdir /var/lib/longhorn
    mount --bind /mnt/sda1/longhorn /var/lib/longhorn
  elif [ -b "/dev/xvdh" ]; then
    mkfs.ext4 -E nodiscard /dev/xvdh
    mkdir /var/lib/longhorn
    mount /dev/xvdh /var/lib/longhorn
  fi
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

if [ "${cis_hardening}" == true ]; then
    cat << EOF > /etc/sysctl.d/60-rke2-cis.conf
vm.panic_on_oom=0
vm.overcommit_memory=1
kernel.panic=10
kernel.panic_on_oops=1
EOF
    systemctl restart systemd-sysctl
    useradd -r -c "etcd user" -s /sbin/nologin -M etcd -U
    cat << EOF >> /etc/rancher/rke2/config.yaml
profile: "cis-1.23"
EOF
fi

systemctl start rke2-agent.service

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
fi

exit $?
