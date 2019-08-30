#!/bin/bash

if [[ $@ =~ "--junitxml=" ]] ; then 
  flake8 .

  py.test -v . $@  >> /tmp/longhorn-pytest 2>&1
  
  cat ${LONGHORN_JUNIT_REPORT_PATH}

elif [[ $@ =~ "test_stress" ]] ; then
  py.test --include-stress-test -s test_stress.py::test_stress -n ${STRESS_TEST_NPODS} || py.test --include-stress-test -s test_stress.py::test_reset_env

else 
  set -x 
  
  flake8 .

  py.test -v . $@
fi 
