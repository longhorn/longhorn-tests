connect_to_vpn(){
  mkdir -p /dev/net
  mknod /dev/net/tun c 10 200
  chmod 600 /dev/net/tun
  openvpn --config vpn.ovpn --daemon
  sleep 10
  cat /var/log/openvpn.log
}
