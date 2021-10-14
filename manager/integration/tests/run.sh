#!/bin/bash

if [[ $@ =~ "--junitxml=" ]] ; then 
  pytest -v "$@" > /tmp/longhorn-pytest 2>&1
  
  cat ${LONGHORN_JUNIT_REPORT_PATH}
else 
  set -x 
  
  flake8

  pytest -v "$@"
fi 
