#!/bin/bash

set -x

flake8 .
py.test -v . $@
