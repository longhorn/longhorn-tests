#!/bin/bash

if [[ $@ =~ "--junitxml=" ]] ; then 
  flake8 .

  py.test -v . $@  >> /tmp/longhorn-pytest 2>&1
  
  cat ${LONGHORN_JUNIT_REPORT_PATH}
else 
  set -x 
  
  flake8 .

  py.test -v . $@
fi 
