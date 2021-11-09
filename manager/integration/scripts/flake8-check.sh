#!/bin/bash

source manager/integration/.venv/bin/activate

pip install -r manager/integration/tests/requirements.txt

flake8 manager/integration/tests

if [[ $? -eq 0 ]] ; then
    echo "flake8 check succeed"
    exit 0
else
    echo "flake8 check failed"
    exit 1
fi
