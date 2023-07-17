#!/bin/bash

usage () {
   echo "USAGE: $0 --test_suite_path <specified_test_suite_path>  \ "
   echo "          --test_case_name <specified_test_case_name> \ "
   echo "Execute e2e testing with Robot Framework."
   echo ""
   echo "  -s, --test_suite_path  (Optional) Test suite file path, e.g., ./tests/node_not_ready/node_power_off.robot. If empty, then run all cases under default folder /e2e/tests"
   echo "  -t, --test_case_name  (Optional) Test case name. e.g., Node power off with replica-VA"
   echo "  -h, --help  Usage message"
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
    test_suite_path[${#test_suite_path[@]}]="$2"
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

# Concate the multiple suite paths as string
for value in "${test_suite_path[@]}"
do
  test_suite_paths+="${value} "
done

# Check if the given test_suite_paths is empty, if yes, execute all cases under the default folder
if [ -z "${test_suite_paths}" ] ; then
    test_suite_paths="./tests"
fi

# Start running the e2e test
if [ -z "${test_case_name}" ] ; then
    robot -P "${PWD}/libs" -L debug ${test_suite_paths}
else
    robot -P "${PWD}/libs" -L debug  -t "${test_case_name}" ${test_suite_paths}
fi
