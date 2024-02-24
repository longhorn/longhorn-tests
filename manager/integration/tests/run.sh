#!/bin/bash

export PYTHONUNBUFFERED=1
pytest -v "$@"
