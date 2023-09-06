apply_selinux_workaround(){
  kubectl apply -f "https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/prerequisite/longhorn-iscsi-selinux-workaround.yaml"
}