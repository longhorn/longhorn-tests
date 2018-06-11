#!/bin/bash

set -e

cd compatibility
img1=`./generate_version_image.sh 2 2 1 1 1 1 | tail -n 1`
img2=`./generate_version_image.sh 0 0 1 1 1 1 | tail -n 1`
img3=`./generate_version_image.sh 1 1 2 2 1 1 | tail -n 1`
img4=`./generate_version_image.sh 1 1 0 0 1 1 | tail -n 1`

echo build done
echo The commands for push:
echo docker push $img1
echo docker push $img2
echo docker push $img3
echo docker push $img4
