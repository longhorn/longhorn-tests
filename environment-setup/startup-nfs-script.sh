touch /startup.log

apt-get update
apt-get install nfs-kernel-server -y >> /startup.log 2>&1
mkdir /var/nfs
chown nobody:nogroup /var/nfs/
echo "/var/nfs *(rw,sync,no_subtree_check)" >> /etc/exports
echo "exporting nfs dirs ..." >> /startup.log 2>&1
exportfs -a >> /startup.log 2>&1
echo "starting nfs ..." >> /startup.log 2>&1
service nfs-kernel-server start >> /startup.log 2>&1
service nfs-kernel-server status >> /startup.log 2>&1
showmount -e >> /startup.log 2>&1
