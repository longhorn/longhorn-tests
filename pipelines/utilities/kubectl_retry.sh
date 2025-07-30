apply_kubectl_retry(){
  cat << 'EOF' > ~/.bashrc

kubectl() {
  { set +x; } 2>/dev/null
  trap 'set -x' RETURN
  local max_retries=60
  local delay=5
  local count=0

  while true; do
    output=$(/usr/local/bin/kubectl "$@" 2>&1)
    exit_code=$?
    echo "$output"
    count=$((count + 1))
    if grep -qiE "connection refused|apiserver not ready|unauthorized|error looking up secret|has prevented the request from succeeding" <<< "$output"; then
      echo "Attempt $count failed with exit code $exit_code. Retrying in $delay seconds..." >&2
    elif [[ $count -ge $max_retries ]]; then
      break
    else
      break
    fi
    sleep $delay
  done
}
EOF

  source ~/.bashrc
}

unset_kubectl_retry(){
  cat << 'EOF' > ~/.bashrc

kubectl() {
  { set +x; } 2>/dev/null
  trap 'set -x' RETURN
  /usr/local/bin/kubectl "$@"
  return $?
}
EOF

  source ~/.bashrc
}
