#!/bin/bash

source test_engine/.venv/bin/activate

pip install -r test_engine/requirements.txt

flake8 test_engine/

if [[ $? -eq 0 ]] ; then
    echo "flake8 check succeed"
    exit 0
else
    echo "flake8 check failed"
    exit 1
fi
