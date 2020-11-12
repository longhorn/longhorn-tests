#!/bin/bash

# This script will be used by Drone to build longhorn engine compitability test images and output image tag

./generate_version_image.sh 5 5 3 3 1 1 | tail -n 1 | cut -d ":" -f2
./generate_version_image.sh 2 2 3 3 1 1 | tail -n 1 | cut -d ":" -f2
./generate_version_image.sh 4 3 4 4 1 1 | tail -n 1 | cut -d ":" -f2
./generate_version_image.sh 4 3 2 2 1 1 | tail -n 1 | cut -d ":" -f2
./generate_version_image.sh 4 3 3 3 1 1 | tail -n 1 | cut -d ":" -f2
