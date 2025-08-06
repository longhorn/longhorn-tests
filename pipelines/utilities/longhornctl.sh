longhornctl_check(){
  curl -L https://github.com/longhorn/cli/releases/download/v1.9.1/longhornctl-linux-amd64 -o longhornctl
  chmod +x longhornctl
  ./longhornctl install preflight
  ./longhornctl check preflight
  if [[ -n $(./longhornctl check preflight 2>&1 | grep error) ]]; then
    exit 1
  fi
}
