#!/bin/bash

if [[ $@ =~ "--junitxml=" ]] ; then 
  pytest -v $@  > /tmp/longhorn-pytest
  
  cat ${LONGHORN_JUNIT_REPORT_PATH}
else 
  set -x 
  
  flake8

  pytest -v $@
fi 
