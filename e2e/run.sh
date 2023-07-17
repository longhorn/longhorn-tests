#!/bin/bash

usage () {
   echo "USAGE: $0 --test_suite_path <specified_test_suite_path>  \ "
   echo "          --test_case_name <specified_test_case_name> \ "
   echo "Execute e2e testing with Robot Framework."
   echo ""
   echo "  -s, --test_suite_path             (Required) Test suite file path. e.g., /node_not_ready/node_reboot.robot or /replica_resiliency_test.robot"
   echo "  -t, --test_case_name             (Optional) Test case name. e.g., 1-RWO 3 replicas abnormal attached and replica node"
   echo "  -h, --help                   Usage message"
}

error_invalid_params() {
  echo -e "[ERROR]Invalid params. Check the required params."
  usage
  exit 1
}

while [[ "$#" -gt 0 ]]; do
  key="$1"
  case $key in
    -s|--test_suite_path)
    test_suite_path="$2"
    shift # past argument
    shift # past value
    ;;
    -t|--test_case_name)
    test_case_name="$2"
    shift # past argument
    shift # past value
    ;;
    -h|--help)
    usage
    exit 0
    shift
    ;;
    *)
    error_invalid_params
    ;;
    esac
done

# Check the required parameters exits
if [ -z "${test_suite_path}" ] ; then
    error_invalid_params
fi

# Start running the e2e test
if [ -z "${test_case_name}" ] ; then
    robot -P "${PWD}/libs" -L debug ./tests${test_suite_path}
else
    robot -P "${PWD}/libs" -L debug  -t "${test_case_name}" ./tests${test_suite_path}
fi
