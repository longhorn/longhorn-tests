#!/bin/bash

robot -x junit.xml -P ./libs -d /tmp/test-report "$@" ./tests
