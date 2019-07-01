#!/bin/bash 

source manager/integration/.venv/bin/activate 

pip install -r manager/integration/tests/requirements.txt

flake8 manager/integration/tests
