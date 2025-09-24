#!/bin/bash

count=1
args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --count)
      # Handle "--count N"
      if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
        count="$2"
        shift # skip the number N
      fi
      ;;
    --count=*)
      # Handle "--count=N"
      count="${1#*=}"
      ;;
    *)
      # Collect other args as options for robot)
      args+=("$1")
      ;;
  esac
  shift
done

# Build repeated ./tests
tests=()
for ((i=0; i<count; i++)); do
  tests+=("./tests")
done

robot -x junit.xml -P ./libs -d /tmp/test-report "${args[@]}" "${tests[@]}"
